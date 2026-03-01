---
title: Environment variables
sidebar:
  label: "[lucide:dollar-sign] Environment variables"
  order: 1
---
## API 

In addition to the configuration file (see the [configuration file documentation](/configuration/configuration_file/)), you can set the following environment variables:

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| CONFIG_FILE | str | `"config.yml"` | Path to the configuration file. |
| GUNICORN_CMD_ARGS | str | `""` | Additional gunicorn command arguments (ex. `--log-config app/log.conf`). |
| PROMETHEUS_MULTIPROC_DIR | str | `"/tmp/prometheus_multiproc"` | Directory to store Prometheus multiprocessing files. |

## Playground

For adapt the playground docker image for your deployment, you can build it with the following arguments. For more information, consult the [reflex self-hosting documentation](https://reflex.dev/docs/hosting/self-hosting/).

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| CONFIG_FILE | str | `"config.example.yml"` | Path to your configuration file. |
| REFLEX_BACKEND_URL | str | `"http://localhost:8500"` | URL of the backend API. |
| REFLEX_FRONTEND_URL | str | `"http://localhost:8501"` | URL of the frontend application. |
| REFLEX_FRONTEND_PATH | str | `""` | Path of the frontend application. |
| FAVICON | str | `"./playground/assets/logo.svg"` | Path to your favicon file. |

Example: 
```bash
 docker build --build-arg \
 CONFIG_FILE=config.yml \
 FAVICON=./playground/assets/logo.svg \
 --file playground/Dockerfile --tag playground:latest .
```