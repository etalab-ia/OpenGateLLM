# ADR - 2026-08-25 - QoS and priority

* **Status:** Draft
* **Date:** 2026-08-25
* **Authors:** Development Team
* **Decision Outcome:** QoS and priority

---

# QoS, load balancing, file d’attente et priorisation

## Contexte

Actuellement un système de queueing et de priorisation est implémenté avec Celery et RabbitMQ. Lors du refactoring du endpoint /v1/chat/completions en clean architecture nous allons enlever toute dépendance avec système. **Nous repartons d'une feuille blanche, sans considération du code existant**, avec les objectifs suivants : **protéger chaque provider**, **envoyer au moins chargé**, **aligner le health**, puis **prioriser** grâce à une vraie attente. Le batch est un chantier suivant.

Plusieurs besoins :

1. priorisation : permettre de prioriser certaines requêtes par rapport à d'autres 

    Cela permet d'assurer un traitement des requêtes de certaines clients par rapport à d'autres dans les périodes de fortes charges.

2. qualité de service (QoS): permettre de limiter le nombre de requêtes traité par un provider pour garantir une qualité de service.

    Cela permet 2 choses : 
        - pour les moteurs d'inférence qui ne supportent pas la charge (comme WhisperX), cela évite au modèle de crasher
        - pour les moteurs d'inférence qui supportent la charge (comme vLLM/Mistral), cela permet de fluidifier le traitement des requêtes si le moteur d'inférence n'est pas optimisé pour la charge.

3. batch : permettre d'exécuter des requêtes quand les providers sont disponibles.

    Cela permet de tirer parti des providers tout le long de la journée et de mieux répartir la charge sur les providers pour éviter des saturations.

Ces 3 concepts sont liés. En effet, le batch a besoin d'un indicateur de la charge des providers pour exécuter des requêtes quand ils sont disponibles. La priorisation suppose qu'il existe un mécanisme d'attente pour permettre aux requêtes prioritaires de passer devant les requêtes non prioritaires.

Le QoS répond à ces 2 besoins en définissant 3 niveaux de charge (vert, orange et rouge) et fait attendre les requêtes dans un boucle jusqu'à ce qu'un provider soit disponible. La charge d'un provider peut être mesurée de plusieurs manières : le nombre de requêtes en cours, le poids des fichiers traités par le modèle, tokens in-flight, ...

## Problème

Sans attente, la priorisation ne sert à rien. Il faut un **plafond de charge** et une **queue** pour que les prioritaires passent devant.

Le QoS actuel a deux faiblesses :

1. **Compteur Redis unique** (`INCR`/`DECR`) qui ne redescend plus si Redis est saturé, si le worker crash, ou si le client coupe.
2. **Métriques provider** (vLLM, Mistral) : latence, chiffre pas live, concurrence, service tiers instable, métrique absente chez beaucoup de providers.

## Principes

- On compte **nous-mêmes** dans Redis (`qos:load`, pas de `SCAN` / `KEYS`).
- Admission **atomique Lua**, en tenant compte du **poids de la requête qui arrive**.
- On **préfère jeter** une requête bloquante plutôt que de geler le système.
- Health et QoS : **même source Redis** (`qos:load`), pas d’API métriques provider.
- Load balancing **least busy filtrant** sur **la même métrique** que le QoS : moins chargé parmi les providers qui peuvent admettre le poids.
- Limites / in-flight **par provider** ; file d’attente **par router**.
- Lua pour admission et claim (tête de file → provider éligible).

---

## 1. Métrique et limite

La limite est **par provider** : un même modèle peut avoir 1 GPU ou 8, donc des capacités différentes.

Tous les providers d’un **même router** partagent **la même métrique QoS**. La **limite** peut différer.

| V1 | Plus tard |
|---|---|
| Nombre de requêtes concurrentes **ou** poids des fichiers audio (octets) | Tokens in-flight, tokens pondérés |

