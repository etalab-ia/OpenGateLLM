import logging
import subprocess
import time

logger = logging.getLogger(__name__)


def run_openmockllm(port: int, model_name: str = "openmockllm", **kwargs) -> subprocess.Popen:
    """Run the openmockllm process and return the process object."""

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

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    time.sleep(1)
    return process


def kill_openmockllm(process: subprocess.Popen, port: int, model_name: str) -> None:
    process.terminate()
    logger.info(f"vllm model - terminated (http://localhost:{port} - {model_name})")
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
