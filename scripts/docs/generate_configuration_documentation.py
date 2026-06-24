import argparse
import html
import os
import re
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


SCOPE_API = "api"
SCOPE_PLAYGROUND = "playground"

SCOPE_LABELS: dict[str, str] = {
    SCOPE_API: "API",
    SCOPE_PLAYGROUND: "Playground",
}

SCOPE_ORDER = [SCOPE_API, SCOPE_PLAYGROUND]

SCOPE_BADGE_VARIANTS: dict[str, str] = {
    SCOPE_API: "note",
    SCOPE_PLAYGROUND: "tip",
}

TYPE_BADGE_VARIANT = "default"


class Row(BaseModel):
    attribute: str
    types: list[str]
    description: str
    default: str
    values: list
    examples: list
    scope: set[str] = Field(default_factory=set)


class Table(BaseModel):
    title: str
    description: str
    rows: list[Row]
    tables: list["Table"] = Field(default_factory=list)  # recursive field
    variant_rows: dict[str, list[Row]] | None = None
    legacy_anchors: list[str] = Field(default_factory=list)


VARIANT_TAB_LABELS: dict[str, str] = {
    "password": "Password",
    "oidc": "OIDC",
}

VARIANT_TAB_ICONS: dict[str, str] = {
    "password": "lucide:key",
    "oidc": "lucide:shield",
}

VARIANT_TAB_ORDER = ["password", "oidc"]


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
        if "discriminator" not in property:
            for i, one_of in enumerate(property["oneOf"]):
                if "$ref" in one_of:
                    if one_of["$ref"] in enum_schemas:
                        property["oneOf"][i] = enum_schemas[one_of["$ref"]]
                    else:
                        ref_key = _extract_key(ref=one_of["$ref"])
                        ref_keys.append(ref_key)

    return property, ref_keys


def normalize_property_schema(property: dict) -> dict:
    normalized: dict = {}
    for key in ("type", "description", "default", "enum", "const", "anyOf", "oneOf", "pattern"):
        if key in property:
            normalized[key] = property[key]
    return normalized


def schemas_are_identical(properties: dict[str, dict]) -> bool:
    if len(properties) < 2:
        return True

    signatures = [normalize_property_schema(property) for property in properties.values()]
    return all(signature == signatures[0] for signature in signatures)


def parse_discriminated_union(property: dict, defs: dict, enum_schemas: dict, scope: set[str]) -> Table:
    mapping = property["discriminator"]["mapping"]
    variant_properties: dict[str, dict] = {}
    for variant_key, ref in mapping.items():
        def_name = ref.split("/")[-1]
        variant_properties[variant_key] = defs[def_name].get("properties", {})

    all_attributes = set()
    for properties in variant_properties.values():
        all_attributes.update(properties.keys())

    common_rows: list[Row] = []
    variant_rows: dict[str, list[Row]] = {variant_key: [] for variant_key in mapping}

    for attribute in sorted(all_attributes):
        per_variant: dict[str, tuple[dict, list[str]]] = {}
        for variant_key, properties in variant_properties.items():
            if attribute not in properties or properties[attribute].get("deprecated"):
                continue

            variant_property, ref_keys = replace_enum_ref_by_enum_schema_and_extract_ref_keys(
                property=properties[attribute].copy(),
                enum_schemas=enum_schemas,
            )
            per_variant[variant_key] = (variant_property, ref_keys)

        if not per_variant:
            continue

        if len(per_variant) == len(variant_properties) and schemas_are_identical(
            {variant_key: prop for variant_key, (prop, _) in per_variant.items()}
        ):
            first_property, first_ref_keys = next(iter(per_variant.values()))
            common_rows.append(build_row(attribute=attribute, property=first_property, ref_keys=first_ref_keys, scope=scope))
        else:
            for variant_key in mapping:
                if variant_key in per_variant:
                    variant_property, ref_keys = per_variant[variant_key]
                    variant_rows[variant_key].append(build_row(attribute=attribute, property=variant_property, ref_keys=ref_keys, scope=scope))

    variant_rows = {variant_key: rows for variant_key, rows in variant_rows.items() if rows}
    legacy_anchors = [ref.split("/")[-1].lower() for ref in mapping.values()]

    return Table(
        title=property.get("title", ""),
        description=property.get("description", ""),
        rows=common_rows,
        variant_rows=variant_rows or None,
        legacy_anchors=legacy_anchors,
    )


