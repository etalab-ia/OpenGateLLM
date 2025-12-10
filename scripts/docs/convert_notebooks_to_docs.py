import argparse
import os
from pathlib import Path
import re

from nbconvert import MarkdownExporter

parser = argparse.ArgumentParser(description="Convert Jupyter notebooks (.ipynb) to Markdown (GFM) for Docusaurus, with front matter.")
parser.add_argument("--input", type=Path, default=Path("./docs/tutorials"), help="Directory containing Jupyter notebooks.")
parser.add_argument("--output", type=Path, default=Path("./docs/docs/guides"), help="Output directory for Markdown files.")


def convert_indented_blocks_to_quote_code(text):
    # Step 1: protect already existing code blocks
    code_blocks = []

    def protect_code_block(match):
        code_blocks.append(match.group(0))
        return f"@@CODEBLOCK{len(code_blocks) - 1}@@"

    text = re.sub(r"```[\s\S]*?```", protect_code_block, text)

    # Step 2: transform 4-space indented blocks
    def replace_indented_block(match):
        block = match.group(0)
        # remove 4 leading spaces at the start of each line
        unindented = re.sub(r"^ {4}", "", block, flags=re.MULTILINE)
        # convert to markdown quote + code block
        return "> ```\n" + "\n".join(["> " + line for line in unindented.strip().splitlines()]) + "\n> ```"

    text = re.sub(r"(?:^ {4}.*(?:\n|$))+", replace_indented_block, text, flags=re.MULTILINE)

    # Step 3: restore protected code blocks
    for i, code in enumerate(code_blocks):
        text = text.replace(f"@@CODEBLOCK{i}@@", code)

    return text


def convert_option_blocks_to_tabs(text: str) -> str:
    """
    Convert successive quote blocks like:

        > Option 1 - with Mistral client
        ...content...
        > Option 2 - with requests
        ...content...

    into Docusaurus Tabs/TabItem blocks, similar to the pattern used in
    `docs/docs/dependencies/vector_store.md`.
    """

    option_re = re.compile(r"^> Option (\d+) - (.+)$")
    heading_re = re.compile(r"^#{1,6}\s+")

    lines = text.split("\n")
    result_lines: list[str] = []
    i = 0
    used_tabs = False

    while i < len(lines):
        match = option_re.match(lines[i])
        if not match:
            result_lines.append(lines[i])
            i += 1
            continue

        # We are at the first option of a group of options.
        options: list[dict[str, object]] = []

        while i < len(lines):
            m = option_re.match(lines[i])
            if not m:
                break

            option_number = m.group(1)
            raw_label = m.group(2).strip()

            # Make the tab label a bit cleaner: drop leading "with "
            label = re.sub(r"^with\s+", "", raw_label, flags=re.IGNORECASE)
            # Fallback if stripping makes it empty
            if not label:
                label = f"Option {option_number}"

            # Slug for the value attribute
            value = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or f"option-{option_number}"

            content_start = i + 1
            content_end = content_start
            while content_end < len(lines):
                line = lines[content_end]
                # Stop this option's content when we reach another option or a new heading
                if option_re.match(line) or heading_re.match(line):
                    break
                content_end += 1

            options.append({
                "value": value,
                "label": label,
                "content_lines": lines[content_start:content_end],
            })

            i = content_end

            # If next line is not another option, we end the group
            if i >= len(lines) or not option_re.match(lines[i]):
                break

        if not options:
            # Should not happen, but just in case
            continue

        used_tabs = True

        # Emit Tabs / TabItem structure
        result_lines.append("<Tabs>")
        for idx, opt in enumerate(options):
            value = opt["value"]
            label = opt["label"]
            default_attr = " default" if idx == 0 else ""
            result_lines.append(f'  <TabItem value="{value}" label="{label}"{default_attr}>')
            # Add the original content for this option
            content_lines = opt["content_lines"]
            if content_lines:
                result_lines.extend(content_lines)
            result_lines.append("  </TabItem>")
        result_lines.append("</Tabs>")

        # Do not increment i here; loop continues from current i (which is
        # already at the first non-option/heading line for this group).

    new_text = "\n".join(result_lines)

    if used_tabs:
        tabs_import = "import Tabs from '@theme/Tabs';"
        tabitem_import = "import TabItem from '@theme/TabItem';"
        if tabs_import not in new_text:
            new_text = f"{tabs_import}\n{tabitem_import}\n\n" + new_text

    return new_text


def escape_braces_outside_code(text):
    # Step 1: protect existing code blocks
    code_blocks = []

    def protect_code_block(match):
        code_blocks.append(match.group(0))
        return f"@@CODEBLOCK{len(code_blocks) - 1}@@"

    text = re.sub(r"```[\s\S]*?```", protect_code_block, text)

    # Step 2: escape { and } outside code blocks
    text = re.sub(r"(?<!\\){", r"\\{", text)
    text = re.sub(r"(?<!\\)}", r"\\}", text)

    # Step 3: restore protected code blocks
    for i, code in enumerate(code_blocks):
        text = text.replace(f"@@CODEBLOCK{i}@@", code)

    return text


def convert_special_quotes_to_admonitions(text):
    """
    Convert Markdown quote blocks starting with > **Tip|Warning|Message|Info**
    into admonition blocks like ::: tip|warning|message|info ... :::.
    """

    pattern = re.compile(r"(^> \*\*(Tip|Warning|Message|Info)\*\*.*(?:\n>.*)*)", flags=re.IGNORECASE | re.MULTILINE)

    def replace_block(match):
        block = match.group(1)
        label = match.group(2).lower()

        # Remove the "> " prefixes and empty lines starting with ">"
        lines = [re.sub(r"^>\s?", "", line) for line in block.splitlines()]
        # Remove unnecessary blank lines
        content = "\n".join(line for line in lines[1:] if line.strip())

        return f":::{label}\n{content.strip()}\n:::"

    return pattern.sub(replace_block, text)


def insert_colab_badge_after_title(text: str, notebook_path: Path) -> str:
    """
    Insert a Colab badge just after the first title Markdown (# ...).
    """
    badge_html = (
        f'<p align="right">\n'
        f"[![](https://colab.research.google.com/assets/colab-badge.svg)]"
        f"(https://colab.research.google.com/github/etalab-ia/opengatellm/blob/main/docs/tutorials/{notebook_path.stem}.ipynb)\n"
        f"</p>\n\n"
    )

    # Find the first line of title Markdown
    return re.sub(r"(^# .*$\n?)", r"\1" + badge_html, text, count=1, flags=re.MULTILINE)


if __name__ == "__main__":
    args = parser.parse_args()
    assert os.path.exists(args.input), f"Input directory does not exist ({args.input})"
    assert os.path.exists(args.output), f"Output directory does not exist ({args.output})"
    args.output.mkdir(parents=True, exist_ok=True)

    exporter = MarkdownExporter()

    for notebook in args.input.glob("*.ipynb"):
        body, resources = exporter.from_filename(notebook)
        md_path = Path(args.output, notebook.stem + ".md")
        body = insert_colab_badge_after_title(text=body, notebook_path=notebook)
        body = convert_special_quotes_to_admonitions(text=body)
        body = convert_option_blocks_to_tabs(text=body)
        body = convert_indented_blocks_to_quote_code(text=body)
        body = escape_braces_outside_code(text=body)
        md_path.write_text(body, encoding="utf-8")
