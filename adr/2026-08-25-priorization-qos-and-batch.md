# ADR — QoS, least-busy filtrant et file d’attente prioritaire

* **Status:** Proposed
* **Date:** 2026-08-25
* **Revised:** 2026-09-03
* **Authors:** Development Team
* **Related:**
  * [ADR 2026-01-07 — Migration to Clean Architecture](2026-01-07-clean-architecture-migration.md)
  * [AGENTS.md](../AGENTS.md)
* **Decision Outcome:** Une seule source de charge Redis (`ogl_qos:*`), admission atomique Lua, least-busy et saturation health alignés sur cette source ; liveness health distincte ; file prioritaire par router en Redis. Le batch est un ADR suivant.

---

## Context

OpenGateLLM doit **protéger chaque provider** (WhisperX crash si trop d’audio en parallèle ; vLLM se dégrade sous surcharge), **envoyer au moins chargé parmi ceux qui peuvent admettre la requête**, **afficher un health cohérent**, et **prioriser** quand il y a une vraie file.

### État actuel du code

| Mécanisme | Où | Comportement |
|---|---|---|
| Compteur in-flight | `INCR`/`DECR` sur `ogl_mg:inflight:{provider_id}` (`RedisProviderMetricsLogger`, et le chat legacy dans `BaseModelProvider`) | Ne redescend plus si Redis est saturé, si le worker crash, ou si le client coupe. |
| QoS | `apply_async_qos_policy` lit le compteur et refuse si `inflight > qos_limit` | Pas atomique avec le choix de provider ; pas de poids. |
| Least-busy | `RedisProviderLoadBalancer` lit le même `ogl_mg:inflight` | Choisit le min, **sans** filtre d’éligibilité au poids. |
| File prioritaire | `apply_routing_with_queuing` → Celery queue `ogl_qr.{router_id}` avec `x-max-priority: routing_max_priority + 1`, `user.priority` | Déjà une file par router. `configuration.dependencies.celery` est marqué `deprecated`. |
| Health | `GetHealthModelsUseCase` sonde `/metrics` (vLLM/Mistral) ou `/models` | Agrège le **pire** statut des providers d’un router. Un provider injoignable force le rouge. Endpoint public `GET /health/models`. |
| Chat | `api/endpoints/chat.py` (legacy) + `HttpProviderClient.forward_stream` → `NotImplementedError` | Compte encore sur `ogl_mg:inflight`. |
| Redis au boot | `scripts/gunicorn.conf.py` `on_starting` → `flushdb()` | Remet toute la DB Redis à zéro au démarrage du master, y compris pendant qu’il reste des workers. |
| Rate limiting | `RouterRateLimiter` (`ogl_rt:*`), RPM/TPM/RPD/TPD par rôle | Exécuté **avant** le forward dans `ProviderRequestForwardingUseCase`. |
| Limite audio | `audio_file_size_limit` (settings, global) vs `qos_limit` (provider) | Deux portées, aucune contrainte croisée. |

Sans file, la priorisation ne sert à rien. Sans plafond atomique qui tient compte du **poids de la requête qui arrive**, le least-busy peut coller une grosse requête au GPU le plus idle mais trop petit.

---

## Alternatives considered

| Option | Description | Décision |
|---|---|---|
| A | **Garder Celery/RabbitMQ** (`apply_routing_with_queuing`, queues `ogl_qr.*`) | Rejetée. Dépendance déjà `deprecated`. La file vit hors process FastAPI mais le QoS in-flight reste un `INCR` Redis non réversible ; les deux systèmes ne partagent pas une admission atomique. Coût ops (broker + workers) pour un wait que FastAPI peut tenir avec un `await`. |
| B | **Scheduler externe** (Celery seul, Redis Queue, Postgres `SKIP LOCKED`) | Rejetée pour le V1 interactif. Utile pour le **batch** (heures / jours, statut de job) — ADR suivant. |
| C | **Sémaphore in-process par worker** | Rejetée comme *seule* ligne de défense : elle ne coordonne pas les workers et ne protège pas le GPU. Conservée nulle part en V1. |
| D | **Redis + Lua**, une source de charge, file par router, least-busy filtrant | **Retenue.** |
| E | **Admission Python puis Lua de confirmation** (éligibilité + `argmin` en Python, retry si course) | Rejetée. Deux algorithmes, une course, un retry arbitraire. Un seul Lua pour le chemin direct et le claim. |

