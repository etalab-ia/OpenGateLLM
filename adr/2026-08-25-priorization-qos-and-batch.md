# ADR - 2026-08-25 - Priorization QoS and Batch

* **Status:** Accepted
* **Date:** 2026-08-25
* **Authors:** Development Team
* **Decision Outcome:** Prioritize QoS and Batch

---

# QoS, load balancing, file d’attente et priorisation

Refonte du QoS actuel (compteur Redis `INCR`/`DECR` + métriques vLLM/Mistral). Objectif : **protéger chaque provider**, **envoyer au moins chargé**, **aligner le health**, puis **prioriser** grâce à une vraie attente. Le batch est un chantier suivant.

## Problème

Sans attente, la priorisation ne sert à rien. Il faut un **plafond de charge** et une **file** pour que les prioritaires passent devant.

Cas immédiat : **WhisperX / Visio**. Trop d’audio en parallèle ne ralentit pas seulement : **le process crash**. D’où une limite en **poids de fichiers** dès le V1, pas seulement en nombre de requêtes.

Le QoS actuel a deux faiblesses :

1. **Compteur Redis unique** (`INCR`/`DECR`) qui ne redescend plus si Redis est saturé, si le worker crash, ou si le client coupe.
2. **Métriques provider** (vLLM, Mistral) : latence, chiffre pas live, concurrence, service tiers instable, métrique absente chez beaucoup de providers. **On n’en fait plus un fallback.**

## Principes

- On compte **nous-mêmes** dans Redis (`qos:load`, pas de `SCAN` / `KEYS`).
- Admission **atomique Lua**, en tenant compte du **poids de la requête qui arrive**.
- On **préfère jeter** une requête bloquante plutôt que de geler le système.
- Health et QoS : **même source Redis** (`qos:load`), pas d’API métriques provider.
- Load balancing **least busy** sur **la même métrique** que le QoS.
- Lua pour admission et tête de file.

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

## 2. Load balancing least busy

Le QoS est **couplé** au least busy.

1. Parmi les providers du router, choisir le **moins chargé** au sens de la **métrique QoS** :  
   `occupation = qos:load / limite` (comparable même si les limites diffèrent).
2. Tenter l’**admission atomique** sur ce provider (**charge + poids requête ≤ limite**).
3. Si ça ne passe pas : **tester les autres** par occupation croissante (un petit provider à 10 % peut ne pas tenir 300 Mo alors qu’un gros à 40 % si).
4. Si **aucun** ne peut admettre → file d’attente du **moins chargé** (ZSET de ce provider), sauf si l’attente est désactivée / à 0.

Sous la limite (la requête **tient** sur au moins un provider) : **pas de ZSET**, prioritaire et non prioritaire passent tout de suite.

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

Deux durées **par provider**, **strictement inférieures** au `timeout` du provider (aujourd’hui défaut 300 s) :

| Paramètre | Rôle |
|---|---|
| `qos_wait_timeout` | Combien de temps la requête HTTP attend une place (poll ~1 s). |
| `qos_queue_max_wait` | Combien de temps max dans la ZSET avant d’être jetée. |

Pour le trafic interactif V1, les deux peuvent être égaux.

| `qos_wait_timeout` | Comportement |
|---|---|
| `null` | Pas de file, pas de 503 QoS. Statut vert/orange/rouge seulement. |
| `0` | 503 immédiat, pas de ZSET. |
| `N` s | Attente jusqu’à N (plafonnée par `qos_queue_max_wait`). |

Erreur : **503** + header **`Retry-After`** (secondes).

### Règle `Retry-After`

Quand un utilisateur reçoit une 503, il obtient une durée estimée pour réessayer.

On n’a pas la durée réelle des requêtes en cours. On réutilise la **timeserie Redis des dernières latences** du provider (`ogl_ts:latency:{provider_id}`, déjà alimentée au forward, rétention 30 min). Médiane (p50) de cette fenêtre, convertie en secondes. Ce n’est pas parfait (requêtes **terminées** seulement, pas le temps passé en file, série vide au démarrage) mais ça suffit pour une estimation.

`charge` = `qos:load`. Provider visé, ou le moins chargé si aucun n’admet.

Si la série est vide : retomber sur une constante (ex. `min(30, timeout_provider - 1)`).

```
Retry-After = clamp(
  1,
  timeout_provider - 1,
  ceil( latency_p50 × (qos:load + poids) / limite )
)
```

Exemples avec `latency_p50 = 60 s`, limite 500 Mo :

| Charge (`qos:load`) | Requête | Occupation | Retry-After |
|---|---|---|---|
| 300 Mo | 300 Mo | 1,2 | 72 s |
| 500 Mo | 1 req / négligeable | 1,0 | 60 s |
| 100 Mo | 50 Mo (admise) | — | pas de 503 |

Idée : à saturation, attendre **à peu près le temps d’une génération de requêtes** avant de réessayer, sans jamais atteindre le timeout provider (la requête cliente mourrait avant). Le TTL / heartbeat in-flight ne mesure **pas** cette durée : il ne sert qu’à purger les zombies.

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

### ZSET d’attente, une par provider

