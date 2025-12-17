from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
]


def list_models(*, only_chat: bool = True) -> list[str]:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ [OpenAI] Não foi possível listar: OPENAI_API_KEY não encontrada.")
        return []

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ [OpenAI] Dependência ausente: instale com `pip install openai`.")
        return []

    try:
        client = OpenAI(api_key=api_key)
        response = client.models.list()
        data = getattr(response, "data", response)
        ids: list[str] = []
        for item in data:
            model_id = getattr(item, "id", None)
            if not model_id:
                continue

            if only_chat:
                starts_like_chat = model_id.startswith(("gpt-", "o"))
                is_non_chat = any(
                    token in model_id
                    for token in (
                        "embedding",
                        "moderation",
                        "whisper",
                        "tts",
                        "dall-e",
                        "image",
                        "audio",
                        "transcribe",
                    )
                )
                if not starts_like_chat or is_non_chat:
                    continue

            ids.append(model_id)

        models = sorted(set(ids))
        return models
    except Exception as exc:  # noqa: BLE001
        print(f"❌ [OpenAI] Erro ao listar modelos (usando lista padrão): {exc}")
        return DEFAULT_MODELS


def run(
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    model: str = "gpt-4o",
    temperature: float = 0.2,
    frequency_penalty: float = 0.3,
    attempts: int = 3,
) -> Path | None:
    print("\n" + "=" * 50)
    print("🟢 [OpenAI] Iniciando...")

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️ [OpenAI] Pulei: OPENAI_API_KEY não encontrada.")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ [OpenAI] Dependência ausente: instale com `pip install openai`.")
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=api_key)

    for attempt in range(1, attempts + 1):
        try:
            stream = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=temperature,
                frequency_penalty=frequency_penalty,
                stream=True,
            )

            text = ""
            print("   ⏳ Gerando resposta (streaming)...")
            print("-" * 30)
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    print(delta, end="", flush=True)
                    text += delta
            print("\n" + "-" * 30)

            output_path = outdir / "resultado_openai.md"
            output_path.write_text(text, encoding="utf-8")
            print(f"\n✅ [OpenAI] Sucesso! Salvo em '{output_path}'.")
            return output_path

        except Exception as exc:  # noqa: BLE001 (CLI tool)
            print(f"\n⚠️ [OpenAI] Erro (tentativa {attempt}/{attempts}): {exc}")
            time.sleep(2)

    return None