Le batch (exécuter des jobs quand les providers ont de la marge) **n’est pas décidé ici**. Il consommera `ogl_qos:load` une fois stable. Deux pistes restent ouvertes pour un ADR dédié : même ZSET à priorité basse et attente longue, ou drain séparé persisté dans Postgres.

---

## Decision

### 1. Une source de charge, trois consommateurs

On compte **nous-mêmes** dans Redis. Pas d’API métriques provider pour l’admission, le least-busy, ni la **saturation** health.

Aujourd’hui le QoS et le least-busy lisent un compteur Redis (`ogl_mg:inflight`) que l’on incrémente au début de la requête et décrémente à la fin (`INCR` / `DECR`). Le **contrôle de limite** et l’**incrément** sont deux allers-retours distincts : deux requêtes peuvent toutes les deux voir « il reste de la place » et entrer. Un crash laisse le compteur trop haut indéfiniment.

On remplace ça par un nombre unique `load(p)` — la charge actuelle du provider `p` et une limite de charge `qos_limit(p)` Ces deux valeurs sont définies au niveau du provider et expriméescal en nombre de requêtes.

 Trois mécanismes posent chacun une question différente sur ce même nombre :

| Mécanisme | Question | Condition |
| --- | --- | --- |
| Admission | Cette requête a-t-elle le droit de **démarrer** sur `p` sans dépasser sa capacité ? | `if at least one provider is eligible: load(p)` ≤ `qos_limit(p)` |
| Load balancer (least-busy) | Lequel des providers du router doit prendre la requête ? | `min(load(p) for p in providers)` |
| Saturation health | À quel point `p` est-il **plein** ? | `load(p) / qos_limit(p)` → vert / orange / rouge (voir §7). |

`load(p)` dépend de la métrique du router.

**Métrique `inflight` : on compte les requêtes en cours, pas un compteur à côté.**

Chaque provider a une ZSET Redis `ogl_qos:inflight:{provider_id}`. C’est un ensemble trié : **un membre = une requête encore en train de tourner** (`request_id`), le score est la date d’expiration du heartbeat. `load(p)` est simplement le nombre de membres : `ZCARD` de cette ZSET.

On ne tient **pas** un entier séparé (`INCR` / `DECR` comme aujourd’hui). Ce second chiffre serait une copie de `ZCARD`. Les deux peuvent diverger : worker crashé, `DECR` perdu, Redis saturé — exactement le bug actuel. La ZSET existe déjà pour savoir *quelles* requêtes sont vivantes et les faire expirer ; la compter *est* la charge.

**Après purge.** Avant le `ZCARD`, le Lua retire les membres dont l’expiration est dépassée (plus de heartbeat : crash, disconnect). Sans ça, un zombie resterait dans la ZSET : `load(p)` trop haut, on refuserait des requêtes alors que le GPU est libre. La fenêtre fantôme, c’est au plus l’intervalle d’expiration in-flight (~30 s), pas « jusqu’au prochain redémarrage ».

**Métrique `audio_bytes`.** Le nombre de requêtes ne suffit plus (10 Mo ≠ 400 Mo) : `load(p)` est alors un entier `ogl_qos:load:{provider_id}`, somme des poids du hash. Voir §5.

Limites / in-flight **par provider** (1 GPU ≠ 8 GPU). File d’attente **par router**. Tous les providers d’un router partagent la **même** `qos_metric` parce que la métrique vit sur le **router**, pas sur le provider.

### 2. Périmètre V1

| Dans le V1 | Hors V1 |
|---|---|
| Use cases model-forward **clean architecture** : audio, embeddings, OCR, rerank | Chat (`api/endpoints/chat.py`) jusqu’à sa migration CA |
| Métriques `inflight` et `audio_bytes` | Tokens in-flight, pondération par codec / durée décodée |
| File prioritaire Redis + `role.priority` | Batch |
| Skip head-of-line pour `audio_bytes` | Aging anti-famine des gros jobs |
| Redis standalone | Redis Cluster (non-objectif ; hash tags `ogl_qos:{id}:…` si un jour) |

