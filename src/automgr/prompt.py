from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SEPARATOR = "___SEPARADOR___"

DEFAULT_IGNORE_KEYS = {
    "id",
    "fk_processo",
    "active",
    "order",
    "code",
    "created_at",
    "updated_at",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def clean_json(value: Any, ignore_keys: set[str] = DEFAULT_IGNORE_KEYS) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, inner in value.items():
            if key in ignore_keys:
                continue
            if inner is None or inner == "null":
                continue
            cleaned_inner = clean_json(inner, ignore_keys=ignore_keys)
            if cleaned_inner in ({}, [], "", None):
                continue
            cleaned[key] = cleaned_inner
        return cleaned

    if isinstance(value, list):
        cleaned_list = [clean_json(item, ignore_keys=ignore_keys) for item in value]
        return [item for item in cleaned_list if item not in ({}, [], "", None)]

    return value


def json_to_string(value: Any, *, indent: int | None = 2) -> str:
    cleaned = clean_json(value)
    if isinstance(cleaned, (dict, list)):
        return json.dumps(cleaned, indent=indent, ensure_ascii=False)
    return str(cleaned)


def split_template(template_text: str, *, separator: str = DEFAULT_SEPARATOR) -> tuple[str, str]:
    if separator in template_text:
        system_txt, user_txt = template_text.split(separator, 1)
    else:
        system_txt, user_txt = "", template_text
    return system_txt.strip(), user_txt.strip()


def build_prompts(
    dados: dict[str, Any],
    template_text: str,
    *,
    separator: str = DEFAULT_SEPARATOR,
    json_indent: int | None = 2,
) -> tuple[str, str]:
    system_txt, user_txt = split_template(template_text, separator=separator)

    for key, value in dados.get("metadados", {}).items():
        user_txt = user_txt.replace(f"{{{{{key}}}}}", str(value))

    etp_str = json_to_string(dados.get("etp_conteudo", ""), indent=json_indent)
    tr_str = json_to_string(dados.get("tr_conteudo", ""), indent=json_indent)

    user_txt = user_txt.replace("{{ETP_CONTEUDO}}", etp_str)
    user_txt = user_txt.replace("{{TR_CONTEUDO}}", tr_str)

    return system_txt, user_txt

