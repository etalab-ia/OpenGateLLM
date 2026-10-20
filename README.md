# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/etalab-ia/OpenGateLLM/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                  |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|-------------------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| api/app.py                                                                            |       62 |        6 |       12 |        5 |     85.14% |28, 57-58, 87, 94, 99 |
| api/dependencies.py                                                                   |      201 |       86 |        6 |        0 |     55.56% |81-90, 94-96, 100-102, 107, 111, 116, 120, 124, 128, 132, 136, 140, 144, 148, 152, 156, 165, 173, 177, 181, 185, 189, 193, 197, 201, 205, 213-215, 229, 254, 275, 290, 308, 325, 344, 354, 361, 365, 369, 373, 378, 382, 387, 392, 396, 409, 425, 429, 433, 437, 441, 446, 450, 454, 458, 462, 475, 491, 499, 507, 515, 521, 528, 534, 540, 546, 552, 562, 570, 577, 583, 589 |
| api/domain/audio/entities.py                                                          |       31 |        1 |        0 |        0 |     96.77% |       186 |
| api/domain/audio/errors.py                                                            |        3 |        0 |        0 |        0 |    100.00% |           |
| api/domain/auth/\_authssosessionvalidator.py                                          |        6 |        1 |        0 |        0 |     83.33% |        12 |
| api/domain/auth/errors.py                                                             |       10 |        0 |        0 |        0 |    100.00% |           |
| api/domain/chat/entities.py                                                           |       62 |        3 |       16 |        3 |     92.31% |22, 26, 76 |
| api/domain/embeddings/entities.py                                                     |       38 |        0 |       12 |        0 |    100.00% |           |
| api/domain/key/\_keyencoder.py                                                        |       11 |        2 |        0 |        0 |     81.82% |    12, 16 |
| api/domain/key/\_keyrepository.py                                                     |       25 |        6 |        0 |        0 |     76.00% |14, 26, 30, 34, 38, 42 |
| api/domain/key/entities.py                                                            |       31 |        0 |        6 |        0 |    100.00% |           |
| api/domain/key/errors.py                                                              |        7 |        0 |        0 |        0 |    100.00% |           |
| api/domain/model/\_modelenvironmentalimpactscomputer.py                               |        7 |        1 |        0 |        0 |     85.71% |        29 |
| api/domain/model/\_modelquery.py                                                      |       10 |        2 |        0 |        0 |     80.00% |    10, 14 |
| api/domain/model/\_modeltokenizer.py                                                  |        5 |        1 |        0 |        0 |     80.00% |         7 |
| api/domain/model/entities.py                                                          |       16 |        0 |        0 |        0 |    100.00% |           |
| api/domain/model/errors.py                                                            |       13 |        0 |        0 |        0 |    100.00% |           |
| api/domain/model/views.py                                                             |        9 |        0 |        0 |        0 |    100.00% |           |
| api/domain/ocr/entities.py                                                            |       37 |        0 |        2 |        0 |    100.00% |           |
| api/domain/organization/\_organizationrepository.py                                   |       23 |        6 |        0 |        0 |     73.91% |11, 15, 19, 30, 34, 38 |
| api/domain/organization/entities.py                                                   |       12 |        0 |        0 |        0 |    100.00% |           |
| api/domain/organization/errors.py                                                     |        9 |        0 |        0 |        0 |    100.00% |           |
| api/domain/provider/\_providerclient.py                                               |       16 |        2 |        0 |        0 |     87.50% |    29, 33 |
| api/domain/provider/\_providerloadbalancer.py                                         |        7 |        1 |        0 |        0 |     85.71% |        10 |
| api/domain/provider/\_providermetricslogger.py                                        |        8 |        2 |        0 |        0 |     75.00% |     7, 11 |
| api/domain/provider/\_providerrepository.py                                           |       29 |        8 |        0 |        0 |     72.41% |26, 30, 34, 45, 49, 53, 57, 61 |
| api/domain/provider/entities.py                                                       |       78 |        5 |        6 |        2 |     91.67% |34, 122, 125, 160, 163 |
| api/domain/provider/errors.py                                                         |       21 |        0 |        0 |        0 |    100.00% |           |
| api/domain/rerank/entities.py                                                         |       12 |        0 |        0 |        0 |    100.00% |           |
| api/domain/role/\_limitrepository.py                                                  |       12 |        3 |        0 |        0 |     75.00% | 9, 16, 23 |
| api/domain/role/\_permissionrepository.py                                             |       12 |        3 |        0 |        0 |     75.00% | 9, 13, 17 |
| api/domain/role/\_rolerepository.py                                                   |       23 |        6 |        0 |        0 |     73.91% |11, 15, 19, 23, 27, 37 |
| api/domain/role/entities.py                                                           |       34 |        0 |        0 |        0 |    100.00% |           |
| api/domain/role/errors.py                                                             |        9 |        0 |        0 |        0 |    100.00% |           |
| api/domain/router/\_routerratelimiter.py                                              |       13 |        3 |        0 |        0 |     76.92% |10, 16, 21 |
| api/domain/router/\_routerrepository.py                                               |       35 |       10 |        0 |        0 |     71.43% |11, 21, 25, 29, 42, 46, 50, 54, 58, 62 |
| api/domain/router/entities.py                                                         |       84 |        7 |        8 |        3 |     89.13% |122, 128-130, 137-139 |
| api/domain/router/errors.py                                                           |       17 |        0 |        0 |        0 |    100.00% |           |
| api/domain/usage/\_usagecontext.py                                                    |       12 |        3 |        0 |        0 |     75.00% | 9, 13, 17 |
| api/domain/usage/\_usagerepository.py                                                 |       23 |        6 |        0 |        0 |     73.91% |22, 26, 30, 34, 38, 52 |
| api/domain/usage/entities.py                                                          |       36 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/\_authenticateduserquery.py                                           |       10 |        2 |        0 |        0 |     80.00% |    10, 14 |
| api/domain/user/\_userpasswordencoder.py                                              |        8 |        2 |        0 |        0 |     75.00% |     7, 11 |
| api/domain/user/\_userrepository.py                                                   |       36 |        9 |        0 |        0 |     75.00% |27, 31, 35, 39, 52, 56, 60, 64, 68 |
| api/domain/user/entities.py                                                           |       13 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/errors.py                                                             |       24 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/views.py                                                              |       21 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/bcrypt/\_bcryptuserpasswordencoder.py                              |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/configuration.py                                                   |      250 |       99 |       50 |        4 |     52.33% |37-79, 82, 91-92, 122-129, 132, 156, 175-179, 295-298, 334-339, 344-347, 352-364, 376-377, 381-396, 400-419, 424 |
| api/infrastructure/context.py                                                         |       13 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/contextvars/\_contextvarsusagecontext.py                           |       19 |        1 |        0 |        0 |     94.74% |        10 |
| api/infrastructure/ecologit/\_ecologitmodelenvironmentalimpactscomputer.py            |       12 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/\_requestcontext.py                                        |       16 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/\_requestlogmiddleware.py                                  |       59 |        2 |        6 |        1 |     95.38% |     26-27 |
| api/infrastructure/fastapi/\_streamingresponsewithstatuscode.py                       |       50 |       14 |       20 |        7 |     64.29% |13-\>exit, 31, 33-\>36, 46-52, 54-\>56, 60-66, 69-\>exit |
| api/infrastructure/fastapi/accesscontroller.py                                        |       48 |        0 |       16 |        1 |     98.44% |   62-\>66 |
| api/infrastructure/fastapi/dependencies.py                                            |       11 |        3 |        0 |        0 |     72.73% |11, 15, 19 |
| api/infrastructure/fastapi/documentation.py                                           |       15 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/fastapi/endpoints/admin/keys.py                                    |       51 |        0 |       18 |        4 |     94.20% |60-\>exit, 80-\>exit, 103-\>exit, 132-\>exit |
| api/infrastructure/fastapi/endpoints/admin/organizations.py                           |       59 |        0 |       22 |        5 |     93.83% |64-\>exit, 86-\>exit, 111-\>exit, 133-\>exit, 156-\>exit |
| api/infrastructure/fastapi/endpoints/admin/providers.py                               |       83 |        0 |       42 |        5 |     96.00% |128-\>exit, 149-\>exit, 203-\>exit, 223-\>exit, 245-\>exit |
| api/infrastructure/fastapi/endpoints/admin/roles.py                                   |       59 |        0 |       22 |        5 |     93.83% |59-\>exit, 87-\>exit, 107-\>exit, 132-\>exit, 154-\>exit |
| api/infrastructure/fastapi/endpoints/admin/routers.py                                 |       62 |        0 |       24 |        5 |     94.19% |71-\>exit, 90-\>exit, 115-\>exit, 140-\>exit, 179-\>exit |
| api/infrastructure/fastapi/endpoints/admin/users.py                                   |       82 |        8 |       34 |        5 |     88.79% |92-\>exit, 113-114, 151-152, 183-184, 232-233 |
| api/infrastructure/fastapi/endpoints/audio.py                                         |       60 |        2 |       30 |        1 |     96.67% |   112-113 |
| api/infrastructure/fastapi/endpoints/auth.py                                          |       45 |        0 |       22 |        2 |     97.01% |46-\>exit, 100-\>exit |
| api/infrastructure/fastapi/endpoints/chat.py                                          |       66 |        1 |       32 |        2 |     96.94% |100, 115-\>exit |
| api/infrastructure/fastapi/endpoints/embeddings.py                                    |       52 |        2 |       26 |        1 |     96.15% |     86-87 |
| api/infrastructure/fastapi/endpoints/exceptions.py                                    |      223 |       12 |       20 |        6 |     90.12% |139-142, 154-157, 189, 327, 329, 332-333, 343 |
| api/infrastructure/fastapi/endpoints/health.py                                        |       21 |        1 |        2 |        1 |     91.30% |21, 41-\>exit |
| api/infrastructure/fastapi/endpoints/keys.py                                          |       68 |        0 |       22 |        5 |     94.44% |80-\>exit, 123-\>exit, 160-\>exit, 193-\>exit, 225-\>exit |
| api/infrastructure/fastapi/endpoints/me.py                                            |       37 |        2 |       10 |        2 |     91.49% |54-\>exit, 100-101 |
| api/infrastructure/fastapi/endpoints/models.py                                        |       29 |        0 |        6 |        2 |     94.29% |43-\>exit, 68-\>exit |
| api/infrastructure/fastapi/endpoints/ocr.py                                           |       52 |        2 |       26 |        1 |     96.15% |     89-90 |
| api/infrastructure/fastapi/endpoints/organizations.py                                 |       21 |        0 |        4 |        1 |     96.00% | 37-\>exit |
| api/infrastructure/fastapi/endpoints/rerank.py                                        |       52 |        2 |       26 |        1 |     96.15% |     86-87 |
| api/infrastructure/fastapi/endpoints/usage.py                                         |       18 |        0 |        2 |        1 |     95.00% | 56-\>exit |
| api/infrastructure/fastapi/monitoring.py                                              |       95 |       78 |       16 |        0 |     15.32% |16, 20-37, 41-102, 106-163, 167-187, 191-212, 216-244 |
| api/infrastructure/fastapi/routes.py                                                  |       44 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/keys.py                                      |       16 |        6 |        4 |        0 |     50.00% |     17-25 |
| api/infrastructure/fastapi/schemas/admin/organizations.py                             |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/providers.py                                 |       11 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/roles.py                                     |       19 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/routers.py                                   |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/users.py                                     |       20 |        1 |        4 |        1 |     91.67% |        22 |
| api/infrastructure/fastapi/schemas/audio.py                                           |       17 |        4 |        0 |        0 |     76.47% |     54-64 |
| api/infrastructure/fastapi/schemas/auth.py                                            |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/chat.py                                            |       13 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/embeddings.py                                      |       12 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/health.py                                          |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/keys.py                                            |       14 |        6 |        4 |        0 |     44.44% |     21-29 |
| api/infrastructure/fastapi/schemas/me.py                                              |       12 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/models.py                                          |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/ocr.py                                             |       14 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/rerank.py                                          |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/usage.py                                           |       16 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpauthssosessionvalidator.py                              |       21 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpprovideradapterbuilder.py                               |       35 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpproviderclient.py                                       |       93 |        5 |       28 |        6 |     90.91% |30-\>33, 36-\>39, 84-\>91, 104-\>107, 110-\>113, 130, 132-\>exit, 143, 147, 149-150 |
| api/infrastructure/http/\_httpproviderrequest.py                                      |        6 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpproviderresponse.py                                     |        4 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/\_httpprovideradapter.py                             |       28 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/audio/\_audiotranscriptionsadapter.py                |       27 |        3 |        2 |        1 |     86.21% | 37, 43-44 |
| api/infrastructure/http/adapters/audio/albert/\_albertaudiotranscriptionsadapter.py   |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/audio/mistral/\_mistralaudiotranscriptionsadapter.py |       30 |        7 |        2 |        0 |     71.88% |30-31, 57-62 |
| api/infrastructure/http/adapters/audio/openai/\_openaiaudiotranscriptionsadapter.py   |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/audio/vllm/\_vllmaudiotranscriptionsadapter.py       |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/\_chatcompletionsadapter.py                     |       20 |        2 |        4 |        1 |     87.50% |     20-21 |
| api/infrastructure/http/adapters/chat/albert/\_albertchatcompletionsadapter.py        |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/mistral/\_mistralchatcompletionsadapter.py      |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/openai/\_openaichatcompletionsadapter.py        |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/vllm/\_vllmchatcompletionsadapter.py            |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/\_embeddingsadapter.py                    |       19 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/albert/\_albertembeddingsadapter.py       |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/mistral/\_mistralembeddingsadapter.py     |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/openai/\_openaiembeddingsadapter.py       |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/tei/\_teiembeddingsadapter.py             |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/vllm/\_vllmembeddingsadapter.py           |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/metrics/\_metricsadapter.py                          |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/metrics/mistral/\_mistralmetricsadapter.py           |       23 |        0 |        8 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/metrics/vllm/\_vllmmetricsadapter.py                 |       19 |        0 |        8 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/\_modelsadapter.py                            |       16 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/albert/\_albertmodelsadapter.py               |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/mistral/\_mistralmodelsadapter.py             |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/openai/\_openaimodelsadapter.py               |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/tei/\_teimodelsadapter.py                     |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/vllm/\_vllmmodelsadapter.py                   |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/\_ocradapter.py                                  |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/albert/\_albertocradapter.py                     |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/mistral/\_mistralocradapter.py                   |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/\_rerankadapter.py                            |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/albert/\_albertreranksadapter.py              |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/tei/\_teireranksadapter.py                    |       31 |        2 |        2 |        0 |     93.94% |     35-36 |
| api/infrastructure/http/adapters/rerank/vllm/\_vllmreranksadapter.py                  |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/jwt/\_jwtkeyencoder.py                                             |       12 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/langfuse/\_langfuseusagerepository.py                              |      120 |        8 |       20 |        1 |     92.14% |27-30, 92-93, 101-102, 222 |
| api/infrastructure/logging.py                                                         |       49 |        1 |       12 |        1 |     96.72% |        29 |
| api/infrastructure/postgres/\_autocommitsession.py                                    |       30 |        6 |        0 |        0 |     80.00% |19-22, 25-28 |
| api/infrastructure/postgres/\_pagination.py                                           |        6 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresauthenticateduserquery.py                       |       43 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgreskeyrepository.py                                |       82 |        1 |       22 |        2 |     97.12% |66-\>69, 82 |
| api/infrastructure/postgres/\_postgreslimitrepository.py                              |       27 |        0 |        4 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresmodelquery.py                                   |       35 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresorganizationrepository.py                       |       82 |        3 |       16 |        3 |     93.88% |30, 120, 135 |
| api/infrastructure/postgres/\_postgrespermissionrepository.py                         |       24 |        0 |        4 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresproviderrepository.py                           |       74 |        2 |       10 |        2 |     95.24% |   60, 137 |
| api/infrastructure/postgres/\_postgresrolesrepository.py                              |       83 |        2 |       14 |        3 |     94.85% |80, 151-\>154, 159 |
| api/infrastructure/postgres/\_postgresrouterrepository.py                             |      110 |        2 |       22 |        3 |     96.21% |173, 191-\>194, 240 |
| api/infrastructure/postgres/\_postgresusagerepository.py                              |       81 |        1 |       18 |        1 |     97.98% |        27 |
| api/infrastructure/postgres/\_postgresusersrepository.py                              |      112 |        8 |       36 |        3 |     91.22% |105, 123-127, 200, 214 |
| api/infrastructure/postgres/decorators.py                                             |       25 |        1 |        6 |        1 |     93.55% |        36 |
| api/infrastructure/postgres/models.py                                                 |      118 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/redis/\_keys.py                                                    |        2 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/redis/\_redisproviderloadbalancer.py                               |       32 |        0 |       12 |        1 |     97.73% | 20-\>exit |
| api/infrastructure/redis/\_redisprovidermetricslogger.py                              |       38 |       12 |        4 |        1 |     64.29% |24-25, 31-32, 48-58 |
| api/infrastructure/redis/\_redisrouterratelimiter.py                                  |      114 |       18 |       40 |       10 |     80.52% |32-33, 51, 59, 64-\>38, 67, 109-110, 114, 119-\>exit, 126, 132-135, 154, 163-164, 168-171 |
| api/infrastructure/tiktoken/\_tiktokenmodeltokenizer.py                               |        9 |        0 |        2 |        0 |    100.00% |           |
| api/lifespan.py                                                                       |      124 |       50 |       52 |        4 |     53.41% |43-64, 68-74, 78, 82, 114-117, 118-\>exit, 152, 155-\>exit, 160-172, 176-184 |
| api/main.py                                                                           |        2 |        2 |        0 |        0 |      0.00% |       1-3 |
| api/use\_cases/\_providerrequestforwardingusecase.py                                  |      143 |        0 |       30 |        0 |    100.00% |           |
| api/use\_cases/admin/\_bootstrapadminusecase.py                                       |       73 |        0 |       30 |        7 |     93.20% |71-\>79, 76-\>79, 82-\>110, 84-\>110, 89-\>97, 94-\>97, 107-\>110 |
| api/use\_cases/admin/keys/\_createkeyusecase.py                                       |       32 |        0 |       10 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_deletekeyusecase.py                                       |       20 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_getkeysusecase.py                                         |       16 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_getonekeyusecase.py                                       |       20 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_updatekeyusecase.py                                       |       31 |        0 |       10 |        1 |     97.56% |   32-\>35 |
| api/use\_cases/admin/organizations/\_createorganizationusecase.py                     |       19 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/organizations/\_deleteorganizationusecase.py                     |       28 |        0 |       12 |        2 |     95.00% |31-\>34, 40-\>exit |
| api/use\_cases/admin/organizations/\_getoneorganizationusecase.py                     |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/organizations/\_getorganizationsusecase.py                       |       20 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/organizations/\_updateorganizationusecase.py                     |       25 |        0 |        6 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_createproviderusecase.py                             |       49 |        0 |       18 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_deleteproviderusecase.py                             |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/providers/\_getoneproviderusecase.py                             |       17 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_getprovidersusecase.py                               |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_updateproviderusecase.py                             |       45 |        0 |       20 |        1 |     98.46% |   59-\>63 |
| api/use\_cases/admin/roles/\_createroleusecase.py                                     |       24 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/roles/\_deleteroleusecase.py                                     |       21 |        0 |        6 |        1 |     96.30% | 33-\>exit |
| api/use\_cases/admin/roles/\_getoneroleusecase.py                                     |       19 |        0 |        4 |        1 |     95.65% | 30-\>exit |
| api/use\_cases/admin/roles/\_getrolesusecase.py                                       |       27 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/roles/\_updateroleusecase.py                                     |       31 |        0 |        6 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_createrouterusecase.py                                 |       19 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_deleterouterusecase.py                                 |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/routers/\_getonerouterusecase.py                                 |       17 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_getroutersusecase.py                                   |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_updaterouterusecase.py                                 |       30 |        0 |       10 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_createuserusecase.py                                     |       27 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_deleteuserusecase.py                                     |       23 |        0 |        8 |        1 |     96.77% | 35-\>exit |
| api/use\_cases/admin/users/\_getoneuserusecase.py                                     |       19 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_getusersusecase.py                                       |       20 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_updateuserusecase.py                                     |       37 |        0 |       10 |        0 |    100.00% |           |
| api/use\_cases/audio/\_createaudiotranscriptionsusecase.py                            |       37 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/auth/\_authloginusecase.py                                             |       33 |        0 |        6 |        0 |    100.00% |           |
| api/use\_cases/auth/\_authssologinusecase.py                                          |       81 |        0 |       20 |        2 |     98.02% |119-\>140, 124-\>140 |
| api/use\_cases/chat/\_createchatcompletionsusecase.py                                 |      115 |        0 |       28 |        0 |    100.00% |           |
| api/use\_cases/embeddings/\_createembeddingsusecase.py                                |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/health/\_gethealthmodelsusecase.py                                     |       64 |        0 |       32 |        4 |     95.83% |78-\>50, 84-\>50, 85-\>50, 86-\>88 |
| api/use\_cases/me/\_getmeusecase.py                                                   |       10 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/me/\_updatemeusecase.py                                                |       32 |        0 |        8 |        0 |    100.00% |           |
| api/use\_cases/models/\_bootstrapmodelsusecase.py                                     |       70 |        0 |       26 |        0 |    100.00% |           |
| api/use\_cases/models/\_getmodelsusecase.py                                           |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/models/\_getonemodelusecase.py                                         |       23 |        0 |        6 |        1 |     96.55% |   32-\>35 |
| api/use\_cases/ocr/\_createocrusecase.py                                              |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/reranks/\_creatererankusecase.py                                       |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/services/\_providercapabilitiesprobe.py                                |       73 |        6 |       30 |        3 |     91.26% |52-53, 65-66, 114-115 |
| api/use\_cases/usage/\_getusagesusecase.py                                            |       17 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                                                             | **6660** |  **575** | **1342** |  **153** | **89.43%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/etalab-ia/OpenGateLLM/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/etalab-ia/OpenGateLLM/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/etalab-ia/OpenGateLLM/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/etalab-ia/OpenGateLLM/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fetalab-ia%2FOpenGateLLM%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/etalab-ia/OpenGateLLM/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.