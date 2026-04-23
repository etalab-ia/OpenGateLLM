import argparse
import os
import sys

from pydantic import BaseModel, Field
from tabulate import tabulate

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "playground"))
os.environ["CONFIG_FILE"] = os.path.join(PROJECT_ROOT, "config.example.yml")

from api.schemas.core.configuration import ConfigFile as ApiConfigFile  # noqa: E402 # type: ignore
from app.core.configuration import ConfigFile as PlaygroundConfigFile  # noqa: E402 # type: ignore

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=str, default=os.path.join("./docs/src/content/docs/configuration/configuration_file.mdx"))


class Row(BaseModel):
    attribute: str
    types: list[str]
    description: str
    default: str
    values: list
    examples: list


class Table(BaseModel):
    title: str
    description: str
    rows: list[Row]
    tables: list["Table"] = Field(default_factory=list)  # recursive field


def get_description(property: dict, ref_keys: list[str]):
    description = property.get("description", "")
    for ref_key in ref_keys:
        description += f" For details of configuration, see the [{ref_key} section](#{ref_key.lower().replace(' ', '-')})."

    return description


def get_default(property: dict):
    default = property.get("default", "required")
    default = str(default)
    return default


def get_attribute(property: dict):
    return property.get("title", "")


def get_types(property: dict):
    type = property.get("type")
    types = [] if type is None else [type]
    if "anyOf" in property:
        for any_of in property["anyOf"]:
            if "type" in any_of:
                types.append(any_of.get("type"))

    return list(set(types))


def get_values(property: dict):
    values = property.get("enum", [])
    if "anyOf" in property:
        for any_of in property["anyOf"]:
            if "enum" in any_of:
                values.extend(any_of.get("enum", []))

    elif property.get("type") == "array":
        values.extend(property.get("items", {}).get("enum", []))

    elif "oneOf" in property:
        for one_of in property["oneOf"]:
            values.extend(one_of.get("enum", []))

    return list(set(values))


def get_examples(property: dict):
    return property.get("examples", [])


def replace_enum_ref_by_enum_schema_and_extract_ref_keys(property: dict, enum_schemas: dict) -> tuple[dict, list[str]]:
    def _extract_key(ref: str) -> str:
        return ref.split("/")[-1]

    ref_keys = []
    if "$ref" in property:
        if property["$ref"] in enum_schemas:
            property.update(enum_schemas[property["$ref"]])
            property.pop("$ref")
        else:
            ref_key = _extract_key(ref=property["$ref"])
            ref_keys.append(ref_key)

    elif property.get("type") == "array" and "$ref" in property["items"]:
        if property["items"]["$ref"] in enum_schemas:
            property["items"] = enum_schemas[property["items"]["$ref"]]
        else:
            ref_key = _extract_key(ref=property["items"]["$ref"])
            ref_keys.append(ref_key)

    elif "anyOf" in property:
        for i, any_of in enumerate(property["anyOf"]):
            if "$ref" in any_of:
                if any_of["$ref"] in enum_schemas:
                    property["anyOf"][i] = enum_schemas[any_of["$ref"]]
                else:
                    ref_key = _extract_key(ref=any_of["$ref"])
                    ref_keys.append(ref_key)

    elif "oneOf" in property:
        for i, one_of in enumerate(property["oneOf"]):
            if "$ref" in one_of:
                if one_of["$ref"] in enum_schemas:
                    property["oneOf"][i] = enum_schemas[one_of["$ref"]]
                else:
                    ref_key = _extract_key(ref=one_of["$ref"])
                    ref_keys.append(ref_key)

    return property, ref_keys


def build_row(attribute: str, property: dict, ref_keys: list[str]):
    description = get_description(property=property, ref_keys=ref_keys)
    default = get_default(property=property)
    types = get_types(property=property)
    values = get_values(property=property)
    examples = get_examples(property=property)
    row = Row(attribute=attribute, types=types, description=description, default=default, values=values, examples=examples)

    return row