Exemple audio : limite 500 Mo, occupé 300 Mo, requête de 300 Mo → **300 + 300 > 500** → la requête **n’entre pas**, elle attend (ou 503).

`qos_metric = null` : pas d’admission, statut health quand même si une limite est définie… Non : sans métrique on n’a pas de charge. Plus simple : **pas de QoS = pas de limite, pas de file, health vert** (ou hors QoS). Si on veut un statut sans bloquer : `qos_wait_timeout = null` (voir §4).

La poids max des fichiers doit être supérieur ou égale au max par fichier déjà configurable dans l'API.

---

## 2. Load balancing least busy (filtrant)

Le QoS est **couplé** au least busy. La **limite** et la **charge** restent **par provider** (`qos:load` / `qos_limit`, §5). Le choix se fait parmi les providers **qui peuvent admettre le poids** de la requête, pas seulement le moins chargé en absolu.

`occupation(p) = qos:load(p) / qos_limit(p)`  
(comparable même si les limites diffèrent — 1 GPU vs 8 GPU)

### Chemin direct (pas de file)

1. Lire `qos:load` de chaque provider du router (éventuellement après une purge légère §5 si on centralise dans un Lua).
2. Garder les **éligibles** : `qos:load(p) + poids ≤ qos_limit(p)`.
3. Parmi les éligibles, prendre `p* = argmin occupation(p)`.
4. **Admission Lua** atomique sur `p*` (§5 : purge ZSET in-flight + check + `ZADD` / incr `qos:load`).
5. Si le Lua refuse (course : la charge a bougé) → retenter une fois sur le prochain éligible ; sinon enfiler (§6) ou 503.

Sous la limite (au moins un provider éligible) : **pas de ZSET d’attente**, prioritaire et non prioritaire passent tout de suite.

### Exemple

| Provider | `qos_limit` | `qos:load` | Occupation | Requête 300 Mo |
|---|---|---|---|---|
| A (1 GPU) | 400 Mo | 50 Mo | 12,5 % | **non** (50+300 > 400) |
| B (8 GPU) | 2000 Mo | 800 Mo | 40 % | **oui** |

Sans filtre d’éligibilité : on choisirait A (moins chargé) → refus → file collée à A alors que B peut prendre.  
Avec filtre : on admet sur **B**.

### Si aucun provider n’est éligible

→ une seule file d’attente **par router** (§6), pas une file par provider. Les limites restent celles de chaque provider au moment du claim.

---

## 3. Health

Statut **par provider**, même source que le QoS : `occupation = qos:load / limite`.

Seuil orange **configurable** (défaut 90 % de la limite).

| Occupation | Statut |
|---|---|
| &lt; seuil orange | Vert |
| ≥ seuil et &lt; 100 % | Orange |
| ≥ 100 % | Rouge |

`GET /health/models` : pour un router, on expose le **meilleur** statut parmi ses providers (un provider vert suffit à afficher vert : le least busy ira dessus).

Pas de fallback vLLM/Mistral.

---

## 4. Attente, timeout et 503

La file d’attente est **par router** : les durées d’attente vivent au **router**. Elles doivent rester **strictement inférieures** au plus petit `timeout` des providers du router (aujourd’hui défaut 300 s).

| Paramètre (router) | Rôle |
|---|---|
| `qos_wait_timeout` | Combien de temps la requête HTTP attend une place (poll ~1 s). |
| `qos_queue_max_wait` | Combien de temps max dans la ZSET d’attente avant d’être jetée. |
| `max_queue_size` | Cap `ZCARD` de `qos:wait:{router_id}` (§6). |

Pour le trafic interactif V1, `qos_wait_timeout` et `qos_queue_max_wait` peuvent être égaux.

| `qos_wait_timeout` | Comportement |
|---|---|
| `null` | Pas de file, pas de 503 QoS. Statut vert/orange/rouge seulement. |
| `0` | 503 immédiat, pas de ZSET d’attente. |
| `N` s | Attente jusqu’à N (plafonnée par `qos_queue_max_wait`). |