**Chat.** Tant que le chat est legacy, il reste sur `ogl_mg:inflight`. Un provider appartient à un seul router : pas de double comptage sur le même provider. La migration CA du chat **doit** brancher `QosGate` dans le même changement que la suppression du `INCR`/`DECR` legacy — pas de période où les deux coexistent sur un router QoS. `HttpProviderClient.forward_stream` est un prérequis de cette migration, pas de ce V1.

**Celery.** Les endpoints CA n’appellent plus `apply_routing_with_queuing`. Quand le chat migre, les queues `ogl_qr.*` et la dépendance Celery sont retirées. Ne pas activer `qos_mode=queue` et Celery sur le même router.

### 3. Métrique, poids, rejet immédiat

| V1 | Plus tard |
|---|---|
| Nombre de requêtes concurrentes **ou** octets audio | Tokens in-flight, durée décodée, poids par codec |

Exemple : limite 500 Mo, occupé 300 Mo, requête 300 Mo → `300 + 300 > 500` → la requête **n’entre pas**.

**Rejet immédiat (413)** si `poids > max(qos_limit(p))` pour les providers du router : la requête n’est éligible nulle part, jamais. Elle ne doit pas occuper la file jusqu’au timeout pour un 503 trompeur.

Le poids n’est connu qu’après réception du corps (`SpooledTemporaryFile`). Si `Content-Length` est présent et déjà `> max(qos_limit)`, refuser **avant** de spouler.

**Validation** (create / update provider, bootstrap) : si `qos_metric = audio_bytes` et `audio_file_size_limit` est défini, chaque `qos_limit` du router doit être `≥ audio_file_size_limit`. Sinon un fichier accepté par l’API ne rentre dans aucun provider.

**Limite assumée.** WhisperX coûte à la *durée*, pas à la taille. 300 Mo de WAV ≈ 30 min ; 300 Mo d’Opus ≈ des dizaines d’heures. `audio_bytes` est un proxy imparfait, suffisant pour un V1, pas une protection exacte contre le crash. Piste suivante : durée décodée ou pondération par codec.

### 4. Admission : un seul Lua

Pas d’éligibilité Python suivie d’un Lua de confirmation. Le script `try_admit` reçoit `(provider_id, qos_limit)*`, `request_id`, `poids` :

1. Purger l’in-flight expiré de **chaque** provider du router (retrancher les poids, `HDEL`, `ZREMRANGEBYSCORE`).
2. Si `poids > max(qos_limit)` → `TOO_HEAVY` (le caller mappe 413, sans file).
3. Éligibles = `load(p) + poids ≤ qos_limit(p)`. Si vide → `FULL`.
4. `p* = argmin occupation(p)` parmi les éligibles.
5. Admettre sur `p*` : `ZADD` in-flight (score = `now + ttl`), `HSET` poids, incrémenter `load` si `audio_bytes` — atomique.
6. Retourner `ADMITTED, p*`.

Le claim de file (§6) **réutilise ce script**, avec en plus : ne retirer le waiter et n’admettre que si la requête est claimable (tête, ou premier qui rentre — skip HOL).

`occupation(p) = load(p) / qos_limit(p)` — comparable entre 1 GPU et 8 GPU.

Sous la limite (au moins un éligible) : **pas de ZSET d’attente**. Prioritaire et non prioritaire passent tout de suite.

### 5. Modèle Redis

Préfixe `PREFIX__REDIS_QOS = "ogl_qos"` (aligné sur `ogl_mg`, `ogl_ts`, `ogl_rt`, `ogl_qr` dans `api/utils/variables.py`).

**Par provider**

| Clé | Rôle |
|---|---|
| `ogl_qos:inflight:{provider_id}` | ZSET : membre = `request_id`, score = **timestamp d’expiration** |
| `ogl_qos:weight:{provider_id}` | Hash : `request_id` → poids (purge / sortie) |
| `ogl_qos:load:{provider_id}` | Entier, **seulement** si `audio_bytes`. Pour `inflight`, `load = ZCARD` après purge. |

**Par router**