def parse_schema(table: Table, properties: dict, defs: dict, enum_schemas: dict):
    for attribute, property in properties.items():
        if property.get("deprecated", False):
            continue

        property, ref_keys = replace_enum_ref_by_enum_schema_and_extract_ref_keys(property=property, enum_schemas=enum_schemas)
        row = build_row(attribute=attribute, property=property, ref_keys=ref_keys)
        table.rows.append(row)

        for ref_key in ref_keys:
            if "properties" in defs[ref_key]:
                sub_table = Table(title=defs[ref_key].get("title", ""), description=get_description(defs[ref_key], ref_keys=[]), rows=[], tables=[])
                sub_table = parse_schema(table=sub_table, properties=defs[ref_key]["properties"], defs=defs, enum_schemas=enum_schemas)
                table.tables.append(sub_table)

    return table


def handle_acorn(text: str) -> str:
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    return text


def format_examples(examples: list) -> str:
    if len(examples) > 0:
        example = str(examples[0])
        example = handle_acorn(text=example)
        return example
    else:
        return ""


def format_description(description: str):
    description = handle_acorn(text=description)
    return description.replace("|", "\\|")


def format_default(default: str) -> str:
    default = handle_acorn(text=default)
    default = default if default != "required" else "**required**"
    return default


def format_values(values: list) -> str:
    values = [handle_acorn(text=value) for value in values]
    if len(values) > 10:
        return "• " + "<br></br>• ".join(values[:8]) + "<br></br>• ..."
    elif len(values) > 0:
        return "• " + "<br></br>• ".join(values)
    else:
        return ""


def format_types(types: list) -> str:
    types = [handle_acorn(text=type) for type in types]
    return ", ".join(types)


def format_row(row: Row):
    row = row.model_dump()
    row["description"] = format_description(row["description"])
    row["default"] = format_default(row["default"])
    row["values"] = format_values(row["values"])
    row["examples"] = format_examples(row["examples"])
    row["types"] = format_types(row["types"])
    row = [value for key, value in row.items()]

    return row


def convert_to_markdown(table: Table, markdown: str = "", level: int = 1):
    breakline_small = "\n\n"
    breakline_large = "\n\n<br></br>\n\n"
    level += 1
    markdown += f"{'#' * level} {table.title}{breakline_small}"
    markdown += f"{table.description}{breakline_large}"

    if len(table.rows) == 0:
        markdown += f"**No settings.**{breakline_large}"
        return markdown

    md_table = tabulate(
        tabular_data=[format_row(row) for row in table.rows],
        headers=["Attribute", "Type", "Description", "Default", "Values", "Examples"],
        tablefmt="pipe",
    )
    markdown += f"{md_table}{breakline_large}"

    if table.tables:
        markdown += "<Tabs>\n" if len(table.tables) > 1 else ""
        for sub_table in table.tables:
            markdown += f'<TabItem value="{sub_table.title}" label="{sub_table.title}">\n\n' if len(table.tables) > 1 else ""
            markdown = convert_to_markdown(table=sub_table, markdown=markdown, level=level)
            markdown += "</TabItem>\n" if len(table.tables) > 1 else ""
        markdown += f"</Tabs>{breakline_small}" if len(table.tables) > 1 else ""

    return markdown


def get_example_configuration(config_example: str):
    markdown = f"""
## Example

The following is an example of configuration file:

```yaml
{config_example}
```

"""

    return markdown


if __name__ == "__main__":
    args = parser.parse_args()
    assert args.output.endswith(".mdx"), f"Output file must end with .md ({args.output})"
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
    table = Table(title="API configuration", description=schema.get("description", ""), rows=[], tables=[])
    enum_schemas = {f"#/$defs/{attribute}": schema["$defs"][attribute] for attribute in schema["$defs"] if "enum" in schema["$defs"][attribute]}

    table = parse_schema(table=table, properties=schema["properties"], defs=schema["$defs"], enum_schemas=enum_schemas)
    markdown += convert_to_markdown(table=table)

    schema = PlaygroundConfigFile.model_json_schema()
    table = Table(title="Playground configuration", description=schema.get("description", ""), rows=[], tables=[])
    enum_schemas = {f"#/$defs/{attribute}": schema["$defs"][attribute] for attribute in schema["$defs"] if "enum" in schema["$defs"][attribute]}

    table = parse_schema(table=table, properties=schema["properties"], defs=schema["$defs"], enum_schemas=enum_schemas)
    markdown += convert_to_markdown(table=table)

    with open(file=args.output, mode="w") as f:
        f.write(markdown)
        f.close()
