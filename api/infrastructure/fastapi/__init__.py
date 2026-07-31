"""AccessController is deliberately absent from these re-exports: import it from `.accesscontroller`.

It declares its `Depends` on providers held by `api/dependencies.py` — the composition root — and the root itself imports
`RequestContextUsageRecorder` from this package. Re-exporting the controller here would therefore make it reachable from the root
that it imports back, and the app would stop booting with
`ImportError: cannot import name '_authenticated_user_query' from partially initialized module 'api.dependencies'`.

The modules below are safe to re-export: they depend on the domain only, never on the composition root.
"""

from ._requestcontext import RequestContext
from ._requestcontextusagerecorder import RequestContextUsageRecorder

__all__ = [
    "RequestContext",
    "RequestContextUsageRecorder",
]
