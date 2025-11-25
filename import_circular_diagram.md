# Diagramme d'import circulaire

```mermaid
graph TD
    A[infrastructure/__init__.py] -->|import PostgresRouterRepository| B[_postgresrouterrepository.py]
    B -->|from api.domain.router import<br/>Model, ModelCosts, ModelType, Router,<br/>RouterLoadBalancingStrategy, RouterRepository| C[domain/router/__init__.py]
    C -->|from ._routerrepository import RouterRepository| D[_routerrepository.py]
    D -->|from api.domain.router import Model, Router| C
    
    C -->|from .model import Model, ModelCosts, ModelType| E[model.py]
    C -->|from .router import Router, RouterLoadBalancingStrategy| F[router.py]
    
    style D fill:#ff6b6b
    style C fill:#ff6b6b
    style B fill:#ffd93d
    style A fill:#6bcf7f
```

## Explication du cycle

Le problème se situe dans la chaîne d'import suivante :

1. **infrastructure/__init__.py** importe `PostgresRouterRepository`
2. **_postgresrouterrepository.py** importe depuis `api.domain.router`
3. **domain/router/__init__.py** commence à s'initialiser et importe `RouterRepository` depuis `_routerrepository.py`
4. **_routerrepository.py** essaie d'importer `Model` et `Router` depuis `api.domain.router`
5. ❌ **CYCLE** : `api.domain.router` n'est pas encore complètement initialisé car il attend la fin de l'import de `_routerrepository.py`

## Solution

Pour résoudre ce problème, `_routerrepository.py` devrait importer directement depuis les modules spécifiques plutôt que depuis le package `__init__.py` :

```python
# Au lieu de :
from api.domain.router import Model, Router

# Utiliser :
from api.domain.router.model import Model
from api.domain.router.router import Router
```

