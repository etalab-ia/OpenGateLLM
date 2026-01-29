---
slug: rag-scaling
title: RAG scaling
authors: [leoguillaume]
tags: [RAG]
---

Face à des difficultés de scalabilité de notre vector store, nous avons décider de reviser notre approche en nous basant sur les recommandations préconisées par Elasticsearch. Les principales modifications sont les suivantes :
* Dépréciation du support de Qdrant au profit d'Elasticsearch
* Fusion des index Elasticsearch dans un index unique
* Métadonnées pré-définies pour les documents

<!-- truncate -->

## Context

Actuellement, nous supportons deux technologies de vector store : Qdrant et Elasticsearch. Nous avons décidé il y a quelque mois de ce concentrer sur Elasticsearch pour la gestion de nos collections de documents. Nous revenons ici sur les raisons de ce choix. 

Cependant depuis quelques semaines nous avons constaté des difficultés de scalabilité avec Elasticsearch. Ces problèmes proviennent de la manière dont nous avons implémenté Elasticsearch dans OpenGateLLM. Pour résoudre ces problèmes, nous avons décidé de reviser notre approche, ce qui implique des changements majeurs et une migrations des données.

A cet fin nous vous proposons ici de détailler les modifications que nous avons apportées et 

### Fin du support de Qdrant


### Fusion des index Elasticsearch dans un index unique

### Métadonnées pré-définies pour les documents