Erreur : **503** + header **`Retry-After`** (secondes).

### Règle `Retry-After`

Le header est renvoyé quand on **refuse** (la requête HTTP est déjà terminée) :

| Cas | Dans `qos:wait:{router_id}` ? |
|---|---|
| `qos_wait_timeout = 0` | non |
| `max_queue_size` atteint | non |
| `qos_wait_timeout` / `qos_queue_max_wait` dépassé | éjecté |

On estime un back-off, on ne promet pas un slot.

#### Durée `D` (déjà dans Redis)

Timeserie `ogl_ts:latency:{provider_id}` (alimentée au forward, rétention 30 min). **p50** de la fenêtre, en secondes. Ce sont des jobs **terminés**, hors temps en file. Série vide : fallback `min(30, timeout_provider - 1)`.

Provider de référence pour `D` / `qos:load` / `limite` : le **moins chargé parmi les éligibles** si un refus Lua vient d’échouer ; sinon le **moins chargé du router** (aucun n’admet ce poids).

Le heartbeat (~30 s) ne mesure **pas** cette durée.

`D` = p50 (moins de sur-attente). p90 plus tard si trop de 503 en boucle.

#### Travail devant le client

La formule `D × (qos:load + poids) / limite` ne voit **que l’in-flight**. À 256/256 et 500 waiters, l’occupation vaut ~1 → on annonce ~`D`. Le client revient trop tôt, reprend une 503, éventuellement derrière `max_queue_size`. Les 503 `max_queue_size` sont les plus trompeurs : la file n’a pas bougé.

Il faut le **poids déjà en file router** (une seule ZSET) et la capacité du provider de référence :

| Grandeur | Source |
|---|---|
| `qos:load` | somme des poids in-flight du provider de référence (§5) |
| `W_queue` | somme des poids dans la file router — entier `qos:wait:load:{router_id}` (même pattern que `qos:load`, O(1), pas de `ZRANGE` / `SCAN`) |
| `poids` | la requête refusée |
| `limite` | `qos_limit` du provider de référence |

Si la métrique est le nombre de requêtes, `W_queue = ZCARD(qos:wait:{router_id})` et `poids = 1`.

Approximation V1 : on divise le travail file **router** par la limite **d’un** provider. Avec plusieurs providers, la capacité réelle est plus haute → `Retry-After` un cran pessimiste (acceptable). Plus tard : `Σ qos:load(p)` / `Σ qos_limit(p)` ou drain parallèle estimé.

#### Formule

```
ETA = D × (qos:load + W_queue + poids) / limite

Retry-After = clamp(
  1,
  qos_queue_max_wait,   # plafond interactif ; pas timeout_provider (voir plus bas)
  ceil(ETA × (0.5 + rand()))   # jitter 50 %–150 %
)
```

`qos:load + W_queue + poids` = travail **déjà admis (sur le provider de référence) + déjà en file router + cette requête** si elle réessayait maintenant. Diviser par `limite` → « générations » de capacité ; × `D` → secondes.

Ce n’est **pas** le temps jusqu’au prochain slot (`≈ D / parallèle`, souvent < 1 s) : trop agressif, orage de retries. C’est un back-off qui **grossit avec la file**.

| Situation (`D = 60 s`) | Calcul | Retry-After (sans jitter) |
|---|---|---|
| 500 Mo / 500 Mo, file vide, poids négligeable | `60 × (500+0+ε)/500` | ~60 s |
| 300 Mo + requête 300 Mo / 500 Mo, file vide | `60 × 600/500` | 72 s |
| 256 req / 256, **file vide** | `60 × (256+0+1)/256` | ~60 s |
| 256 req / 256, **256 en file router** | `60 × (256+256+1)/256` | ~120 s |
| 256 / 256, **file pleine** (`max_queue_size = 512`) | `60 × (256+512+1)/256` | ~180 s |
| requête admise | — | pas de 503 |

#### Plafond : ne pas reclamper sur `timeout` provider

