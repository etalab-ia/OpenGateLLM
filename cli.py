import argparse
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
import tomllib
import urllib.error
import urllib.request

from pydantic_settings import BaseSettings, SettingsConfigDict
from rich import box
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.padding import Padding
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
import yaml

project_root = Path(__file__).resolve().parent


class EnvFile(BaseSettings):
    compose_file: str = "compose.yml"
    api_port: int = 8000
    playground_port: int = 8501
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")


def get_project_version() -> str:
    with (project_root / "pyproject.toml").open("rb") as file:
        data = tomllib.load(file)
    return data["project"]["version"]


def display_header(console: Console, tag: str | None = None) -> None:
    version = get_project_version()
    title = Text()
    title.append("\n")
    title.append(" OpenGateLLM ", style="bold black on bright_green")
    title.append(" ")
    if tag:
        title.append(f" {tag} ", style="bold black on bright_blue")
    title.append(" ")
    title.append(f"– v{version}", style="bright_grey")
    title.append("\n")
    console.print(title)


def display_make_help(console: Console) -> None:
    display_header(console)
    commands = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
    commands.add_column("Command", style="bold")
    commands.add_column("Description")
    commands.add_row("quickstart [env=.env]", "Start services in docker environment")
    commands.add_row("dev [env=.env]", "Start services in local development mode")
    commands.add_row("create-user", "Create a first user")
    commands.add_row("lint", "Run linter")
    commands.add_row("test-unit", "Run unit tests")
    commands.add_row("test-integ", "Run integration tests")

    options = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
    options.add_column("Option", style="bold")
    options.add_column("Description")
    options.add_row("env", "Optional, environment file to use. Default: .env")

    body = Group(
        Text("Usage: make COMMAND [OPTIONS]", style="bold"),
        Text(""),
        commands,
        Text(""),
        options,
    )
    console.print(Panel(body, title="Make Help", border_style="bright_blue", padding=(1, 2)))


def setup(console: Console, env_file: str) -> tuple[EnvFile | None, int]:
    if not os.path.exists(env_file):
        if re.match(r"^(\.\/)?\.env(\.(example))?$", env_file):
            shutil.copy2(".env.example", ".env")
            env_file = ".env"
            console.print(f"🚸 Environment file {env_file} does not exist, creating it from {env_file}.example and using it.", style="yellow")  # fmt: off
        else:
            console.print(f"❌ Environment file {env_file} does not exist.", style="bold red")
            return (None, 1)

    env = EnvFile(_env_file=env_file)
    env._env_file = env_file

    if not os.path.exists(env.config_file):
        if re.match(r"^(\.\/)?config\.yml(\.(example))?$", env.config_file):
            shutil.copy2("config.example.yml", env.config_file)
            console.print(f"🚸 Configuration file {env.config_file} does not exist, creating it from config.example.yml and using it.", style="yellow")  # fmt: off
        else:
            console.print(f"❌ Configuration file {env.config_file} does not exist. Setup CONFIG_FILE environment variable to modify it.", style="bold red")  # fmt: off
            return (None, 1)

    if not os.path.exists(env.compose_file):
        if re.match(r"^(\.\/)?compose\.yml(\.(example))?$", env.compose_file):
            shutil.copy2("compose.example.yml", env.compose_file)
            console.print(f"🚸 Compose file {env.compose_file} does not exist, creating it from compose.example.yml and using it.", style="yellow")  # fmt: off
        else:
            console.print(f"❌ Compose file {env.compose_file} does not exist. Setup COMPOSE_FILE environment variable to modify it.", style="bold red")  # fmt: off
            return (None, 1)

    return (env, 0)


def run_docker_compose(console: Console, env: EnvFile, local_api: bool = False, local_playground: bool = False) -> int:
    exclude_services = []
    if local_api:
        exclude_services.append("api")
    if local_playground:
        exclude_services.append("playground")

    try:
        with open(env.compose_file) as file:
            data = yaml.safe_load(file)
            services = [service for service in data.get("services", {}).keys() if service not in exclude_services]
            assert services, f"No services found in compose file {env.compose_file}."
    except Exception as error:
        console.print(f"❌ {error}", style="bold red")  # fmt: off
        return 1

    try:
        command = [
            "docker",
            "compose",
            "--env-file",
            env._env_file,
            "--file",
            env.compose_file,
            "up",
            *services,
            "--detach",
            "--quiet-pull",
            "--wait",
        ]
        console.print(f":whale: $ {' '.join(command)}", style="dim")
        completed = subprocess.run(command, cwd=project_root, check=False)
        console.print()
        return completed.returncode
    except KeyboardInterrupt:
        return 130


