import argparse
import base64
import json
import os
from pathlib import Path

parser = argparse.ArgumentParser(description="Convert Jupyter notebooks (.ipynb) to Markdown (GFM) for Docusaurus, with front matter.")
parser.add_argument("--input", type=Path, default=Path("./docs/tutorials"), help="Directory containing Jupyter notebooks.")


def convert_markdown_cell(cell: dict) -> str:
    tags = cell.get("metadata", {}).get("tags", [])
    content = "".join(cell["source"])

    if "warning" in tags:
        content = f"\n\n:::warning\n{content}\n:::"
    elif "danger" in tags:
        content = f"\n\n:::danger\n{content}\n:::"
    elif "tip" in tags:
        content = f"\n\n:::tip\n{content}\n:::"
    elif "note" in tags:
        content = f"\n\n:::note\n{content}\n:::"

    content += "\n\n"

    return content


def convert_code_cell(cell: dict, image_name: str) -> str:
    image_path = Path("./docs/static/img/guides")
    image_relative_path = Path("../../static/img/guides")
    content = "\n```python\n"
    content += "".join(cell["source"])
    content += "\n```\n\n"

    if cell["outputs"]:
        content += "\n> ```python\n"
        content += "> " + "> ".join(cell["outputs"][0]["text"])
        content += "> ```\n"

        if len(cell["outputs"]) > 1:
            data = cell["outputs"][1].get("data", {})
            if "image/jpeg" in data:
                image_path = image_path / f"{image_name}.jpg"
                image_bytes = base64.b64decode(data["image/jpeg"])
                with open(image_path, "wb") as f:
                    f.write(image_bytes)

                content += f"> ![]({image_relative_path / f"{image_name}.jpg"})\n\n"

        content += "\n\n"

    return content


def convert_notebook(file_path: Path) -> str:
    file = json.loads(file_path.read_text(encoding="utf-8"))
    filename = file_path.stem
    tab_import = False
    tab_section = False

    markdown = ""
    for i, cell in enumerate(file["cells"]):
        badge = f"""
<p align="right">
[![](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/{filename}.ipynb)
</p>
"""

        if i == 0:
            cell["source"] = cell["source"][:1] + [badge] + cell["source"][1:]

        tags = cell.get("metadata", {}).get("tags", [])
        if "tab-heading" in tags or "tab-content" in tags:
            tab_import = True

            if "tab-heading" in tags:
                if not tab_section:  # start a new tab section
                    markdown += "<Tabs>\n"
                    tab_section = True
                else:
                    markdown += "</TabItem>\n"

                assert cell["cell_type"] == "markdown", "Tab must be started with a markdown cell"
                content = convert_markdown_cell(cell).replace("#", "").strip()
                markdown += f'<TabItem value="{content.lower().replace(" ", "-")}" label="{content}">\n\n'
            else:
                if cell["cell_type"] == "code":
                    content = convert_code_cell(cell, image_name=f"{filename}_{i}")
                    markdown += content
                elif cell["cell_type"] == "markdown":
                    content = convert_markdown_cell(cell)
                    markdown += content
                else:
                    raise ValueError(f"Unexpected cell type: {cell["cell_type"]}")

        else:
            if tab_section:
                markdown += "</TabItem>\n"
                markdown += "</Tabs>\n\n"  # end of tab section
                tab_section = False

            if cell["cell_type"] == "code":
                content = convert_code_cell(cell, image_name=f"{filename}_{i}")
                markdown += content
            elif cell["cell_type"] == "markdown":
                content = convert_markdown_cell(cell)
                markdown += content
            else:
                raise ValueError(f"Unexpected cell type: {cell["cell_type"]}")

    if tab_section:
        markdown += "</TabItem>\n"
        markdown += "</Tabs>\n\n"  # end of tab section

    if tab_import:
        markdown = "import Tabs from '@theme/Tabs';\nimport TabItem from '@theme/TabItem';\n\n" + markdown

    return markdown


if __name__ == "__main__":
    args = parser.parse_args()
    assert os.path.exists(args.input), f"Input directory does not exist ({args.input})"

    for notebook_file_path in args.input.glob("*.ipynb"):
        markdown = convert_notebook(file_path=notebook_file_path)
        markdown_path = Path("./docs/docs/guides") / f"{notebook_file_path.stem}.md"
        markdown_path.write_text(data=markdown, encoding="utf-8")