Le `timeout` provider borne **un forward**, pas un nouvel essai après 503. Le client n’a plus de connexion.

Reclamper sur `timeout_provider - 1` (ex. 299 s) **recasse** l’estimation dès que la file est profonde : l’ETA honnête est tronqué, le client revient trop tôt — exactement le biais d’ignorer `W_queue`.

Le plafond utile en V1 interactif, c’est `qos_queue_max_wait` (déjà `< min(timeout)` des providers). Si on veut un `Retry-After` plus long que l’attente HTTP max, le poser explicitement, pas le timeout d’inférence.

#### Jitter

Sans jitter, tout le monde reçoit le même entier au même instant → stampede sur Redis et le GPU. `× (0.5 + rand())` suffit. Le header reste un entier de secondes.

#### Ce que ça ne promet pas

- D’ici `Retry-After`, des rôles plus prioritaires peuvent s’insérer, `D` et le least-busy filtrant peuvent changer.
- Après éjection, on **ne retranche pas** le temps déjà attendu : le client n’est plus dans `qos:wait`, les autres si.
- Option plus tard : `W_queue` = seulement les waiters **devant** ce rôle (score ZSET meilleur). En V1, toute la file : un cran pessimiste, plus simple.

---

## 5. Comptage : ZSET in-flight + somme de poids (Lua)

Un `INCR`/`DECR` global ne redescend plus si :

| Incident | Mitigation |
|---|---|
| Client / proxy coupe | Disconnect FastAPI → Lua de sortie (retrait ZSET + décrément somme) |
| Pool Redis saturé | Retry (jamais 100 %) |
| Worker crash | **Expiration** : plus de code à exécuter |

On ne compte **pas** des clés avec `SCAN` / `KEYS` (coût O(n) à chaque admission et à chaque poll).

**Modèle Redis, par provider :**

| Clé | Rôle |
|---|---|
| `qos:inflight:{provider_id}` | **ZSET** : un membre par requête en cours (`request_id`). Score = **timestamp d’expiration**. |
| `qos:load:{provider_id}` | **Entier** : somme des poids (1 par requête, ou octets audio). Source de vérité pour l’admission, le least-busy et le health. |
| `qos:weight:{provider_id}` | **Hash** : `request_id` → poids, pour retrancher le bon montant à la purge. |

Least-busy, health et « est-ce que ça rentre ? » lisent **`qos:load`**, pas le cardinal de la ZSET (le cardinal reste utile pour debug / nombre de requêtes si la métrique est `inflight`).

**Admission (un seul script Lua) :**

1. Purger : `ZRANGEBYSCORE` des membres dont le score (expiration) est dépassé, retrancher leurs poids de `qos:load`, `HDEL` + `ZREMRANGEBYSCORE`.
2. Lire `qos:load`.
3. Si `charge + poids_requête > limite` → refuser (le caller enfile ou 503).
4. Sinon : `ZADD` le `request_id` (score = `now + ttl_heartbeat`), `HSET` le poids, incrémenter `qos:load` — **atomique**.

Pas d’overshoot volontaire.

Le TTL n’est pas « un peu au-dessus de la durée moyenne » pour **mesurer** la charge. C’est uniquement le **filet** anti-zombie. La mesure, c’est `qos:load`, toujours aligné avec la ZSET dans le même round-trip Lua. Un worker crash → plus de heartbeat → le prochain Lua d’admission **purge** le membre (fenêtre fantôme = intervalle de heartbeat, pas la durée du job). Utile (WhisperX, GPU) : on sous-admet un moment, le temps que l’infra revienne.

**Sortie normale** (fin de requête, disconnect) : Lua inverse — `ZREM` + `HDEL` + décrément du poids. Retry Redis conservé ; si ça échoue, le prochain admit **purge à l’expiration**.

Si Redis est down : on **laisse passer** (fail-open).

---

## 6. File d’attente et priorisation

### Priorité