| Clé | Rôle |
|---|---|
| `ogl_qos:wait:{router_id}` | ZSET d’attente. Score = ordre seulement, **pas** d’expiration. |
| `ogl_qos:wait:hb:{router_id}:{request_id}` | Présence / heartbeat (`EXPIRE`). |
| `ogl_qos:wait:weight:{router_id}` | Hash : `request_id` → poids |
| `ogl_qos:wait:load:{router_id}` | Somme des poids en file (unité de `qos_metric`) |
| canal `ogl_qos:free:{router_id}` | Pub/sub à la libération d’un slot |

Pas de `SCAN` / `KEYS`. Redis Cluster : non-objectif V1 (le Lua touche N providers + le router).

**Score de la ZSET d’attente**

Le domaine garde « entier plus élevé = plus prioritaire » (`role.priority`, plafond `routing_max_priority`, aujourd’hui 0–10). Redis `ZRANGE 0 0` renvoie le **plus petit** score : il faut encoder, pas additionner.

```
SCORE_SCALE = 10**13          # timestamp_ms < SCALE jusqu’à ~2286
score = -priority * SCORE_SCALE + timestamp_ms
```

`ZRANGE 0 0` → priorité la plus haute, puis FIFO. `|score| ≤ 1.1 × 10¹⁴ < 2⁵³` (9 × 10¹⁵) : entier exact en float64. Une addition littérale `priority + timestamp_ms` rend la priorité inopérante (epoch ms ≈ 1,7 × 10¹²).

**Réconciliation.** `ogl_qos:load` est une dénormalisation du hash. Si un décrément la ferait passer sous 0, le Lua la **reconstruit** (`HVALS` → somme) dans le même round-trip. Pas de job périodique en V1.

**TTL des clés.** `inflight` / `load` / `weight` n’ont **pas** de TTL de clé. Exiger `maxmemory-policy noeviction` (ou équivalent qui n’évince pas ces clés). Une éviction LRU du hash ou de la ZSET laisserait une charge fantôme permanente.

**`flushdb()`.** Retirer `client.flushdb()` de `scripts/gunicorn.conf.py` `on_starting`. Le heartbeat / expiration remplace le nettoyage des compteurs zombies. Un `flushdb` au rolling restart met `load` à 0 pendant que d’autres workers ont encore des forwards → sur-admission garantie.

### 6. File d’attente et priorisation

Priorité : aujourd’hui `user.priority`. Cible : **`role.priority`**. Les utilisateurs héritent du rôle. Le plafond `routing_max_priority` reste.

On n’enfile **que** si `try_admit` a renvoyé `FULL` et `qos_mode = queue`.

1. Si `wait:load + poids > max_queue_size` → 503 + `Retry-After`, sans entrer. `max_queue_size` est dans l’**unité de la métrique** (nombre de requêtes ou octets), pas un simple `ZCARD` : sous surcharge audio, plafonner les octets en file, pas seulement le nombre de waiters.
2. `ZADD` wait (score encodé §5) + `HSET` poids + incr `wait:load` + créer la clé de présence.
3. Attendre un message `ogl_qos:free:{router_id}` ou le timeout de heartbeat ; renouveler la présence ; **si et seulement si** `ZRANGE 0 0` est soi (chemin `inflight`) ou si on est encore dans la ZSET (chemin skip-HOL), appeler le Lua de claim.
4. Succès → forward sur `p*`.
5. Timeout `qos_wait_timeout` → sortie file + 503 + `Retry-After`.

Seul le waiter concerné paie le Lua de claim ; les autres font un `ZRANGE 0 0` O(log n) et se rendorment. La purge N-providers ne tourne pas 2 000 fois par seconde.

**Waiter évincé.** Le claim Lua retire un membre dont la clé de présence a expiré. Le client, lui, peut encore poller. Après chaque cycle, le waiter teste `EXISTS` de sa clé hb **et** `ZSCORE` dans la wait ZSET. S’il a disparu et que `qos_wait_timeout` n’est pas écoulé : **ré-enfiler** (même priorité, nouveau `timestamp_ms` — il perd sa place FIFO parmi ses pairs, c’est le prix du hoquet). Sinon 503. Sans cette règle, un GC / tokenizer / spool de 10 s produit un 503 après avoir perdu sa place.

**Heartbeat : comment on sait qu’une requête est encore vivante.**

