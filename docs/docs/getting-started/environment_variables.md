# Environment variables

## API 

In addition to the configuration file (see the [configuration documentation](./configuration.md)), you can set the following environment variables:

| Variable | Type | Default | Description |
| --- | --- | --- | --- |
| CONFIG_FILE | str | `"config.yml"` | Path to the configuration file. |
| GUNICORN_CMD_ARGS | str | `""` | Additional gunicorn command arguments (ex. `--log-config app/log.conf`). |


## Playground

For adapt the playground docker image for your deployment, you can build it with the following arguments:

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| CONFIG_FILE | str | `"config.example.yml"` | Path to your configuration file. |
| API_HOST | str | `"api"` | Host name of the API. By default, `api` is the hostname in docker compose file. |
| FAVICON | str | `"./playground/assets/favicon.ico"` | Path to your favicon file. |

Example: 
```bash
 docker build --build-arg \
 CONFIG_FILE=config.yml \
 API_HOST=api \
 FAVICON=./playground/assets/favicon.ico \
 --file playground/Dockerfile --tag playground:latest .