Aujourd’hui : `user.priority`.  
Cible : **`role.priority`** (entier, plus élevé = plus prioritaire). Les utilisateurs héritent du rôle. Le plafond `routing_max_priority` reste.

### ZSET d’attente, **une par router**

Distincte des ZSET **in-flight** du §5, qui restent **par provider** (`qos:inflight` / `qos:load` / `qos:weight`). On n’enfile **que** si la requête **ne tient sur aucun provider** (§2). Même modèle que l’in-flight : ZSET + compteur de poids O(1), **pas** de `SCAN` / `KEYS`.

| Clé | Portée | Rôle |
|---|---|---|
| `qos:wait:{router_id}` | Router | **ZSET** d’attente. Score = **priorité** + **timestamp (ms)** — ordre seulement, **pas** d’expiration. |
| `qos:wait:hb:{router_id}:{request_id}` | Router | Clé de présence / heartbeat O(1). |
| `qos:wait:weight:{router_id}` | Router (hash) | `request_id` → poids (claim + purge sans relire le body). |
| `qos:wait:load:{router_id}` | Router (entier) | Somme des poids en file — miroir de `qos:load`, pour `Retry-After` / `W_queue` (§4). |

Cycle :

1. Si `max_queue_size` atteint (`ZCARD qos:wait:{router_id}`) → 503 + `Retry-After`, sans entrer.
2. `ZADD` wait + `HSET` poids + incr `qos:wait:load` + créer la clé de présence.
3. Chaque seconde : heartbeat + tenter un **claim** (Lua ci-dessous).
4. Succès → forward sur le provider choisi par le claim.
5. Sinon → attendre jusqu’à `qos_queue_max_wait` / `qos_wait_timeout` → 503 + `Retry-After`.

### Claim Lua (tête de file → meilleur provider éligible)

Un script, avec en args la liste `(provider_id, qos_limit)` du router :

1. Lire le premier de `qos:wait:{router_id}` (`ZRANGE` 0 0).
2. Si la clé de présence hb est absente → `ZREM` + `HDEL` poids + décr `qos:wait:load`, passer au suivant (anti-blocage zombie).
3. Pour **chaque** provider : purge in-flight §5 (`ZRANGEBYSCORE` expirés → retrancher `qos:load` / `HDEL` / `ZREMRANGEBYSCORE`).
4. Lire le poids dans `qos:wait:weight`. Éligibles = `qos:load(p) + poids ≤ qos_limit(p)`.
5. Si aucun éligible → no-op (le waiter re-polle à la seconde suivante).
6. Sinon `p* = argmin occupation(p)` parmi les éligibles (`occupation = qos:load / qos_limit`).
7. Atomique : `ZREM` wait + `DEL` hb + `HDEL` poids wait + décr `qos:wait:load` + admission §5 sur `p*` (`ZADD` inflight avec score `now + ttl_heartbeat`, `HSET` `qos:weight`, incr `qos:load`).

Seul le **premier** vivant claim (sauf purge zombie). Plus de collage à un provider : dès qu’**un** provider du router a de la place pour ce poids, la tête part dessus, en préférant le moins chargé **parmi ceux qui peuvent l’admettre**.

### Head-of-line (poids)

La file router **ne supprime pas** le HOL : si le 1er demande 400 Mo et qu’aucun provider n’a 400 Mo libres, les 10 Mo derrière attendent. V1 : garder « premier seulement ». Plus tard : **skip** si la tête ne rentre nulle part, claim le premier qui rentre quelque part (avec aging pour ne pas affamer les gros).

### Cap de file

`max_queue_size` : `ZCARD` de `qos:wait:{router_id}` (**par router**). Plafond atteint → **503 + `Retry-After`**, sans entrer.  
`null` = pas de cap. Un entier = file max, indépendant de `qos_wait_timeout`.

---

## Heartbeat

Le heartbeat couvre **toute la vie** de la requête (file et in-flight). Tant que le worker est vivant et la connexion active, on **repousse l’expiration**. Si le worker crash, si Redis ne répond plus, ou si le client coupe : plus de renouvellement → le prochain Lua **purge**.

