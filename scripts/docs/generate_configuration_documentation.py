import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "playground"))
os.environ["CONFIG_FILE"] = os.path.join(PROJECT_ROOT, "config.example.yml")

from api.schemas.core.configuration import ConfigFile as ApiConfigFile  # noqa: E402 # type: ignore
from app.core.configuration import ConfigFile as PlaygroundConfigFile  # noqa: E402 # type: ignore

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=str, default=os.path.join("./docs/docs/getting-started/configuration_file.md"))


def get_documentation_data(title: str, data: list, properties: dict, defs: dict, header: str = "", level: int = 1):
    # attribute, type, description, required, default, values, examples
    table = list()
    for property in sorted(properties):
        description = properties[property].get("description", "")
        default = convert_field_to_string_if_dict(
            properties[property].get(
                "default",
                properties[property].get("extra_json_schema", {}).get("default", "**required**"),
            )
        )
        examples = convert_field_to_string_if_dict(properties[property].get("examples", [""])[0])

        if "anyOf" in properties[property]:
            properties[property].update(properties[property]["anyOf"][0])

        if "$ref" in properties[property]:
            ref_key = properties[property]["$ref"].split("/")[-1]
            ref = defs[ref_key]
            type = ref.get("type", "")
            values = ref.get("enum", [])

            # neested object section, get the data from the nested section
            if "properties" in ref:
                data = get_documentation_data(
                    title=ref_key,
                    data=data,
                    properties=ref["properties"],
                    defs=defs,
                    header=ref.get("description"),
                    level=level + 1,
                )
                description += f" For details of configuration, see the [{ref_key} section](#{ref_key.lower().replace(" ", "-")})."

        else:
            type = properties[property].get("type", "")
            values = properties[property].get("enum", [])

        if type == "array" and "$ref" in properties[property]["items"]:
            ref_key = properties[property]["items"]["$ref"].split("/")[-1]
            ref = defs[ref_key]

            # neested array section, get the data from the nested section
            if "properties" in ref:
                data = get_documentation_data(
                    title=ref_key,
                    data=data,
                    properties=ref["properties"],
                    defs=defs,
                    header=ref.get("description"),
                    level=level + 1,
                )
                description += f" For details of configuration, see the [{ref_key} section](#{ref_key.lower().replace(" ", "-")})."
            else:
                values = ref.get("enum", [])

        table.append([property, type, description, default, values, examples])

    data.append({"title": title, "table": table, "level": level, "header": header})

    return data


def get_example_configuration(config_example: str):
    data = f"""
## Example

The following is an example of configuration file:

```yaml
{config_example}
```

"""

    return data


def convert_field_to_string_if_dict(field):
    if isinstance(field, dict):
        return "`" + str(field) + "`"
    return field


def convert_to_markdown(data: list):
    markdown = ""
    for item in reversed(data):
        markdown += f"{"#" * (item["level"] + 1)} {item["title"]}\n"
        if item["header"]:
            markdown += f"{item["header"]}\n<br></br>\n\n"

        if len(item["table"]) > 0:
            markdown += "| Attribute | Type | Description | Default | Values | Examples |\n"
            markdown += "| --- | --- | --- | --- | --- | --- |\n"
            for row in item["table"]:
                if len(row[4]) > 10:
                    row[4] = "• " + "<br></br>• ".join(row[5][:8]) + "<br></br>• ..."
                elif len(row[4]) > 0:
                    row[4] = "• " + "<br></br>• ".join(row[4])
                else:
                    row[4] = ""

                markdown += "| " + " | ".join(str(cell) for cell in row) + " |\n"

        elif item["header"] == "":
            markdown += "No settings."

        markdown += "\n<br></br>\n\n"

    return markdown


if __name__ == "__main__":
    args = parser.parse_args()
    assert args.output.endswith(".md"), f"Output file must end with .md ({args.output})"
    assert os.path.exists(os.path.dirname(args.output)), f"Output directory does not exist ({os.path.dirname(args.output)})"

    with open(file=os.path.join("./scripts/docs/configuration_header.md")) as f:
        header = f.read()
        f.close()
    markdown = header + "\n"

    with open(file=os.path.join("config.example.yml")) as f:
        config_example = f.read()
        f.close()
    markdown += get_example_configuration(config_example=config_example)

    schema = ApiConfigFile.model_json_schema()
    api_data = get_documentation_data(
        title="API configuration",
        data=[],
        properties=schema["properties"],
        header=schema.get("description", ""),
        defs=schema["$defs"],
    )
    markdown += convert_to_markdown(data=api_data)

    schema = PlaygroundConfigFile.model_json_schema()
    playground_data = get_documentation_data(
        title="Playground configuration",
        data=[],
        properties=schema["properties"],
        header=schema.get("description", ""),
        defs=schema["$defs"],
    )
    markdown += convert_to_markdown(data=playground_data)

    with open(file=args.output, mode="w") as f:
        f.write(markdown)
        f.close()