Distincte de la ZSET **in-flight** du §5. Uniquement si la requête **ne tient sur aucun provider**. Score = **priorité** + **timestamp** (haute prio et arrivée ancienne devant) — ce score sert à l’ordre, **pas** à l’expiration. On ne récupère que le **premier** (`ZRANGE` / claim Lua).

Cycle :

1. Entrer dans `qos:wait:{provider_id}` du provider least-busy.
2. Chaque seconde : heartbeat + « suis-je le premier **et** le slot (avec *mon* poids) est-il libre ? »
3. Oui → **un Lua** : `ZREM` wait + admission §5 (`ZADD` inflight + incr `qos:load`) + forward.
4. Non → attendre, jusqu’à `qos_queue_max_wait` / `qos_wait_timeout` → 503 + `Retry-After`.

Si le premier n’est jamais retiré (crash, disconnect, Redis), **toute la file est bloquée**.

`max_queue_size` : compter les waiters **par provider** (`ZCARD` de `qos:wait`). Si plafond atteint → **503 + `Retry-After`**, sans entrer en file.

`null` = pas de cap (tu assumes le scale). Un entier = file max, indépendant de `qos_wait_timeout`.

---

## Heartbeat

Le heartbeat couvre **toute la vie** de la requête (file et in-flight). Tant que le worker est vivant et la connexion active, on **repousse l’expiration**. Si le worker crash, si Redis ne répond plus, ou si le client coupe : plus de renouvellement → le prochain Lua **purge**.

On ne SCAN pas des clés `inflight:*`. En file, le score de `qos:wait` est l’ordre de priorité : l’expiration vit sur une **clé de présence** O(1). In-flight, le score de `qos:inflight` **est** l’expiration ; la charge reste `qos:load`.

| Phase | Structure | Compte dans `qos:load` | Heartbeat | Expire si heartbeat manqué |
|---|---|---|---|---|
| En file | Membre `qos:wait` + clé `qos:wait:hb:{provider_id}:{request_id}` | Non | Chaque **1 s** (même rythme que le poll) | **3 s** |
| In-flight | Membre `qos:inflight` (score = expiration) + poids dans `qos:weight` | Oui | Chaque **~10 s** : `ZADD` avec `now + ~30 s` | **~30 s** (≈ 3 heartbeats) |

### En file

Toutes les secondes : poll (« suis-je premier + y a-t-il de la place pour *mon* poids ? ») **et** `EXPIRE` de la clé de présence à 3 s.

Si le premier de `qos:wait` n’a plus de heartbeat → on le **retire**, on passe au suivant. On accepte de **perdre** une prioritaire zombie plutôt que de bloquer la file.

### In-flight

Dès l’admission atomique (Lua §5, éventuellement précédé du `ZREM` wait) :

1. `ZADD` inflight + `HSET` poids + incr `qos:load`, score `now + ~30 s`.
2. Tant que le forward tourne (y compris stream), un task asyncio **repousse le score** toutes les ~10 s.
3. Fin normale, disconnect FastAPI, ou erreur provider → Lua de sortie immédiat (le heartbeat n’est que le filet).

Un WhisperX de 5 min reste dans `qos:load` jusqu’à la fin. Un worker qui crash au milieu : au plus ~30 s de charge fantôme, puis la place se libère. C’est assez court pour ne pas figer le QoS, assez long pour encaisser un hic Redis sans sous-compter une requête encore vivante.

### Toujours supprimer dès qu’on peut

Le heartbeat ne remplace pas les sorties explicites :

| Événement | Action |
|---|---|
| Requête terminée (succès ou erreur provider) | Lua sortie in-flight (`ZREM` + `HDEL` + décr `qos:load`) |
| Client / proxy coupe (`disconnect`) | Lua sortie file ou in-flight |
| Plus premier / jeter après `qos_queue_max_wait` | `ZREM` wait + `DEL` clé de présence |
| Crash worker / Redis saturé malgré retry | Rien à exécuter → le prochain Lua d’admission purge à l’expiration |

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

- `load_balancing_strategy` : `least_busy` dès que le QoS est actif
- contrainte : tous les providers ont la **même** `qos_metric`

**Provider**

- `qos_metric` : `inflight` \| `audio_bytes` \| `null`
- `qos_limit`
- `qos_yellow_ratio` (défaut `0.9`)
- `qos_wait_timeout` (`null` \| `0` \| N)
- `qos_queue_max_wait`
- `timeout` (existant) : `qos_wait_timeout` et `qos_queue_max_wait` **&lt; timeout**
- Heartbeat in-flight : intervalle ~10 s, expiration ~30 s (pas un TTL calé sur la durée moyenne)

**Role**

- `priority` (migré depuis `user.priority`)

---

## Phasage

1. **V1 QoS + least busy** — ZSET in-flight + `qos:load`, Lua (requêtes **et** poids audio), wait/`null`/`0`, 503 + `Retry-After`, health par provider / meilleur statut router, plus d’API métriques pour ça.
2. **Priorisation** — ZSET + heartbeat + `role.priority`.
3. **Métrique tokens / pondération** — étude ; éventuellement revoir les rate limits.
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