def build_row(attribute: str, property: dict, ref_keys: list[str], scope: set[str]):
    description = get_description(property=property, ref_keys=ref_keys)
    default = get_default(property=property)
    types = get_types(property=property)
    values = get_values(property=property)
    examples = get_examples(property=property)
    row = Row(
        attribute=attribute,
        types=types,
        description=description,
        default=default,
        values=values,
        examples=examples,
        scope=scope,
    )

    return row


def merge_rows(*rows: Row) -> Row:
    scope = set().union(*(row.scope for row in rows))
    types = list(dict.fromkeys(type_ for row in rows for type_ in row.types))

    unique_descriptions = list(dict.fromkeys(row.description for row in rows if row.description))
    if len(unique_descriptions) == 1:
        description = unique_descriptions[0]
    else:
        description = " ".join(f"**{SCOPE_LABELS[next(iter(row.scope))]}**: {row.description}" for row in rows if row.description)

    defaults_by_scope = {next(iter(row.scope)): row.default for row in rows}
    unique_defaults = set(defaults_by_scope.values())
    if len(unique_defaults) == 1:
        default = next(iter(unique_defaults))
    else:
        default = " / ".join(f"{SCOPE_LABELS[scope_key]}: {value}" for scope_key, value in sorted(defaults_by_scope.items()))

    values = list(dict.fromkeys(value for row in rows for value in row.values))
    examples = next((row.examples for row in rows if row.examples), [])

    return Row(
        attribute=rows[0].attribute,
        types=types,
        description=description,
        default=default,
        values=values,
        examples=examples,
        scope=scope,
    )


def merge_variant_rows(variant_rows_list: list[dict[str, list[Row]]]) -> dict[str, list[Row]] | None:
    variant_keys = set().union(*(variant_rows.keys() for variant_rows in variant_rows_list))
    if not variant_keys:
        return None

    merged_variant_rows: dict[str, list[Row]] = {}
    for variant_key in variant_keys:
        rows_by_attribute: dict[str, list[Row]] = {}
        for variant_rows in variant_rows_list:
            for row in variant_rows.get(variant_key, []):
                rows_by_attribute.setdefault(row.attribute, []).append(row)
        merged_variant_rows[variant_key] = [merge_rows(*rows) for _, rows in sorted(rows_by_attribute.items())]

    return merged_variant_rows or None


def merge_tables(*tables: Table) -> Table:
    title = next((table.title for table in tables if table.title), "")
    unique_descriptions = list(dict.fromkeys(table.description for table in tables if table.description))
    description = unique_descriptions[0] if len(unique_descriptions) == 1 else "\n\n".join(unique_descriptions)

    rows_by_attribute: dict[str, list[Row]] = {}
    for table in tables:
        for row in table.rows:
            rows_by_attribute.setdefault(row.attribute, []).append(row)

    sub_tables_by_title: dict[str, list[Table]] = {}
    for table in tables:
        for sub_table in table.tables:
            sub_tables_by_title.setdefault(sub_table.title, []).append(sub_table)

    variant_rows_list = [table.variant_rows for table in tables if table.variant_rows]
    legacy_anchors = list(dict.fromkeys(anchor for table in tables for anchor in table.legacy_anchors))

    return Table(
        title=title,
        description=description,
        rows=[merge_rows(*rows) for _, rows in sorted(rows_by_attribute.items())],
        tables=[merge_tables(*sub_tables) for sub_tables in sub_tables_by_title.values()],
        variant_rows=merge_variant_rows(variant_rows_list),
        legacy_anchors=legacy_anchors,
    )