def print_log_line(console: Console, service: str, line: str) -> None:
    service_name = service.split(" ")[-1]
    service_styles = {"API": "bold black on bright_green", "Playground": "bold black on bright_magenta"}
    style = service_styles.get(service_name, "black on white")

    clean_line = strip_ansi(line).replace("\r", "")
    output = Text()
    output.append(f" {service_name} ", style=style)
    output.append(f" {clean_line}", style="default")
    console.print(output, highlight=False)


def strip_ansi(line: str) -> str:
    return re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]", "", line)


def format_duration(seconds: float) -> str:
    return f"{seconds:.1f}s"


def build_local_services_status_table(rows: list[tuple[RenderableType, str, RenderableType, float]]) -> Table:
    table = Table.grid(expand=True)
    table.add_column(justify="left")
    table.add_column(justify="right")

    for indicator, service, status, started_at in rows:
        left_line = Table.grid(padding=(0, 1))
        left_line.add_column(no_wrap=True)
        left_line.add_column(no_wrap=True, width=38)
        left_line.add_column(no_wrap=True)
        left_line.add_row(Padding(indicator, (0, 0, 0, 1)), Text(service), status)

        right_line = Text()
        if started_at > 0:
            elapsed = time.perf_counter() - started_at
            right_line.append(f"{format_duration(elapsed)}", style="blue")

        table.add_row(left_line, Padding(right_line, (0, 1, 0, 0)))

    return table


def display_local_service_start(
    console: Console,
    service: str,
    status_text: str,
    started_at: float = 0.0,
    indicator: str = "✔",
    indicator_style: str = "green",
    status_style: str = "underline bold green",
) -> None:
    table = build_local_services_status_table([(Text(indicator, style=indicator_style), service, Text(status_text, style=status_style), started_at)])
    console.print(table)


def _extract_complete_lines(buffer: str, chunk: bytes) -> tuple[list[str], str]:
    text = buffer + chunk.decode("utf-8", errors="replace")
    parts = text.split("\n")
    return parts[:-1], parts[-1]


def is_http_200(url: str, timeout: float = 1.5) -> bool:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def stop_process_group(process: subprocess.Popen, grace_period_seconds: float = 5.0) -> None:
    if process.poll() is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except PermissionError:
        process.terminate()

    deadline = time.perf_counter() + grace_period_seconds
    while process.poll() is None and time.perf_counter() < deadline:
        time.sleep(0.1)

    if process.poll() is not None:
        return

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except PermissionError:
        process.kill()


def stop_local_processes(processes: dict[subprocess.Popen, dict]) -> None:
    for process in processes:
        stop_process_group(process)


def run_local_api(console: Console, env: EnvFile) -> tuple[subprocess.Popen, str, str, float]:
    log_level = "debug" if env.debug else "info"
    started_at = time.perf_counter()
    command = [
        "bash",
        "-c",
        (
            f"set -a; . {env._env_file}; "
            "export PYTHONUNBUFFERED=1; "
            "export REDIS_HOST=localhost; "
            "export POSTGRES_HOST=localhost; "
            "export ELASTICSEARCH_HOST=localhost; "
            "python -m alembic -c api/alembic.ini upgrade head && "
            f"python -u -m uvicorn api.main:app --host localhost --port {env.api_port} --reload --reload-dir api --log-level {log_level} --use-colors"
        ),
    ]

    console.print(f":sparkles: $ {command[-1].split('&& ')[-1]}", style="dim")
    process = subprocess.Popen(
        command,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
        start_new_session=True,
    )
    return process, "OpenGateLLM API", f"http://localhost:{env.api_port}/docs", started_at