Le problème que l’on corrige : aujourd’hui, si le worker crash ou si le client coupe, personne n’exécute le `DECR`. La charge reste trop haute jusqu’au redémarrage. On a besoin d’un filet qui n’exige **aucun code après la mort** du process.

Tant que le worker vit et que la connexion HTTP est ouverte, il **rappelle régulièrement Redis** (« je suis encore là »). Si les rappels s’arrêtent, Redis considère la requête morte et le prochain Lua la retire. Ça s’appelle un heartbeat.

**Qui met à jour le heartbeat in-flight, et comment.**

Ce n’est **pas** Redis tout seul, ni un cron, ni un worker Celery. C’est le **même process FastAPI** qui sert cette requête HTTP.

Au moment où `try_admit` réussit, le Lua insère le membre une première fois :

```
ZADD ogl_qos:inflight:{provider_id}  {now_ms + 30_000}  {request_id}
```

Le score n’est pas un rang : c’est **la date (ms) à laquelle on pourra considérer la requête morte** si plus personne n’écrit. La clé ZSET n’a pas de `EXPIRE` Redis — Redis ne va pas effacer le membre tout seul.

Pendant le `forward_request` (l’appel HTTP au provider, qui peut durer des minutes), `RedisQosGate` lance une **tâche asyncio** à côté de cet `await`. Toutes les ~10 s, tant que le forward n’est pas fini, cette tâche refait :

```
ZADD ogl_qos:inflight:{provider_id}  {now_ms + 30_000}  {request_id}
```

`ZADD` sur un membre **déjà présent** ne crée pas un doublon : Redis **remplace le score**. On recule donc l’expiration de 30 s à chaque rappel. Un WhisperX de 5 min : le membre reste dans la ZSET, `ZCARD` / `load` ne baisse pas.

Quand le forward se termine (succès, erreur, disconnect), le use case appelle `release` : on **annule** la tâche asyncio et on retire le membre (`ZREM` + retrancher le poids). Plus de heartbeat.

Si le process meurt au milieu, la tâche s’arrête avec lui. Personne ne `ZADD`. Au bout de 30 s le score est dans le passé.

Le **prochain** Lua `try_admit` / claim sur ce provider les ramasse avec `ZRANGEBYSCORE`. Une ZSET est triée par score. Cette commande ne prend pas « les n premiers » (`ZRANGE`) : elle renvoie les membres dont le **score est dans un intervalle**. Ici le score *est* la date d’expiration, donc :

```
ZRANGEBYSCORE ogl_qos:inflight:{provider_id}  -inf  {now_ms}
```

= « tous les `request_id` dont l’expiration est déjà passée ». Le Lua les `ZREM`, retranche leurs poids, et `load` redescend. Redis ne « ping » rien et n’efface rien tout seul : c’est le prochain client qui, en voulant entrer, ramasse les morts.

**Deux requêtes qui purgent en même temps.** Redis exécute les commandes (et les scripts Lua) **une par une**, sur un seul thread. Deux `try_admit` ne s’entrelacent jamais : A purge + admet entièrement, puis B démarre.

Le `ZREM` d’un membre déjà parti est inoffensif (no-op). Le conflit réel, ce serait de **retrancher deux fois** le même poids de `ogl_qos:load` (`audio_bytes`). Ça n’arrive pas : B, en reprenant la main, refait `ZRANGEBYSCORE` et ne voit plus ces membres — rien à retrancher. C’est pour ça que purge, lecture de `load` et admission sont **le même** script, pas trois allers-retours Python. En Python, A et B liraient les mêmes zombies, puis décrémenteraient chacun : `load` trop bas, sur-admission.

**Différence avec la file.** En file, le heartbeat n’est pas le score de `ogl_qos:wait` (ce score sert à l’ordre de priorité). C’est une **clé à part** `ogl_qos:wait:hb:{router_id}:{request_id}` : le worker fait `SET` + `EXPIRE 10`. Redis peut alors supprimer la clé tout seul ; le claim Lua teste `EXISTS` et évince le waiter si elle a disparu.

Le heartbeat n’est **que** le filet. Dès qu’on peut sortir proprement, on le fait tout de suite, sans attendre l’expiration :

* requête terminée (succès ou erreur provider) ;
* client / proxy qui coupe (`disconnect`) ;
* timeout de file.