On ne SCAN pas des clés `inflight:*` ni `wait:*`. En file, le score de `qos:wait:{router_id}` est l’ordre de priorité : l’expiration vit sur une **clé de présence** O(1). In-flight, le score de `qos:inflight:{provider_id}` **est** l’expiration ; la charge reste `qos:load:{provider_id}`.

| Phase | Structure | Compte dans `qos:load` | Heartbeat | Expire si heartbeat manqué |
|---|---|---|---|---|
| En file | Membre `qos:wait:{router_id}` + `qos:wait:hb:{router_id}:{request_id}` + poids dans `qos:wait:weight` | Non | Chaque **1 s** (même rythme que le poll / claim) | **3 s** |
| In-flight | Membre `qos:inflight:{provider_id}` (score = expiration) + poids dans `qos:weight:{provider_id}` | Oui | Chaque **~10 s** : `ZADD` avec `now + ~30 s` | **~30 s** (≈ 3 heartbeats) |

### En file

Toutes les secondes : tenter le claim §6 **et** `EXPIRE` de la clé de présence à 3 s.

Si le premier de `qos:wait:{router_id}` n’a plus de heartbeat → le claim Lua le **retire**, on passe au suivant. On accepte de **perdre** une prioritaire zombie plutôt que de bloquer la file.

### In-flight

Dès l’admission atomique (Lua §5, éventuellement dans le même claim §6) :

1. `ZADD` inflight + `HSET` poids + incr `qos:load` sur le **provider choisi**, score `now + ~30 s`.
2. Tant que le forward tourne (y compris stream), un task asyncio **repousse le score** toutes les ~10 s.
3. Fin normale, disconnect FastAPI, ou erreur provider → Lua de sortie immédiat (le heartbeat n’est que le filet).

Un WhisperX de 5 min reste dans `qos:load` jusqu’à la fin. Un worker qui crash au milieu : au plus ~30 s de charge fantôme, puis la place se libère. C’est assez court pour ne pas figer le QoS, assez long pour encaisser un hic Redis sans sous-compter une requête encore vivante.

### Toujours supprimer dès qu’on peut

Le heartbeat ne remplace pas les sorties explicites :

| Événement | Action |
|---|---|
| Requête terminée (succès ou erreur provider) | Lua sortie in-flight (`ZREM` + `HDEL` + décr `qos:load`) |
| Client / proxy coupe (`disconnect`) | Lua sortie file (`ZREM` wait + `DEL` hb + `HDEL` poids + décr `qos:wait:load`) ou in-flight |
| Jeter après `qos_queue_max_wait` | `ZREM` wait + `DEL` hb + `HDEL` poids + décr `qos:wait:load` |
| Crash worker / Redis saturé malgré retry | Rien à exécuter → claim / admit suivant purge à l’expiration |

Retry Redis conservé sur heartbeat / sortie. Si un renouvellement in-flight échoue plusieurs fois, on **préfère jeter** (arrêter le forward si possible, ou laisser expirer le membre) plutôt que de garder une charge fantôme indéfiniment.

---

## 7. Suite : tokens et rate limiting

Le **nombre de requêtes** (ou les Mo) ne suffira pas partout : **2 requêtes à 400k tokens** peuvent saturer autant que **200 petites**.

À étudier plus tard :

- charge ≈ somme des tokens in-flight → une limite tokens ;
- sinon → requêtes **pondérées** par tokens d’entrée / max context.

### Rate limiting (clarification du point 10)

Aujourd’hui les rôles ont des quotas **RPM / TPM / RPD / TPD** : ça **bride l’utilisateur**, ça ne protège pas le GPU (un petit nombre de grosses requêtes passe encore).

L’idée de l’audio : si QoS + prio tiennent, le **QoS protège le provider** et la **prio garantit que les rôles importants passent**. On pourrait alors **assouplir ou retirer** ces rate limits comme protection d’infra.