def run_local_playground(console: Console, env: EnvFile) -> tuple[subprocess.Popen, str, str, float]:
    started_at = time.perf_counter()
    log_level = "debug" if env.debug else "info"
    config_file = os.path.join("..", Path(env.config_file).absolute())
    command = [
        "bash",
        "-c",
        (
            f"set -a; . {env._env_file}; "
            "cd ./playground; "
            f"export REDIS_HOST=localhost; "
            f'export CONFIG_FILE="{config_file}"; '
            f"export OPENGATELLM_URL=http://localhost:{env.api_port}; "
            f"reflex run --env dev --loglevel {log_level}"
        ),
    ]

    console.print(f":laptop_computer: $ {command[-1].split('; ')[-1]}", style="dim")
    process = subprocess.Popen(
        command,
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=False,
        bufsize=0,
        start_new_session=True,
    )
    return (
        process,
        "OpenGateLLM Playground",
        f"http://localhost:{env.playground_port}",
        started_at,
    )


def run_local_services(console: Console, env: EnvFile, local_api: bool, local_playground: bool) -> int:
    healthcheck_targets: dict[str, str] = {}
    if local_api:
        healthcheck_targets["OpenGateLLM API"] = f"http://localhost:{env.api_port}/health"
    if local_playground:
        healthcheck_targets["OpenGateLLM Playground"] = f"http://localhost:{env.playground_port}"

    processes: dict[subprocess.Popen, dict] = {}
    startup_selector = selectors.DefaultSelector()
    live_selector: selectors.BaseSelector | None = None

    try:

        def register_local_process(process: subprocess.Popen, service: str, url: str, started_at: float) -> None:
            assert process.stdout is not None
            startup_selector.register(process.stdout, selectors.EVENT_READ, process)
            processes[process] = {
                "service": service,
                "url": url,
                "started_at": started_at,
                "buffer": [],
                "partial": "",
            }

        starters = []
        if local_api:
            starters.append(run_local_api)
        if local_playground:
            starters.append(run_local_playground)

        for starter in starters:
            process, service, url, started_at = starter(console, env)
            register_local_process(process, service, url, started_at)

        if not processes:
            return 0

        service_urls = {data["service"]: data["url"] for data in processes.values()}
        service_started_at = {data["service"]: data["started_at"] for data in processes.values()}
        health_status = {service: False for service in healthcheck_targets}
        healthcheck_timeout_seconds = 120.0
        healthcheck_interval_seconds = 2.0
        healthcheck_deadline = time.perf_counter() + healthcheck_timeout_seconds
        next_healthcheck_at = time.perf_counter()
        recent_lines: list[str] = []
        timed_out_services: list[str] = []

        def _status_renderable() -> Table:
            status_rows: list[tuple[RenderableType, str, RenderableType, float]] = []
            for service, healthy in health_status.items():
                indicator = Text("✔", style="green") if healthy else Spinner("dots", style="yellow")
                status = Text(service_urls[service], style="green") if healthy else Text("Waiting")
                status_rows.append((indicator, service, status, service_started_at[service]))
            return build_local_services_status_table(status_rows)

        def _startup_renderable() -> Group:
            status_block = _status_renderable()
            log_lines = recent_lines[-6:]
            logs_block: RenderableType
            if log_lines:
                logs_block = Group(*[Text(f"  {line}", style="dim") for line in log_lines])
            else:
                logs_block = Text("  Waiting for startup logs...", style="dim")
            return Group(
                status_block,
                logs_block,
            )

        with Live(_startup_renderable(), console=console, refresh_per_second=10, transient=False) as live:
            while True:
                for process, data in processes.items():
                    if process.poll() is not None:
                        for buffered_line in data["buffer"]:
                            print_log_line(console, data["service"], buffered_line)
                        return process.returncode

                if health_status and all(health_status.values()):
                    live.update(_status_renderable())
                    break
                if not health_status:
                    break

                now = time.perf_counter()
                if now >= next_healthcheck_at:
                    for service, url in healthcheck_targets.items():
                        if health_status[service]:
                            continue
                        health_status[service] = is_http_200(url)
                    next_healthcheck_at = now + healthcheck_interval_seconds
                    live.update(_startup_renderable())

                if now >= healthcheck_deadline:
                    unready_services = [service for service, healthy in health_status.items() if not healthy]
                    if unready_services:
                        timed_out_services = unready_services
                    break

                for key, _ in startup_selector.select(timeout=0.1):
                    process = key.data
                    data = processes[process]
                    stream = key.fileobj
                    chunk = os.read(stream.fileno(), 65536)
                    if chunk == b"":
                        if data["partial"]:
                            line = data["partial"]
                            data["buffer"].append(line)
                            clean_line = strip_ansi(line).replace("\r", "")
                            recent_lines.append(clean_line)
                            data["partial"] = ""
                        live.update(_startup_renderable())
                        continue

                    lines, data["partial"] = _extract_complete_lines(data["partial"], chunk)
                    for line in lines:
                        data["buffer"].append(line)
                        clean_line = strip_ansi(line).replace("\r", "")
                        recent_lines.append(clean_line)
                    live.update(_startup_renderable())

        if timed_out_services:
            for service, healthy in health_status.items():
                if healthy:
                    display_local_service_start(
                        console,
                        service,
                        service_urls[service],
                        started_at=service_started_at[service],
                    )
                else:
                    display_local_service_start(
                        console,
                        service,
                        "Unhealthy",
                        started_at=service_started_at[service],
                        indicator="✖",
                        indicator_style="bold red",
                        status_style="bold red",
                    )
            for process, data in processes.items():
                if process.poll() is not None:
                    continue
                for buffered_line in data["buffer"]:
                    print_log_line(console, data["service"], buffered_line)
            return 1

        console.print()
        console.rule(title="Logs", style="bold blue")

        for data in processes.values():
            data["buffer"].clear()

        live_selector = selectors.DefaultSelector()
        for process in processes:
            if process.stdout is not None:
                live_selector.register(process.stdout, selectors.EVENT_READ, process)

        while live_selector.get_map():
            for key, _ in live_selector.select(timeout=0.1):
                process = key.data
                data = processes[process]
                stream = key.fileobj
                chunk = os.read(stream.fileno(), 65536)
                if chunk == b"":
                    if data["partial"]:
                        line = data["partial"]
                        print_log_line(console, data["service"], line)
                        data["partial"] = ""
                    live_selector.unregister(stream)
                    continue

                lines, data["partial"] = _extract_complete_lines(data["partial"], chunk)
                for line in lines:
                    print_log_line(console, data["service"], line)

        exit_codes = [process.wait() for process in processes]
        return next((code for code in exit_codes if code != 0), 0)
    except KeyboardInterrupt:
        return 130
    finally:
        stop_local_processes(processes)
        if live_selector is not None:
            live_selector.close()
        startup_selector.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=str, default=".env")
    parser.add_argument("--make-help", action="store_true", default=False)
    parser.add_argument("--quickstart", action="store_true", default=False)
    parser.add_argument("--dev", action="store_true", default=False)
    parser.add_argument("--test-integ", action="store_true", default=False)

    args = parser.parse_args()
    console = Console()

    if args.make_help:
        display_make_help(console)
        raise SystemExit(0)

    elif args.quickstart:
        display_header(console)
        env, exit_code = setup(console, env_file=args.env_file)
        if exit_code != 0:
            raise SystemExit(exit_code)
        exit_code = run_docker_compose(console, env=env, local_api=False, local_playground=False)
        if exit_code != 0:
            raise SystemExit(exit_code)

        display_local_service_start(console, "OpenGateLLM API", f"http://localhost:{env.api_port}")
        display_local_service_start(console, "OpenGateLLM Playground", f"http://localhost:{env.playground_port}")

    elif args.dev:
        display_header(console, tag="dev")
        env, exit_code = setup(console, env_file=args.env_file)
        if exit_code != 0:
            raise SystemExit(exit_code)
        exit_code = run_docker_compose(console, env=env, local_api=True, local_playground=True)
        if exit_code != 0:
            raise SystemExit(exit_code)
        exit_code = run_local_services(console, env=env, local_api=True, local_playground=True)
        if exit_code != 0:
            raise SystemExit(exit_code)

    elif args.test_integ:
        display_header(console, tag="test")
        env, exit_code = setup(console, env_file=str(project_root / ".github/.env.ci"))
        if exit_code != 0:
            raise SystemExit(exit_code)
        exit_code = run_docker_compose(console, env=env, local_api=False, local_playground=False)
        if exit_code != 0:
            raise SystemExit(exit_code)
        raise SystemExit(0)

    else:  # error
        display_header(console)
        console.print("❌ Invalid command", style="bold red")
        display_make_help(console)
        raise SystemExit(1)

    raise SystemExit(0)


if __name__ == "__main__":
    main()
