from __future__ import annotations

from jinja2 import Template


def render_template_text(text: str, variables: dict[str, object]) -> str:
    tmpl = Template(text)
    return tmpl.render(**variables)