Ce n’est **pas le V1**. Les rate limits peuvent rester comme **quotas produit / équité**. Décision séparée, une fois la métrique de charge (surtout tokens) jugée bonne.

---

## 8. Batch (chantier suivant)

Dès qu’on a capacité + file, un batch peut **n’envoyer que s’il reste de la marge**.

Deux options, sans choix pour l’instant :

| A — Même file, attente longue | B — Drain séparé |
|---|---|
| Priorité plus basse. Attente **heures / 1–2 jours**. Heartbeat + reconcilier la ZSET depuis Postgres si Redis est vidé. | Jobs en base / pub-sub. Un worker n’envoie **que si le provider est vert**. 503 → retry / remise en queue. |

Le dur : **statut de job, retry, monitoring**. Piste : framework de jobs **branché Postgres** plutôt que tout custom.

---

## Config (esquisse)

**Router**

- `load_balancing_strategy` : `least_busy` dès que le QoS est actif (least busy **filtrant**, §2)
- contrainte : tous les providers ont la **même** `qos_metric`
- `qos_wait_timeout` (`null` \| `0` \| N)
- `qos_queue_max_wait`
- `max_queue_size` (`null` \| entier)
- `qos_wait_timeout` et `qos_queue_max_wait` **&lt;** `min(timeout)` des providers du router

**Provider**

- `qos_metric` : `inflight` \| `audio_bytes` \| `null`
- `qos_limit` (capacité infra — 1 GPU ≠ 8 GPU)
- `qos_yellow_ratio` (défaut `0.9`)
- `timeout` (existant)
- Heartbeat in-flight : intervalle ~10 s, expiration ~30 s (filet anti-zombie sur `qos:inflight`, pas une mesure de durée)
- Pas de file d’attente dédiée : l’attente est au router

**Role**

- `priority` (migré depuis `user.priority`)

---

## Phasage

1. **V1 QoS + least busy filtrant** — ZSET in-flight + `qos:load` **par provider**, admission Lua (requêtes **et** poids audio), éligibilité puis `argmin occupation`, wait/`null`/`0`, 503 + `Retry-After`, health par provider / meilleur statut router, plus d’API métriques pour ça.
2. **Priorisation** — ZSET d’attente + `qos:wait:load` **par router**, claim multi-provider, heartbeat, `role.priority`.
3. **Métrique tokens / pondération** — étude ; éventuellement revoir les rate limits ; optionnellement skip HOL.
4. **Batch** — option A ou B + persistance job.

---

### Limites 

Tu as raison : j’avais mal cadré le risque. Avec un `await` (sleep / wait Redis), **le process FastAPI n’est pas bloqué**. Le reste de l’API continue. Ce n’est pas un argument pour Celery.

Ce qui reste tenu, ce n’est **pas le CPU**, c’est une **connexion HTTP + l’état de la requête**.

## Ce qui ne pose pas de problème

1. **Connexions** — chaque attente occupe un FD côté uvicorn, ingress, LB. Ce sont des limites de *nombre*, pas de CPU. 2 000 waiters WhisperX = 2 000 connexions idle, même à 0 % CPU.
2. **Corps de requête** — l’audio est déjà spoulé (`SpooledTemporaryFile`), donc plutôt disque que RAM, mais 2 000 fichiers en attente pèsent quand même. Le chat, lui, ne pèse presque rien.
3. **Timeouts devant l’API** — nginx / ingress / le client peuvent couper avant tes N secondes. Là tu attends pour rien et le client voit un 504, pas ton 503 + `Retry-After`.
4. **Session Postgres** — l’attente doit rester **après** relâchement de la connexion (comme le model-forward en autocommit). Sinon `idle in transaction`, et scaler FastAPI n’y change rien.

Rien de tout ça n’interdit d’attendre dans FastAPI. Ça dit juste : sans plafond, une file Redis peut **remplir les connexions** plus vite que le GPU ne se libère, et le CPU ne te préviendra pas.