Dans ces cas : Lua inverse (retirer le membre, retrancher le poids) **et** `PUBLISH` sur `ogl_qos:free:{router_id}` pour réveiller les waiters. Si on ne publiait pas, ils attendraient le prochain timeout de heartbeat pour retenter.

**Head-of-line : une grosse requête en tête de file ne doit pas bloquer les petites.**

La file est ordonnée par priorité, puis FIFO. « Head-of-line » (HOL), c’est le défaut classique : on ne sert **que** la tête. Si la tête ne rentre nulle part, tout le monde derrière attend.

Exemple `audio_bytes`, limite 500 Mo, déjà 200 Mo en vol :

| Place | Requête | Rentre maintenant ? |
|---|---|---|
| 1 (tête) | 400 Mo | Non (`200 + 400 > 500`) |
| 2 | 10 Mo | Oui (`200 + 10 ≤ 500`) |

Sans skip : la 10 Mo attend que la 400 Mo parte — alors qu’il y a de la place. C’est exactement le cas WhisperX / gros fichiers.

**V1 `audio_bytes` : skip.** Le claim ne prend pas forcément la tête. Il parcourt la file (dans l’ordre de priorité) et admet **le premier waiter qui rentre** sur au moins un provider. Ici, la 10 Mo part ; la 400 Mo reste en tête jusqu’à ce qu’un provider ait 400 Mo libres.

**V1 `inflight` : pas de skip.** Chaque requête pèse 1. Si la tête ne rentre pas, `load` est déjà à la limite : personne derrière ne rentre non plus. Parcourir la file ne changerait rien.

**Limitation V1 (pas d’aging).** L’inverse du HOL : tant que des petits jobs arrivent et remplissent la capacité, un gros job peut **ne jamais** partir. On l’accepte en V1. Plus tard : vieillir les gros (monter leur priorité s’ils sont skippés trop longtemps) pour ne pas les affamer.

### 7. Health : liveness ≠ saturation

Deux dimensions. Un provider **injoignable** a `load = 0` : en saturation seule, il serait vert. C’est inacceptable.

| Dimension | Source | Rouge si |
|---|---|---|
| Liveness | Sonde déjà en place (`/metrics` ou `/models`) | Provider injoignable / réponse invalide |
| Saturation | `occupation = load / qos_limit` (si `qos_mode ≠ off`) | `≥ 1.0` |

Seuil orange configurable (défaut 90 % de la limite) : `<` orange → vert saturation ; `≥` orange et `< 100 %` → orange ; `≥ 100 %` → rouge saturation.

**Par provider** : le pire des deux. **Par router** (`GET /health/models`) : le **pire** statut des providers — sémantique actuelle, endpoint public déjà consommé. Ne pas inverser en « meilleur statut » : un router 7 rouges / 1 vert doit rester rouge.

`qos_mode = off` : pas de saturation QoS ; la liveness seule reste.

### 8. Attente, 503, `Retry-After`

Paramètres **router** (V1 = deux leviers, pas trois) :

| Paramètre | Rôle |
|---|---|
| `qos_mode` | `off` \| `reject` \| `queue` |
| `qos_wait_timeout` | Obligatoire si `queue`. Durée max de l’attente HTTP **et** dans la ZSET. Doit rester `< min(timeout)` des providers du router (défaut provider 300 s). |
| `max_queue_size` | Cap de `wait:load` dans l’unité de `qos_metric`. `null` = pas de cap. |

`qos_mode` :

| Valeur | Comportement |
|---|---|
| `off` | Pas d’admission. Kill switch. WhisperX n’est **pas** protégé. |
| `reject` | `FULL` → 503 immédiat, pas de ZSET. |
| `queue` | `FULL` → file jusqu’à `qos_wait_timeout`. |

Pas de tri-état `qos_wait_timeout = null` qui signifierait à la fois « pas de file » et « pas de 503 » : le nom se lirait comme « attendre indéfiniment » et désactiverait la protection.

Erreur : **503** + `Retry-After` (secondes). Le header **ne promet pas un slot**.

```
Retry-After = clamp(1, qos_wait_timeout, ceil((1 + depth) * (0.5 + rand())))
```

