import datetime as dt
import logging
from pathlib import Path
import random
import subprocess
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx

from api.schemas.admin.providers import CreateProvider, ProviderCarbonFootprintZone, ProviderType
from api.schemas.admin.roles import CreateRole, Limit, LimitType
from api.schemas.admin.routers import CreateRouter
from api.schemas.admin.tokens import CreateToken
from api.schemas.admin.users import CreateUser
from api.schemas.core.configuration import Metric
from api.schemas.models import ModelType
from api.utils.variables import (
    ENDPOINT__ADMIN_PROVIDERS,
    ENDPOINT__ADMIN_ROLES,
    ENDPOINT__ADMIN_ROUTERS,
    ENDPOINT__ADMIN_TOKENS,
    ENDPOINT__ADMIN_USERS,
)

logger = logging.getLogger(__name__)


def generate_test_id(prefix: str) -> str:
    return f"{prefix}_{dt.datetime.now().strftime("%Y%m%d%H%M%S")}_{uuid4()}"


def run_openmockllm(test_id: str, **kwargs) -> subprocess.Popen:
    """Run the openmockllm process and return the process object."""

    model_name = f"{test_id}_model"
    port = random.randint(40000, 41000)

    # Kill any process listening on the specified port
    try:
        result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True, check=False)
        if result.stdout.strip():
            pids = result.stdout.strip().split("\n")
            for pid in pids:
                subprocess.run(["kill", "-9", pid], check=False)
            time.sleep(0.5)  # Give time for the port to be released
    except Exception:
        pass  # Ignore errors if lsof is not available or port is already free

    command = ["openmockllm", "--port", str(port), "--model", model_name]
    for key, value in kwargs.items():
        command.append(f"--{key}")
        command.append(str(value))

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs/openmockllm")
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Create log file with unique name
    log_file_path = logs_dir / f"openmockllm_{test_id}_{port}.log"
    log_file = open(log_file_path, "w")

    logger.info(f"openmockllm logs will be written to: {log_file_path.absolute()}")

    process = subprocess.Popen(command, stdout=log_file, stderr=log_file)

    url = f"http://localhost:{port}"
    process.url = url
    process.model_name = model_name
    process.log_file = log_file
    process.log_file_path = log_file_path

    # Wait for the server to be ready with health check
    max_retries = 30  # 30 seconds max wait time
    retry_interval = 1  # Check every second
    for attempt in range(max_retries):
        # Check if process has terminated unexpectedly
        returncode = process.poll()
        if returncode is not None:
            # Process has terminated, try to read error from log file
            error_msg = "Unknown error"
            try:
                # Use wait with timeout to avoid blocking indefinitely
                process.wait(timeout=0.1)
                # Try to read the log file for error message
                if hasattr(process, "log_file_path") and process.log_file_path.exists():
                    process.log_file.flush()  # Ensure all data is written
                    error_msg = process.log_file_path.read_text()[-1000:]  # Last 1000 chars
            except Exception:
                # Log file might not be readable
                pass
            raise RuntimeError(
                f"openmockllm process failed to start. "
                f"Process exited with code {returncode}. "
                f"Check logs at {process.log_file_path if hasattr(process, "log_file_path") else "unknown"}. "
                f"Error: {error_msg}"
            )

        try:
            # Check if the server is responding by calling /v1/models endpoint
            response = httpx.get(f"{url}/v1/models", timeout=2)
            if response.status_code == 200:
                logger.info(f"openmockllm server is ready at {url} (attempt {attempt + 1})")
                return process
        except (httpx.ConnectError, httpx.TimeoutException, httpx.RequestError):
            # Server not ready yet, wait and retry
            if attempt < max_retries - 1:
                time.sleep(retry_interval)
            else:
                # Final attempt failed, check process status
                returncode = process.poll()
                if returncode is not None:
                    error_msg = "Unknown error"
                    try:
                        process.wait(timeout=0.1)
                        # Try to read the log file for error message
                        if hasattr(process, "log_file_path") and process.log_file_path.exists():
                            process.log_file.flush()  # Ensure all data is written
                            error_msg = process.log_file_path.read_text()[-1000:]  # Last 1000 chars
                    except Exception:
                        pass
                    raise RuntimeError(
                        f"openmockllm process failed to start after {max_retries} attempts. "
                        f"Process exited with code {returncode}. "
                        f"Check logs at {process.log_file_path if hasattr(process, "log_file_path") else "unknown"}. "
                        f"Error: {error_msg}"
                    )
                else:
                    raise RuntimeError(
                        f"openmockllm server at {url} did not become ready after {max_retries} attempts. "
                        f"Process is still running but not responding. "
                        f"Check logs at {process.log_file_path if hasattr(process, "log_file_path") else "unknown"}"
                    )

    return process


def kill_openmockllm(process: subprocess.Popen) -> None:
    process.terminate()
    logger.info(f"openmockllm model - terminated ({process.url} - {process.model_name})")
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    finally:
        # Close log file if it exists
        if hasattr(process, "log_file") and process.log_file:
            try:
                process.log_file.close()
            except Exception:
                pass


def create_router(model_name: str, model_type: ModelType, client: TestClient) -> int:
    payload = CreateRouter(name=model_name, type=model_type)
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROUTERS}", json=payload.model_dump())
    assert response.status_code == 201, response.text
    router_id = response.json()["id"]

    return router_id


def create_provider(
    router_id: int,
    provider_url: str,
    provider_key: str,
    provider_name: str,
    provider_type: ProviderType,
    client: TestClient,
    model_hosting_zone: ProviderCarbonFootprintZone = ProviderCarbonFootprintZone.WOR,
    model_total_params: int = 0,
    model_active_params: int = 0,
    qos_metric: Metric | None = None,
    qos_limit: float | None = None,
) -> int:
    payload = CreateProvider(
        router=router_id,
        type=provider_type,
        url=provider_url,
        key=provider_key,
        timeout=10,
        model_name=provider_name,
        model_hosting_zone=model_hosting_zone,
        model_total_params=model_total_params,
        model_active_params=model_active_params,
        qos_metric=qos_metric,
        qos_limit=qos_limit,
    )
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_PROVIDERS}", json=payload.model_dump())
    assert response.status_code == 201, response.text
    provider_id = response.json()["id"]

    return provider_id


def create_role(router_id: int, client: TestClient) -> int:
    payload = CreateRole(
        name=f"test-role-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}",
        limits=[
            Limit(router=router_id, type=LimitType.RPM, value=None),
            Limit(router=router_id, type=LimitType.RPD, value=None),
            Limit(router=router_id, type=LimitType.TPM, value=None),
            Limit(router=router_id, type=LimitType.TPD, value=None),
        ],
    )

    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROLES}", json=payload.model_dump())
    assert response.status_code == 201, response.text
    role_id = response.json()["id"]

    return role_id


def create_user(role_id: int, client: TestClient) -> int:
    payload = CreateUser(
        name=f"test-user-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}",
        email=f"test-user-{dt.datetime.now().strftime("%Y%m%d%H%M%S")}@example.com",
        role=role_id,
        password="test-password",
    )
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_USERS}", json=payload.model_dump())
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]

    return user_id


def create_token(user_id: int, token_name: str, client: TestClient) -> str:
    payload = CreateToken(
        name=token_name,
        user=user_id,
        expires=int((time.time()) + 60 * 10),
        password="test-password",
    )
    response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_TOKENS}", json=payload.model_dump())
    assert response.status_code == 201, response.text

    key_id = response.json()["id"]
    key = response.json()["token"]

    return key_id, key