def parse_schema(table: Table, properties: dict, defs: dict, enum_schemas: dict, scope: set[str]):
    for attribute, property in properties.items():
        if property.get("deprecated", False):
            continue

        property, ref_keys = replace_enum_ref_by_enum_schema_and_extract_ref_keys(property=property, enum_schemas=enum_schemas)

        if "discriminator" in property and "oneOf" in property:
            section_title = property.get("title", attribute)
            row = build_row(attribute=attribute, property=property, ref_keys=[section_title], scope=scope)
            table.rows.append(row)
            table.tables.append(parse_discriminated_union(property=property, defs=defs, enum_schemas=enum_schemas, scope=scope))
            continue

        row = build_row(attribute=attribute, property=property, ref_keys=ref_keys, scope=scope)
        table.rows.append(row)

        for ref_key in ref_keys:
            if "properties" in defs[ref_key]:
                sub_table = Table(title=defs[ref_key].get("title", ""), description=get_description(defs[ref_key], ref_keys=[]), rows=[], tables=[])
                sub_table = parse_schema(table=sub_table, properties=defs[ref_key]["properties"], defs=defs, enum_schemas=enum_schemas, scope=scope)
                table.tables.append(sub_table)

    return table


def handle_acorn(text: str) -> str:
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")
    return text


def format_examples(examples: list) -> str:
    if len(examples) > 0:
        return str(examples[0])
    return ""


def format_cell_html(text: str) -> str:
    text = handle_acorn(text=html.escape(text))
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def format_default(default: str) -> str:
    default = default if default != "required" else "**required**"
    return default


def format_values(values: list) -> str:
    values = sorted(handle_acorn(text=value) for value in values)
    if len(values) == 0:
        return ""
    options = "".join(f'<option value="{html.escape(value, quote=True)}">{value}</option>' for value in values)
    return f'<select><option value="">---</option>{options}</select>'


def format_types(types: list) -> str:
    badges = [
        f'<Badge text="{html.escape(type_, quote=True)}" variant="{TYPE_BADGE_VARIANT}" size="small" style="white-space: nowrap" />'
        for type_ in types
    ]
    return f'<span class="config-type-badges">{"".join(badges)}</span>'


def format_scope(scope: set[str]) -> str:
    badges = [
        (f'<Badge text="{SCOPE_LABELS[scope_key]}" variant="{SCOPE_BADGE_VARIANTS[scope_key]}" size="small" style="white-space: nowrap" />')
        for scope_key in SCOPE_ORDER
        if scope_key in scope
    ]
    return f'<span class="config-scope-badges">{"".join(badges)}</span>'


def style_scope_column(table_html: str) -> str:
    table_html = re.sub(r"<th>Scope\s*</th>", '<th class="config-scope-cell">Scope</th>', table_html)
    table_html = re.sub(
        r'<td>(<span class="config-scope-badges">)',
        r'<td class="config-scope-cell">\1',
        table_html,
    )
    return table_html


def style_type_column(table_html: str) -> str:
    table_html = re.sub(r"<th>Type\s*</th>", '<th class="config-type-cell">Type</th>', table_html)
    table_html = re.sub(
        r'<td>(<span class="config-type-badges">)',
        r'<td class="config-type-cell">\1',
        table_html,
    )
    return table_html


def style_description_column(table_html: str) -> str:
    return re.sub(r"<th>Description\s*</th>", '<th class="config-description-cell">Description</th>', table_html)


def format_row(row: Row):
    return [
        format_cell_html(row.attribute),
        format_scope(row.scope),
        format_types(row.types),
        format_cell_html(row.description),
        format_cell_html(format_default(row.default)),
        format_values(row.values),
        format_cell_html(format_examples(row.examples)),
    ]