`depth = ZCARD` si `inflight`, `ceil(wait:load / max(1, poids moyen récent ou poids de la requête))` si `audio_bytes` — en V1, plus simple : `depth = ZCARD` dans les deux cas. Jitter 50 %–150 % anti-stampede. Pas de timeserie `ogl_ts:latency`, pas de p50, pas de « provider de référence ». Un `D × (charge + file + poids) / limite` mélange durée d’une requête et ratio d’octets ; il n’est correct que si `D` est le temps de drainer une capacité pleine, ce que le p50 n’est pas.

### 9. Redis down, kill switch

La prémisse audio est qu’un excès de parallélisme **crash** WhisperX. Fail-open sur Redis down transformerait une panne Redis en crash GPU.

| Métrique | Redis down | Rationale |
|---|---|---|
| `audio_bytes` | **Fail-closed** → 503 | C’est la raison d’être de l’ADR. |
| `inflight` | **Fail-open** | vLLM encaisse ; on préfère servir. |

Kill switch : `qos_mode = off` (router) et/ou un flag settings global. À utiliser si le chemin Lua se comporte mal, pas comme équivalent de « Redis down » sur l’audio.

### 10. Insertion clean architecture

Dépendance : `infrastructure → use_cases → domain`. Session : **autocommit** (model-forward). L’attente Redis a lieu **après** les lectures Postgres, comme le forward — jamais `idle in transaction`.

| Pièce | Emplacement |
|---|---|
| Erreurs | `api/domain/provider/errors.py` : `QosRejectedError`, `QosTimeoutError`, `QosTooHeavyError`, `QosUnavailableError` |
| Port | `api/domain/provider/_qosgate.py` — `QosGate` : `admit(...)`, `release(...)`, `heartbeat(...)` |
| Adapter | `api/infrastructure/redis/_redisqosgate.py` — Lua + pub/sub + boucle d’attente |
| Load balancer | `find_best_provider` **n’existe plus** pour un router `qos_mode ≠ off` : le Lua choisit `p*`. Shuffle sans QoS inchangé. |
| Use case | `ProviderRequestForwardingUseCase._send_request` : rate limit (déjà fait) → `qos_gate.admit` → forward → `release` |
| DI | Factory autocommit, à côté de `_authentication_key_repository` |
| HTTP | 413 trop lourd, 503 file/timeout/Redis down (`audio_bytes`), `Retry-After` |
| Config | `qos_metric` + `qos_mode` + `qos_wait_timeout` + `max_queue_size` sur **Router** ; `qos_limit` (+ `qos_yellow_ratio` si on le garde local) sur **Provider** |

La boucle d’attente vit dans l’adapter (`admit` se suspend), pas dans l’endpoint. Le use case reste linéaire : `match admit` → forward → release.

**Ordre rate limit / QoS.** Inchangé : RPM/TPM/RPD/TPD **à l’entrée** de la requête (avant la file). Le temps en file **ne re-vérifie pas** et **ne re-compte pas** le RPM. Le TPM d’output reste calculé au retour du forward. Une requête qui attend 60 s a consommé 1 RPM à t = 0.

### 11. Config

**Router**

- `qos_mode` : `off` \| `reject` \| `queue`
- `qos_metric` : `inflight` \| `audio_bytes` (ignoré si `off`)
- `qos_wait_timeout` (si `queue`)
- `max_queue_size` (`null` \| nombre dans l’unité de la métrique)
- `load_balancing_strategy` : `least_busy` dès que `qos_mode ≠ off` (filtrant, dans le Lua)

**Provider**

- `qos_limit` (capacité infra)
- `qos_yellow_ratio` (défaut `0.9`)
- `timeout` (existant)

**Role**

- `priority` (migré depuis `user.priority`)

**Ops**

- Redis `maxmemory-policy noeviction`
- Plus de `flushdb()` au start gunicorn
- Heartbeat file 2 s / 10 s ; in-flight 10 s / 30 s

### 12. Migration `user.priority` → `role.priority`

