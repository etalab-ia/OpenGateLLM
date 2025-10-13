# Environment variables

In addition to the configuration file (see the [configuration documentation](./configuration.md)), you can set the following environment variables:

| Variable    | Required | Type | Values | Default | Description |
| --- | --- | --- | --- | --- | --- |
| CONFIG_FILE | Optional | str | | `"config.yml"` | Path to the configuration file |
| SERVER      | Optional | str | `"gunicorn"`, `"uvicorn"` | `"gunicorn"` | Server to use for the API |
| SERVER_CMD_ARGS | Optional | str | | `""` | Additional server command arguments (ex. --log-config app/log.conf) |