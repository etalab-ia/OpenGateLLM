"""
Publish the authorization model to OpenFGA.

Runs once per deploy, next to `alembic upgrade head` in scripts/startup_api.sh -- the OpenFGA model is application
schema in the same sense the Postgres schema is, even though both services live on their own machines.
"""

import asyncio
import logging
import sys

from api.infrastructure.openfga import OpenFgaAuthorizationProvisioner
from api.utils.configuration import get_configuration

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("provision_openfga")


async def main() -> int:
    openfga = get_configuration().dependencies.openfga
    try:
        provisioner = OpenFgaAuthorizationProvisioner(
            url=openfga.url,
            store_name=openfga.store_name,
            api_token=openfga.api_token,
        )
        authorization_model_id = await provisioner.provision()
    except Exception:
        logger.exception("Could not publish the authorization model to %s.", openfga.url)
        return 1

    logger.info("Authorization model published: %s", authorization_model_id)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
