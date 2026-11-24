# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/etalab-ia/OpenGateLLM/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                                                            |    Stmts |     Miss |   Branch |   BrPart |      Cover |   Missing |
|---------------------------------------------------------------------------------------------------------------- | -------: | -------: | -------: | -------: | ---------: | --------: |
| api/alembic/env.py                                                                                              |       24 |        5 |        4 |        2 |     75.00% |16, 33-41, 61 |
| api/alembic/versions/2025\_03\_11\_1552-9a9c82ec2470\_create\_usages\_table.py                                  |       12 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_04\_02\_1603-e78eaed1bcb2\_add\_auth.py                                              |       56 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_04\_04\_1641-8c5ae2a3d4d0\_remove\_delete\_cascade\_usage\_token\_id.py              |       12 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_04\_15\_1513-a4ac45e7c990\_remove\_unique\_name\_on\_token\_and\_.py                 |       12 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_04\_17\_1201-896cbf4c2cbb\_add\_new\_columns\_to\_usages\_table.py                   |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_05\_12\_1613-5553fa60acfa\_remove\_default\_role\_attribut.py                        |       14 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_05\_28\_1541-752279f74929\_add\_cost\_and\_budget\_colonne.py                        |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_06\_16\_1029-37d92be0a44c\_add\_environnement\_impact\_in\_db.py                     |       17 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_07\_11\_1151-564856827493\_add\_email\_and\_sub\_fields\_in\_user\_table.py          |       18 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_08\_14\_0837-28019ec49533\_change\_permission\_types.py                              |       21 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_08\_14\_1732-c1e54102255e\_add\_organisation\_table.py                               |       17 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_08\_22\_1157-788a3b052a11\_move\_user\_auth\_from\_ui\_to\_app.py                    |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_08\_23\_1934-479aeeae940b\_db\_schema\_for\_model\_router\_client.py                 |       21 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_09\_07\_1246-17be379f45ac\_force\_non\_null\_email.py                                |       27 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_09\_25\_0000-a1b2c3d4e5f6\_add\_celery\_related\_fields.py                           |       19 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_11\_13\_2012-9ba1f6a21f20\_refacto\_model\_provision.py                              |      146 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_11\_13\_2152-05211e3047e8\_add\_index\_to\_usage.py                                  |       17 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_11\_14\_1642-85459163c680\_rename\_qos\_value\_to\_qos\_limit.py                     |       15 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_11\_19\_1120-0ae7dc72ec5c\_add\_mistral\_type.py                                     |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_11\_19\_1711-843230e94aec\_rename\_usage\_columns.py                                 |       25 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_09\_1858-9b3cdc1e64dd\_add\_image\_to\_text\_model\_type.py                      |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_11\_1010-2d2550e0771d\_add\_unique\_constraint\_on\_organization\_.py            |       15 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_16\_1535-1db1572f2605\_add\_unique\_constraint\_on\_provider\_by\_.py            |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_16\_1737-d2e9e967501b\_add\_default\_value\_carbon\_params.py                    |       15 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_17\_0947-551b2920b23c\_add\_provider\_router\_list\_relationship.py              |       12 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2025\_12\_22\_1507-f02a2525b97c\_remove\_carbon\_footprint\_prefix.py                      |       63 |        2 |        4 |        2 |     94.03% |   66, 128 |
| api/alembic/versions/2026\_02\_26\_1730-c206a2bfefe9\_remove\_min\_max\_carbon\_impact.py                       |       21 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_04\_23\_1814-4a8f3b3aed3a\_remove\_master\_user.py                                   |       51 |       20 |        4 |        1 |     58.18% |40-86, 90-94, 107-121, 125-127 |
| api/alembic/versions/2026\_05\_06\_1224-9fd5b6491d48\_add\_constraint\_on\_router\_delete.py                    |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_05\_06\_1658-4cbcc969c660\_add\_constraint\_on\_provinder\_delete.py                 |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_06\_01\_1421-7498a3a48271\_add\_storage\_limits.py                                   |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_06\_10\_1828-0daf52aadaf0\_add\_basic\_auth\_to\_provider\_definition.py             |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_06\_16\_1400-c3d4e5f6a7b9\_all\_datetime\_timestamptz.py                             |       10 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_06\_17\_1518-5138304df5f5\_add\_unique\_constraint\_on\_key\_name.py                 |       27 |        7 |        6 |        1 |     63.64% |     41-54 |
| api/alembic/versions/2026\_07\_15\_1826-50ddc08e9202\_add\_claims\_column.py                                    |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_07\_30\_1805-c83449930fe2\_update\_constraint\_name.py                               |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_08\_19\_1239-b2d58fce4b3c\_remove\_create\_public\_collection\_.py                   |       31 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_04\_1000-a7f3c91b2e04\_rename\_providercarbonfootprintzone\_to\_hostingzone.py   |       10 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_11\_1340-c8e1a04b7f12\_drop\_provider\_qos\_columns.py                           |       16 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_14\_1100-f4b7c2a91e30\_require\_user\_organization.py                            |       15 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_18\_1000-e7a1c4d8b902\_replace\_image\_text\_to\_text\_with\_text\_generation.py |       19 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_21\_1826-b7e4c1a90f23\_add\_token\_revoked\_drop\_unique\_name.py                |       14 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_22\_1539-a9c2e7b41d35\_rename\_modeltype\_enum\_to\_routertype.py                |        9 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_23\_1612-c4f8e2d91a70\_drop\_usage\_method.py                                    |       13 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_24\_1200-d1e2f3a4b5c6\_add\_usage\_request\_id.py                                |       12 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_25\_1851-c8fef686d652\_add\_router\_qos\_fields.py                               |       14 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_09\_28\_2030-bf92da1a3246\_remove\_user\_budget.py                                   |       11 |        0 |        0 |        0 |    100.00% |           |
| api/alembic/versions/2026\_11\_19\_0952-2b8e23234402\_default\_router\_load\_balancing\_strategy.py             |       11 |        0 |        0 |        0 |    100.00% |           |
| api/app.py                                                                                                      |       63 |        5 |       12 |        4 |     88.00% |28, 58-59, 88, 95 |
| api/dependencies.py                                                                                             |      217 |       91 |        4 |        0 |     57.01% |89-98, 102-104, 108-110, 115, 119, 124, 128, 132, 136, 140, 144, 148, 152, 156, 160, 164, 174, 178, 182, 190, 194, 198, 202, 206, 210, 214, 218, 222, 226, 230-241, 256, 282, 303, 318, 336, 355, 374, 384, 391, 395, 399, 403, 408, 412, 417, 422, 426, 434, 448, 467, 476, 482, 486, 493, 503, 515, 522, 529, 536, 555, 571, 579, 587, 595, 601, 608, 614, 620, 626, 632, 642, 650, 657, 663, 669 |
| api/domain/audio/entities.py                                                                                    |       31 |        1 |        0 |        0 |     96.77% |       186 |
| api/domain/audio/errors.py                                                                                      |        3 |        0 |        0 |        0 |    100.00% |           |
| api/domain/auth/\_authssosessionvalidator.py                                                                    |        6 |        1 |        0 |        0 |     83.33% |        12 |
| api/domain/auth/errors.py                                                                                       |       10 |        0 |        0 |        0 |    100.00% |           |
| api/domain/authorization/\_authorizationclient.py                                                               |       15 |        4 |        0 |        0 |     73.33% |9, 13, 17, 21 |
| api/domain/authorization/entities.py                                                                            |       39 |        4 |        0 |        0 |     89.74% |46, 50, 54, 57 |
| api/domain/chat/entities.py                                                                                     |       91 |        3 |       28 |        3 |     94.96% |22, 26, 76 |
| api/domain/embeddings/entities.py                                                                               |       38 |        0 |       12 |        0 |    100.00% |           |
| api/domain/key/\_keyencoder.py                                                                                  |       11 |        2 |        0 |        0 |     81.82% |    12, 16 |
| api/domain/key/\_keyrepository.py                                                                               |       25 |        6 |        0 |        0 |     76.00% |14, 26, 30, 34, 38, 42 |
| api/domain/key/entities.py                                                                                      |       31 |        0 |        6 |        0 |    100.00% |           |
| api/domain/key/errors.py                                                                                        |        7 |        0 |        0 |        0 |    100.00% |           |
| api/domain/model/\_modelenvironmentalimpactscomputer.py                                                         |        7 |        1 |        0 |        0 |     85.71% |        29 |
| api/domain/model/\_modelquery.py                                                                                |       10 |        2 |        0 |        0 |     80.00% |    10, 14 |
| api/domain/model/\_modeltokenizer.py                                                                            |        6 |        1 |        0 |        0 |     83.33% |         9 |
| api/domain/model/entities.py                                                                                    |       26 |        0 |        8 |        0 |    100.00% |           |
| api/domain/model/errors.py                                                                                      |       20 |        0 |        0 |        0 |    100.00% |           |
| api/domain/model/views.py                                                                                       |        9 |        0 |        0 |        0 |    100.00% |           |
| api/domain/ocr/entities.py                                                                                      |       37 |        0 |        2 |        0 |    100.00% |           |
| api/domain/organization/\_organizationauthorization.py                                                          |       17 |        5 |        0 |        0 |     70.59% |7, 11, 15, 19, 23 |
| api/domain/organization/\_organizationrepository.py                                                             |       23 |        6 |        0 |        0 |     73.91% |11, 15, 19, 30, 34, 38 |
| api/domain/organization/entities.py                                                                             |       12 |        0 |        0 |        0 |    100.00% |           |
| api/domain/organization/errors.py                                                                               |       15 |        0 |        0 |        0 |    100.00% |           |
| api/domain/provider/\_providerclient.py                                                                         |       16 |        2 |        0 |        0 |     87.50% |    29, 33 |
| api/domain/provider/\_providerconcurrencylimiter.py                                                             |       23 |        2 |        0 |        0 |     91.30% |    29, 42 |
| api/domain/provider/\_providerrepository.py                                                                     |       29 |        8 |        0 |        0 |     72.41% |26, 30, 34, 45, 49, 53, 57, 61 |
| api/domain/provider/entities.py                                                                                 |      114 |        4 |       18 |        2 |     95.45% |131, 134, 198, 201 |
| api/domain/provider/errors.py                                                                                   |       22 |        0 |        0 |        0 |    100.00% |           |
| api/domain/rerank/entities.py                                                                                   |       12 |        0 |        0 |        0 |    100.00% |           |
| api/domain/role/\_limitrepository.py                                                                            |       12 |        3 |        0 |        0 |     75.00% | 9, 16, 23 |
| api/domain/role/\_permissionrepository.py                                                                       |       12 |        3 |        0 |        0 |     75.00% | 9, 13, 17 |
| api/domain/role/\_rolerepository.py                                                                             |       23 |        6 |        0 |        0 |     73.91% |11, 15, 19, 23, 27, 37 |
| api/domain/role/entities.py                                                                                     |       34 |        0 |        0 |        0 |    100.00% |           |
| api/domain/role/errors.py                                                                                       |       11 |        0 |        0 |        0 |    100.00% |           |
| api/domain/router/\_routerratelimiter.py                                                                        |       13 |        3 |        0 |        0 |     76.92% |10, 16, 21 |
| api/domain/router/\_routerrepository.py                                                                         |       35 |       10 |        0 |        0 |     71.43% |11, 21, 25, 29, 42, 46, 50, 54, 58, 62 |
| api/domain/router/entities.py                                                                                   |       93 |        0 |       12 |        0 |    100.00% |           |
| api/domain/router/errors.py                                                                                     |       17 |        0 |        0 |        0 |    100.00% |           |
| api/domain/router/views.py                                                                                      |        7 |        0 |        0 |        0 |    100.00% |           |
| api/domain/usage/\_usagecontext.py                                                                              |       25 |        7 |        0 |        0 |     72.00% |10, 14, 18, 22, 26, 30, 34 |
| api/domain/usage/\_usagerepository.py                                                                           |       10 |        2 |        0 |        0 |     80.00% |    12, 26 |
| api/domain/usage/entities.py                                                                                    |       52 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/\_authenticateduserquery.py                                                                     |       10 |        2 |        0 |        0 |     80.00% |    10, 14 |
| api/domain/user/\_bootstrapauthorization.py                                                                     |        5 |        1 |        0 |        0 |     80.00% |         7 |
| api/domain/user/\_userauthorization.py                                                                          |       23 |        7 |        0 |        0 |     69.57% |7, 11, 15, 19, 23, 27, 31 |
| api/domain/user/\_userpasswordencoder.py                                                                        |        8 |        2 |        0 |        0 |     75.00% |     7, 11 |
| api/domain/user/\_userrepository.py                                                                             |       36 |        9 |        0 |        0 |     75.00% |27, 31, 35, 39, 54, 58, 62, 66, 70 |
| api/domain/user/entities.py                                                                                     |       13 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/errors.py                                                                                       |       34 |        0 |        0 |        0 |    100.00% |           |
| api/domain/user/views.py                                                                                        |       21 |        0 |        4 |        0 |    100.00% |           |
| api/infrastructure/bcrypt/\_bcryptuserpasswordencoder.py                                                        |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/configuration/\_configuration.py                                                             |       37 |        4 |        6 |        2 |     86.05% |29-30, 57, 61 |
| api/infrastructure/configuration/\_interpolation.py                                                             |       26 |        0 |       12 |        0 |    100.00% |           |
| api/infrastructure/configuration/\_validationerrors.py                                                          |       43 |        1 |        8 |        2 |     94.12% |25-\>34, 27 |
| api/infrastructure/configuration/sections/dependencies.py                                                       |       22 |        2 |        2 |        1 |     87.50% |     21-22 |
| api/infrastructure/configuration/sections/models.py                                                             |       29 |        8 |       10 |        2 |     58.97% |32, 38-40, 61-65 |
| api/infrastructure/configuration/sections/settings.py                                                           |       28 |        1 |        2 |        1 |     93.33% |        79 |
| api/infrastructure/context.py                                                                                   |       14 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/ecologit/\_ecologitmodelenvironmentalimpactscomputer.py                                      |       12 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/\_requestcontext.py                                                                  |       12 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/\_requestlogmiddleware.py                                                            |       62 |        2 |        8 |        1 |     95.71% |     26-27 |
| api/infrastructure/fastapi/\_requesttracer.py                                                                   |       14 |        3 |        0 |        0 |     78.57% |11, 15, 20 |
| api/infrastructure/fastapi/\_streamingresponsewithstatuscode.py                                                 |       50 |       14 |       20 |        7 |     64.29% |13-\>exit, 31, 33-\>36, 46-52, 54-\>56, 60-66, 69-\>exit |
| api/infrastructure/fastapi/\_usagerecorder.py                                                                   |       45 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/fastapi/accesscontroller.py                                                                  |       47 |        0 |       16 |        1 |     98.41% |   61-\>65 |
| api/infrastructure/fastapi/decorators.py                                                                        |       24 |        1 |        4 |        1 |     92.86% |        40 |
| api/infrastructure/fastapi/dependencies.py                                                                      |       11 |        3 |        0 |        0 |     72.73% |11, 15, 19 |
| api/infrastructure/fastapi/documentation.py                                                                     |       15 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/fastapi/endpoints/admin/keys.py                                                              |       51 |        0 |       18 |        4 |     94.20% |60-\>exit, 80-\>exit, 103-\>exit, 132-\>exit |
| api/infrastructure/fastapi/endpoints/admin/organizations.py                                                     |       67 |        0 |       28 |        5 |     94.74% |77-\>exit, 99-\>exit, 124-\>exit, 149-\>exit, 177-\>exit |
| api/infrastructure/fastapi/endpoints/admin/providers.py                                                         |       87 |        2 |       46 |        7 |     93.23% |121, 138-\>exit, 159-\>exit, 207, 218-\>exit, 238-\>exit, 260-\>exit |
| api/infrastructure/fastapi/endpoints/admin/roles.py                                                             |       61 |        2 |       24 |        5 |     89.41% |60-\>exit, 92-93, 112-\>exit, 137-\>exit, 159-\>exit |
| api/infrastructure/fastapi/endpoints/admin/routers.py                                                           |       62 |        0 |       24 |        5 |     94.19% |71-\>exit, 90-\>exit, 115-\>exit, 140-\>exit, 179-\>exit |
| api/infrastructure/fastapi/endpoints/admin/users.py                                                             |       94 |        8 |       44 |        5 |     90.58% |103-\>exit, 127-128, 173-174, 208-209, 261-262 |
| api/infrastructure/fastapi/endpoints/audio.py                                                                   |       64 |        2 |       32 |        1 |     96.88% |   119-120 |
| api/infrastructure/fastapi/endpoints/auth.py                                                                    |       45 |        0 |       22 |        2 |     97.01% |46-\>exit, 100-\>exit |
| api/infrastructure/fastapi/endpoints/chat.py                                                                    |       70 |        1 |       34 |        2 |     97.12% |105, 122-\>exit |
| api/infrastructure/fastapi/endpoints/embeddings.py                                                              |       56 |        2 |       28 |        1 |     96.43% |     93-94 |
| api/infrastructure/fastapi/endpoints/exceptions.py                                                              |      243 |       14 |       20 |        6 |     90.11% |24, 158-161, 173-176, 208, 283, 362, 364, 367-368, 378 |
| api/infrastructure/fastapi/endpoints/health.py                                                                  |       21 |        1 |        2 |        1 |     91.30% |21, 41-\>exit |
| api/infrastructure/fastapi/endpoints/keys.py                                                                    |       68 |        0 |       22 |        5 |     94.44% |80-\>exit, 123-\>exit, 160-\>exit, 193-\>exit, 225-\>exit |
| api/infrastructure/fastapi/endpoints/limits.py                                                                  |       17 |        0 |        2 |        1 |     94.74% | 32-\>exit |
| api/infrastructure/fastapi/endpoints/me.py                                                                      |       35 |        2 |       10 |        2 |     91.11% |47-\>exit, 85-86 |
| api/infrastructure/fastapi/endpoints/models.py                                                                  |       29 |        0 |        6 |        2 |     94.29% |43-\>exit, 68-\>exit |
| api/infrastructure/fastapi/endpoints/ocr.py                                                                     |       56 |        2 |       28 |        1 |     96.43% |     96-97 |
| api/infrastructure/fastapi/endpoints/organizations.py                                                           |       21 |        0 |        4 |        1 |     96.00% | 37-\>exit |
| api/infrastructure/fastapi/endpoints/rerank.py                                                                  |       56 |        2 |       28 |        1 |     96.43% |     93-94 |
| api/infrastructure/fastapi/endpoints/usage.py                                                                   |       18 |        0 |        2 |        1 |     95.00% | 56-\>exit |
| api/infrastructure/fastapi/monitoring.py                                                                        |       89 |       18 |       14 |        5 |     73.79% |38-40, 99-105, 164-166, 188-190, 210-215 |
| api/infrastructure/fastapi/routes.py                                                                            |       46 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/keys.py                                                                |       16 |        6 |        4 |        0 |     50.00% |     17-25 |
| api/infrastructure/fastapi/schemas/admin/organizations.py                                                       |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/providers.py                                                           |       11 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/roles.py                                                               |       19 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/routers.py                                                             |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/admin/users.py                                                               |       20 |        1 |        4 |        1 |     91.67% |        22 |
| api/infrastructure/fastapi/schemas/audio.py                                                                     |       17 |        4 |        0 |        0 |     76.47% |     54-64 |
| api/infrastructure/fastapi/schemas/auth.py                                                                      |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/chat.py                                                                      |       13 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/embeddings.py                                                                |       12 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/health.py                                                                    |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/keys.py                                                                      |       14 |        6 |        4 |        0 |     44.44% |     21-29 |
| api/infrastructure/fastapi/schemas/limits.py                                                                    |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/me.py                                                                        |       12 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/models.py                                                                    |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/ocr.py                                                                       |       14 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/rerank.py                                                                    |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/fastapi/schemas/usage.py                                                                     |       16 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpauthssosessionvalidator.py                                                        |       21 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpprovideradapterbuilder.py                                                         |       33 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpproviderclient.py                                                                 |       90 |        6 |       28 |        7 |     88.98% |29-\>32, 35-\>38, 79-\>86, 91, 99-\>102, 105-\>108, 122, 124-\>exit, 135, 139, 141-142 |
| api/infrastructure/http/\_httpproviderrequest.py                                                                |        5 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/\_httpproviderresponse.py                                                               |        4 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/\_httpprovideradapter.py                                                       |       28 |        0 |        2 |        1 |     96.67% |   30-\>33 |
| api/infrastructure/http/adapters/audio/\_audiotranscriptionsadapter.py                                          |       27 |        3 |        2 |        1 |     86.21% | 37, 43-44 |
| api/infrastructure/http/adapters/audio/albert/\_albertaudiotranscriptionsadapter.py                             |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/audio/mistral/\_mistralaudiotranscriptionsadapter.py                           |       30 |        7 |        2 |        0 |     71.88% |30-31, 57-62 |
| api/infrastructure/http/adapters/audio/openai/\_openaiaudiotranscriptionsadapter.py                             |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/audio/vllm/\_vllmaudiotranscriptionsadapter.py                                 |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/\_chatcompletionsadapter.py                                               |       20 |        2 |        4 |        1 |     87.50% |     20-21 |
| api/infrastructure/http/adapters/chat/albert/\_albertchatcompletionsadapter.py                                  |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/mistral/\_mistralchatcompletionsadapter.py                                |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/openai/\_openaichatcompletionsadapter.py                                  |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/chat/vllm/\_vllmchatcompletionsadapter.py                                      |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/\_embeddingsadapter.py                                              |       19 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/albert/\_albertembeddingsadapter.py                                 |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/mistral/\_mistralembeddingsadapter.py                               |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/openai/\_openaiembeddingsadapter.py                                 |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/tei/\_teiembeddingsadapter.py                                       |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/embeddings/vllm/\_vllmembeddingsadapter.py                                     |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/\_modelsadapter.py                                                      |       15 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/albert/\_albertmodelsadapter.py                                         |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/mistral/\_mistralmodelsadapter.py                                       |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/openai/\_openaimodelsadapter.py                                         |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/tei/\_teimodelsadapter.py                                               |        8 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/models/vllm/\_vllmmodelsadapter.py                                             |        7 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/\_ocradapter.py                                                            |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/albert/\_albertocradapter.py                                               |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/ocr/mistral/\_mistralocradapter.py                                             |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/\_rerankadapter.py                                                      |        9 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/albert/\_albertreranksadapter.py                                        |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/http/adapters/rerank/tei/\_teireranksadapter.py                                              |       31 |        2 |        2 |        0 |     93.94% |     35-36 |
| api/infrastructure/http/adapters/rerank/vllm/\_vllmreranksadapter.py                                            |        3 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/jwt/\_jwtkeyencoder.py                                                                       |       12 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/langfuse/\_langfuserequesttracer.py                                                          |       38 |        0 |        8 |        0 |    100.00% |           |
| api/infrastructure/logging.py                                                                                   |       49 |        1 |       12 |        1 |     96.72% |        29 |
| api/infrastructure/openfga/\_openfgaauthorizationclient.py                                                      |       22 |        8 |        0 |        0 |     63.64% |15-18, 21, 24, 27-28, 32 |
| api/infrastructure/openfga/\_openfgabootstrapauthorization.py                                                   |       22 |       12 |        4 |        0 |     38.46% |     17-30 |
| api/infrastructure/openfga/\_openfgaorganizationauthorization.py                                                |       31 |       21 |        0 |        0 |     32.26% |8, 11-16, 19-24, 27-32, 35-40, 43-48 |
| api/infrastructure/openfga/\_openfgauserauthorization.py                                                        |       41 |       29 |        0 |        0 |     29.27% |8, 11-16, 19-24, 27-32, 35-40, 43-48, 51-56, 59-64 |
| api/infrastructure/postgres/\_autocommitsession.py                                                              |       30 |        6 |        0 |        0 |     80.00% |19-22, 25-28 |
| api/infrastructure/postgres/\_pagination.py                                                                     |        6 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresauthenticateduserquery.py                                                 |       43 |        0 |        6 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgreskeyrepository.py                                                          |       82 |        1 |       22 |        2 |     97.12% |66-\>69, 82 |
| api/infrastructure/postgres/\_postgreslimitrepository.py                                                        |       27 |        0 |        4 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresmodelquery.py                                                             |       35 |        0 |        2 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresorganizationrepository.py                                                 |       82 |        3 |       16 |        3 |     93.88% |30, 120, 135 |
| api/infrastructure/postgres/\_postgrespermissionrepository.py                                                   |       24 |        0 |        4 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresproviderrepository.py                                                     |       74 |        2 |       10 |        2 |     95.24% |   61, 138 |
| api/infrastructure/postgres/\_postgresrolesrepository.py                                                        |       83 |        2 |       14 |        3 |     94.85% |80, 151-\>154, 159 |
| api/infrastructure/postgres/\_postgresrouterrepository.py                                                       |      110 |        2 |       22 |        3 |     96.21% |173, 191-\>194, 240 |
| api/infrastructure/postgres/\_postgresusagerepository.py                                                        |       54 |        0 |       10 |        0 |    100.00% |           |
| api/infrastructure/postgres/\_postgresusersrepository.py                                                        |      118 |        8 |       40 |        3 |     91.77% |107, 125-129, 212, 226 |
| api/infrastructure/postgres/decorators.py                                                                       |       25 |        1 |        6 |        1 |     93.55% |        36 |
| api/infrastructure/postgres/models.py                                                                           |      119 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/redis/\_keys.py                                                                              |        2 |        0 |        0 |        0 |    100.00% |           |
| api/infrastructure/redis/\_redisproviderconcurrencylimiter.py                                                   |       85 |        1 |       10 |        0 |     98.95% |       132 |
| api/infrastructure/redis/\_redisrouterratelimiter.py                                                            |      117 |       15 |       42 |        9 |     84.91% |33-\>exit, 52, 65-\>39, 68, 110-111, 115, 120-\>exit, 127, 137-140, 159, 168-169, 173-176 |
| api/infrastructure/tiktoken/\_tiktokenmodeltokenizer.py                                                         |       13 |        0 |        2 |        0 |    100.00% |           |
| api/lifespan.py                                                                                                 |      167 |       80 |       64 |        4 |     46.32% |64-91, 95-101, 105, 109, 143-146, 147-\>exit, 185, 190-191, 225-237, 241-249, 253-275, 279-289 |
| api/main.py                                                                                                     |        2 |        2 |        0 |        0 |      0.00% |       1-3 |
| api/use\_cases/\_providerrequestforwardingusecase.py                                                            |      194 |        2 |       58 |        3 |     98.02% |230-\>236, 288-290, 349-\>exit |
| api/use\_cases/admin/\_bootstrapadminusecase.py                                                                 |       76 |        0 |       30 |        7 |     93.40% |74-\>82, 79-\>82, 85-\>113, 87-\>113, 92-\>100, 97-\>100, 110-\>113 |
| api/use\_cases/admin/keys/\_createkeyusecase.py                                                                 |       32 |        0 |       10 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_deletekeyusecase.py                                                                 |       20 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_getkeysusecase.py                                                                   |       16 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_getonekeyusecase.py                                                                 |       20 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/admin/keys/\_updatekeyusecase.py                                                                 |       31 |        0 |       10 |        1 |     97.56% |   32-\>35 |
| api/use\_cases/admin/organizations/\_createorganizationusecase.py                                               |       24 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/admin/organizations/\_deleteorganizationusecase.py                                               |       33 |        0 |       14 |        2 |     95.74% |42-\>45, 52-\>exit |
| api/use\_cases/admin/organizations/\_getoneorganizationusecase.py                                               |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/organizations/\_getorganizationsusecase.py                                                 |       20 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/organizations/\_updateorganizationusecase.py                                               |       29 |        0 |        8 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_createproviderusecase.py                                                       |       52 |        0 |       20 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_deleteproviderusecase.py                                                       |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/providers/\_getoneproviderusecase.py                                                       |       17 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_getprovidersusecase.py                                                         |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/providers/\_updateproviderusecase.py                                                       |       48 |        0 |       22 |        1 |     98.57% |   64-\>68 |
| api/use\_cases/admin/roles/\_createroleusecase.py                                                               |       24 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/roles/\_deleteroleusecase.py                                                               |       21 |        0 |        6 |        1 |     96.30% | 33-\>exit |
| api/use\_cases/admin/roles/\_getoneroleusecase.py                                                               |       19 |        0 |        4 |        1 |     95.65% | 30-\>exit |
| api/use\_cases/admin/roles/\_getrolesusecase.py                                                                 |       27 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/roles/\_updateroleusecase.py                                                               |       33 |        1 |        8 |        1 |     95.12% |        38 |
| api/use\_cases/admin/routers/\_createrouterusecase.py                                                           |       20 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_deleterouterusecase.py                                                           |       19 |        0 |        4 |        1 |     95.65% | 31-\>exit |
| api/use\_cases/admin/routers/\_getonerouterusecase.py                                                           |       17 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_getroutersusecase.py                                                             |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/admin/routers/\_updaterouterusecase.py                                                           |       30 |        0 |       10 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_createuserusecase.py                                                               |       40 |        0 |        8 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_deleteuserusecase.py                                                               |       28 |        0 |       10 |        1 |     97.37% | 43-\>exit |
| api/use\_cases/admin/users/\_getoneuserusecase.py                                                               |       23 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_getusersusecase.py                                                                 |       27 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/admin/users/\_updateuserusecase.py                                                               |       69 |        3 |       28 |        5 |     91.75% |68-\>71, 85, 86-\>89, 120, 125 |
| api/use\_cases/audio/\_createaudiotranscriptionsusecase.py                                                      |       38 |        0 |        4 |        0 |    100.00% |           |
| api/use\_cases/auth/\_authloginusecase.py                                                                       |       33 |        0 |        6 |        0 |    100.00% |           |
| api/use\_cases/auth/\_authssologinusecase.py                                                                    |       81 |        0 |       20 |        2 |     98.02% |119-\>140, 124-\>140 |
| api/use\_cases/chat/\_createchatcompletionsusecase.py                                                           |      110 |        0 |       28 |        2 |     98.55% |84-\>90, 180-\>196 |
| api/use\_cases/embeddings/\_createembeddingsusecase.py                                                          |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/health/\_gethealthmodelsusecase.py                                                               |       39 |        0 |        6 |        1 |     97.78% |   46-\>49 |
| api/use\_cases/health/\_providerlivenessprobe.py                                                                |       14 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/limits/\_getlimitsusecase.py                                                                     |       32 |        0 |        8 |        0 |    100.00% |           |
| api/use\_cases/me/\_getmeusecase.py                                                                             |       10 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/me/\_updatemeusecase.py                                                                          |       32 |        0 |        8 |        0 |    100.00% |           |
| api/use\_cases/models/\_bootstrapmodelsusecase.py                                                               |       79 |        0 |       28 |        0 |    100.00% |           |
| api/use\_cases/models/\_getmodelsusecase.py                                                                     |       15 |        0 |        0 |        0 |    100.00% |           |
| api/use\_cases/models/\_getonemodelusecase.py                                                                   |       23 |        0 |        6 |        1 |     96.55% |   32-\>35 |
| api/use\_cases/ocr/\_createocrusecase.py                                                                        |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/reranks/\_creatererankusecase.py                                                                 |        9 |        0 |        2 |        0 |    100.00% |           |
| api/use\_cases/services/\_providercapabilitiesprobe.py                                                          |       73 |        6 |       30 |        3 |     91.26% |52-53, 65-66, 114-115 |
| api/use\_cases/usage/\_getusagesusecase.py                                                                      |       17 |        0 |        0 |        0 |    100.00% |           |
| **TOTAL**                                                                                                       | **8191** |  **575** | **1462** |  **173** | **91.34%** |           |


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