def format_table(rows: list[Row]) -> str:
    table_html = tabulate(
        tabular_data=[format_row(row) for row in rows],
        headers=["Attribute", "Scope", "Type", "Description", "Default", "Values", "Examples"],
        tablefmt="unsafehtml",
    )
    table_html = style_scope_column(table_html)
    table_html = style_type_column(table_html)
    table_html = style_description_column(table_html)
    return f'<div class="config-table-wrapper">\n{table_html}\n</div>'


def format_variant_tabs(variant_rows: dict[str, list[Row]]) -> str:
    tabs = "<Tabs>\n"
    ordered_keys = [key for key in VARIANT_TAB_ORDER if key in variant_rows]
    ordered_keys.extend(key for key in variant_rows if key not in ordered_keys)
    for variant_key in ordered_keys:
        rows = variant_rows[variant_key]
        label = VARIANT_TAB_LABELS.get(variant_key, variant_key.capitalize())
        icon = VARIANT_TAB_ICONS.get(variant_key)
        icon_attr = f' icon="{icon}"' if icon else ""
        tabs += f'  <TabItem value="{variant_key}" label="{label}"{icon_attr}>\n\n'
        tabs += f"{format_table(rows=rows)}\n\n"
        tabs += "  </TabItem>\n"
    tabs += "</Tabs>"
    return tabs


def convert_to_markdown(table: Table, markdown: str = "", level: int = 1):
    breakline_small = "\n\n"
    breakline_large = "\n\n"
    level += 1
    markdown += f"{'#' * level} {table.title}{breakline_small}"

    if table.legacy_anchors:
        anchors = "".join(f'<span id="{anchor}"></span>' for anchor in table.legacy_anchors)
        markdown += f"{anchors}{breakline_small}"

    markdown += f"{table.description}{breakline_large}"

    has_rows = len(table.rows) > 0
    has_variants = bool(table.variant_rows)

    if not has_rows and not has_variants:
        markdown += f"**No settings.**{breakline_large}"
    else:
        if has_rows:
            markdown += f"{format_table(rows=table.rows)}{breakline_large}"

        if has_variants:
            markdown += (
                f"#### Authentication specific fields {breakline_small}{format_variant_tabs(variant_rows=table.variant_rows)}{breakline_large}"
            )

    if table.tables:
        for sub_table in table.tables:
            markdown = convert_to_markdown(table=sub_table, markdown=markdown, level=level)

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
    assert args.output.endswith(".mdx"), f"Output file must end with .mdx ({args.output})"
    assert os.path.exists(os.path.dirname(args.output)), f"Output directory does not exist ({os.path.dirname(args.output)})"

    with open(file=os.path.join("./scripts/docs/configuration_header.md")) as f:
        header = f.read()
        f.close()
    markdown = header + "\n"

    with open(file=os.path.join("config.example.yml")) as f:
        config_example = f.read()
        f.close()

    markdown += get_example_configuration(config_example=config_example)

    def build_config_table(config_file_model, scope: set[str]) -> Table:
        schema = config_file_model.model_json_schema()
        table = Table(title="Configuration", description=schema.get("description", ""), rows=[], tables=[])
        enum_schemas = {f"#/$defs/{attribute}": schema["$defs"][attribute] for attribute in schema["$defs"] if "enum" in schema["$defs"][attribute]}
        return parse_schema(
            table=table,
            properties=schema["properties"],
            defs=schema["$defs"],
            enum_schemas=enum_schemas,
            scope=scope,
        )

    api_table = build_config_table(ApiConfigFile, {SCOPE_API})
    playground_table = build_config_table(PlaygroundConfigFile, {SCOPE_PLAYGROUND})
    table = merge_tables(api_table, playground_table)
    markdown += convert_to_markdown(table=table)

    with open(file=args.output, mode="w") as f:
        f.write(markdown)
        f.close()
