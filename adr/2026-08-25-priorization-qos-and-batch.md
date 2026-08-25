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

- On compte **nous-mêmes** dans Redis.
- Admission **atomique Lua**, en tenant compte du **poids de la requête qui arrive**.
- On **préfère jeter** une requête bloquante plutôt que de geler le système.
- Health et QoS : **même source Redis**, pas d’API métriques provider.
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
   `occupation = charge / limite` (comparable même si les limites diffèrent).
2. Tenter l’**admission atomique** sur ce provider (**charge + poids requête ≤ limite**).
3. Si ça ne passe pas : **tester les autres** par occupation croissante (un petit provider à 10 % peut ne pas tenir 300 Mo alors qu’un gros à 40 % si).
4. Si **aucun** ne peut admettre → file d’attente du **moins chargé** (ZSET de ce provider), sauf si l’attente est désactivée / à 0.

Sous la limite (la requête **tient** sur au moins un provider) : **pas de ZSET**, prioritaire et non prioritaire passent tout de suite.

---

## 3. Health

Statut **par provider**, mêmes compteurs que le QoS.

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

On n’a pas la durée réelle des requêtes en cours. On utilise le **TTL des clés in-flight** (durée moyenne un peu majorée) et le **taux d’occupation** du provider visé (ou du moins chargé si aucun n’admet) :

```
Retry-After = clamp(
  1,
  timeout_provider - 1,
  ceil( ttl_inflight × (charge + poids) / limite )
)
```

Exemples avec `ttl_inflight = 60 s`, limite 500 Mo :

| Charge | Requête | Occupation | Retry-After |
|---|---|---|---|
| 300 Mo | 300 Mo | 1,2 | 72 s |
| 500 Mo | 1 req / négligeable | 1,0 | 60 s |
| 100 Mo | 50 Mo (admise) | — | pas de 503 |

Idée : à saturation, attendre **à peu près le temps d’une génération de requêtes** avant de réessayer, sans jamais atteindre le timeout provider (la requête cliente mourrait avant).

---

## 5. Comptage : une clé Redis par requête, avec TTL

Un `INCR`/`DECR` global ne redescend plus si :

| Incident | Mitigation |
|---|---|
| Client / proxy coupe | Disconnect FastAPI → delete de la clé |
| Pool Redis saturé | Retry (jamais 100 %) |
| Worker crash | **TTL** : plus de code à exécuter |

**Modèle :** une **clé par requête**, expiration, charge = **nombre de clés** ou **somme des poids** (JSON : octets, plus tard tokens).

- TTL in-flight ≈ durée moyenne, un peu au-dessus (ordre de 1 min).
- Worker crash → les clés meurent au TTL. On **sous-admet** un moment, le temps que l’infra revienne — utile (WhisperX, GPU).

Admission Lua : lire la charge, ajouter le poids, créer la clé **si et seulement si** ≤ limite. Pas d’overshoot volontaire.

---

## 6. File d’attente et priorisation

### Priorité

Aujourd’hui : `user.priority`.  
Cible : **`role.priority`** (entier, plus élevé = plus prioritaire). Les utilisateurs héritent du rôle. Le plafond `routing_max_priority` reste.

### ZSET, un par provider

Uniquement si la requête **ne tient sur aucun provider**. Sorted set Redis : score = **priorité** + **timestamp** (haute prio et arrivée ancienne devant). On ne récupère que le **premier** (`ZRANGE` / claim Lua).

Cycle :

1. Entrer dans la ZSET du provider least-busy.
2. Chaque seconde : heartbeat + « suis-je le premier **et** le slot (avec *mon* poids) est-il libre ? »
3. Oui → claim atomique, clé in-flight, forward.
4. Non → attendre, jusqu’à `qos_queue_max_wait` / `qos_wait_timeout` → 503 + `Retry-After`.

Si le premier n’est jamais retiré (crash, disconnect, Redis), **toute la file est bloquée**.

`max_queue_size` : compter les waiters **par provider** (même Redis que la ZSET : `ZCARD`). Si plafond atteint → **503 + `Retry-After`**, sans entrer en file.

`null` = pas de cap (tu assumes le scale). Un entier = file max, indépendant de `qos_wait_timeout`.

Voici la section **Heartbeat** à coller à la place de l’ancienne. Le TTL « durée moyenne un peu majorée » disparaît : la clé ne vit que tant qu’on la renouvelle, **en file et in-flight**.