1. Alembic : ajouter `role.priority` (`NOT NULL`, default 0, `ge=0`, `le=routing_max_priority`).
2. Backfill : `role.priority = MAX(user.priority)` des utilisateurs de ce rôle (on ne rétrograde personne silencieusement). Les écarts intra-rôle disparaissent : le rôle devient la source de vérité. Documenter l’impact ops.
3. Lire `role.priority` dans l’admission ; cesser d’écrire `user.priority`.
4. Retirer `user.priority` (Alembic suivant ou le même si le déploiement est atomique).
5. API : `/v1/admin/roles` expose et accepte `priority` ; `/v1/admin/users` ne le prend plus ; `/v1/me` n’expose pas un champ user (aujourd’hui le GET CA ne le renvoie déjà pas). Playground : priorité sur le formulaire rôle, plus sur l’utilisateur.

### 13. Tests

Chaque couche teste **sa** responsabilité (`AGENTS.md`).

| Couche | Contenu |
|---|---|
| Unit use case | Chaque branche de `admit` (ADMITTED, FULL→reject, FULL→queue→timeout, TOO_HEAVY, Redis down fail-closed / fail-open, `qos_mode=off`) |
| Unit domaine | Encodage du score ZSET (ordre prio + FIFO, bornes float64) |
| Intégration Redis | Harnais Redis réel : Lua admit/claim, course entre deux waiters, purge zombie, éviction + ré-enfile, skip HOL, `load` reconstruit si négatif, `PUBLISH` réveille |
| Intégration endpoint | 413, 503 + `Retry-After`, auth, `qos_mode=off` |
| Health | Provider mort + `load=0` → rouge ; 7 rouges / 1 vert → rouge router |
| ForwardScenario | Audio (et les autres CA) : connexion Postgres relâchée pendant l’attente **et** pendant le forward |

### 14. Observabilité

Prometheus (namespace `ogl`, déjà branché) :

* `ogl_qos_admit_total{router, result}` — `admitted`, `queued`, `rejected`, `too_heavy`, `timeout`, `redis_down`
* `ogl_qos_queue_depth{router}` / `ogl_qos_queue_load{router}`
* `ogl_qos_wait_seconds` (histogramme)
* `ogl_qos_load{provider}`
* `ogl_qos_purge_total{provider}`
* `ogl_qos_lua_errors_total`
* `ogl_qos_evicted_requeued_total{router}`

---

## Consequences

**Plus facile**

- Un seul chiffre à raisonner pour « est-ce que ça rentre », « qui est le moins chargé », « à quel point c’est saturé ».
- Plus de `INCR` orphelin : crash worker → expiration → purge au prochain Lua.
- Plus de Celery pour le trafic interactif CA.
- Skip HOL : le cas WhisperX/Visio (gros fichier en tête, petits derrière) n’est pas livré cassé.

**Plus difficile / à accepter**

- Redis devient critique pour l’audio (fail-closed). Le kill switch désactive la protection.
- FastAPI garde la connexion HTTP pendant l’attente : FD uvicorn / ingress / LB, fichiers spoulés sur disque, timeouts nginx qui coupent avant le 503. `max_queue_size` (en octets pour l’audio) est le plafond, pas le CPU.
- `audio_bytes` reste un mauvais proxy de la durée GPU.
- Un gros job peut être affamé (skip HOL sans aging).
- Le chat legacy et les endpoints CA n’ont pas la même admission tant que le chat n’est pas migré.
- Ops : `noeviction`, plus de `flushdb` au boot, Redis standalone.

**Connexions et Postgres.** Chaque waiter occupe un FD. L’attente doit rester après relâchement de la session Postgres (`AutocommitSession`) — contrainte dure, déjà le contrat des model-forward.

---

## Phasage

1. **V1** — Port `QosGate` + Lua unique + clés `ogl_qos:*` ; `qos_mode` / `qos_metric` sur le router ; métriques `inflight` et `audio_bytes` ; 413 trop lourd ; fail-closed audio / fail-open inflight ; health liveness + saturation, agrégation pire statut ; retirer `flushdb()` ; tests Redis + Prometheus. Brancher les use cases CA (audio d’abord).
2. **Priorisation** — ZSET d’attente, claim + pub/sub, skip HOL, `role.priority` + Alembic, heartbeat 2 s / 10 s, ré-enfilement si éviction.
3. **Chat CA** — `forward_stream` + `QosGate` ; suppression Celery / `ogl_mg:inflight` legacy.
4. **Ensuite** — durée / codec ; aging HOL ; tokens in-flight ; ADR batch.