Rule : sI Redis down, on laisse passer. 

---

## Heartbeat

La clé Redis de la requête existe **dès l’entrée en file** (ou dès l’admission si on ne passe pas par la ZSET). Elle n’a **pas** un TTL calé sur la durée moyenne d’une requête. Un TTL long sous-compte les jobs longs (stream, transcription) dès qu’il expire alors que le travail continue ; un TTL court laisse des fantômes après un crash.

À la place : un **heartbeat** sur toute la vie de la requête. Tant que le worker est vivant et la connexion active, on **renouvelle le TTL**. Si le worker crash, si Redis ne répond plus, ou si le client coupe : plus de renouvellement → la clé expire toute seule.

| Phase | Rôle de la clé | Heartbeat | TTL (expire si heartbeat manqué) |
|---|---|---|---|
| En file | Présence dans la ZSET (ne compte **pas** dans la charge QoS) | Chaque **1 s** (même rythme que le poll) | **3 s** |
| In-flight | Compte dans la charge QoS (poids : 1 requête ou octets) | Chaque **~10 s** | **~30 s** (≈ 3 heartbeats) |

On peut garder **deux clés** (ou deux préfixes) : `queue:{provider}:{request_id}` et `inflight:{provider}:{request_id}`. Au claim, on crée l’in-flight et on supprime la clé de file. Seules les clés `inflight:*` entrent dans le Lua d’admission.

### En file

Toutes les secondes : poll (« suis-je premier + y a-t-il de la place pour *mon* poids ? ») **et** `EXPIRE` à 3 s.

Si le premier de la ZSET n’a plus de heartbeat → on le **retire**, on passe au suivant. On accepte de **perdre** une prioritaire zombie plutôt que de bloquer la file.

### In-flight

Dès l’admission atomique (Lua : premier + place + claim) :

1. Créer la clé `inflight` avec le poids, TTL ~30 s.
2. Tant que le forward tourne (y compris stream), un task asyncio **renouvelle** ce TTL toutes les ~10 s.
3. Fin normale, disconnect FastAPI, ou erreur provider → **delete** immédiat de la clé (le heartbeat n’est que le filet).

Un WhisperX de 5 min reste compté jusqu’à la fin. Un worker qui crash au milieu : au plus ~30 s de charge fantôme, puis la place se libère. C’est assez court pour ne pas figer le QoS, assez long pour encaisser un hic Redis sans sous-compter une requête encore vivante.

Lua inchangé sur le claim : « premier + place pour ce poids + création in-flight atomique ».

### Toujours supprimer dès qu’on peut

Le heartbeat ne remplace pas les deletes explicites :

| Événement | Action |
|---|---|
| Requête terminée (succès ou erreur provider) | `DEL` in-flight |
| Client / proxy coupe (`disconnect`) | `DEL` file ou in-flight |
| Plus premier / jeter après `qos_queue_max_wait` | Retirer de la ZSET + `DEL` clé de file |
| Crash worker / Redis saturé malgré retry | Rien à exécuter → expiration du TTL |

Retry Redis conservé sur `EXPIRE` / `DEL`. Si un renouvellement in-flight échoue plusieurs fois, on **préfère jeter** (arrêter le forward si possible, ou laisser mourir la clé) plutôt que de garder une charge fantôme indéfiniment.


---

Le `Retry-After` ne peut plus s’appuyer sur « TTL = durée moyenne ». Il reste le taux d’occupation, et éventuellement un **percentile de durée observé** (métrique à part, pas le TTL des clés).
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
- TTL in-flight : dérivé du timeout ou champ dédié

**Role**

- `priority` (migré depuis `user.priority`)

---

## Phasage

1. **V1 QoS + least busy** — clés TTL, Lua (requêtes **et** poids audio), wait/`null`/`0`, 503 + `Retry-After`, health par provider / meilleur statut router, plus d’API métriques pour ça.
2. **Priorisation** — ZSET + heartbeat + `role.priority`.
3. **Métrique tokens / pondération** — étude ; éventuellement revoir les rate limits.
4. **Batch** — option A ou B + persistance job.

---

Un point encore utile à trancher plus tard, pas bloquant pour la note : le TTL in-flight est-il **un champ provider** ou **dérivé du timeout** (ex. `timeout / 5`) ? Le `Retry-After` en dépend.


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
