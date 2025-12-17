from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
]


def list_models() -> list[str]:
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ [Groq] Não foi possível listar: GROQ_API_KEY não encontrada.")
        return []

    try:
        from groq import Groq
    except ImportError:
        print("❌ [Groq] Dependência ausente: instale com `pip install groq`.")
        return []

    try:
        client = Groq(api_key=api_key)
        response = client.models.list()
        models = [m.id for m in response.data if getattr(m, "id", None)]
        models = sorted(set(models))
        return models
    except Exception as exc:  # noqa: BLE001
        print(f"❌ [Groq] Erro ao listar modelos (usando lista padrão): {exc}")
        return DEFAULT_MODELS


def run(
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    model: str = "llama-3.3-70b-versatile",
    temperature: float = 0.2,
    max_tokens: int = 4000,
    attempts: int = 3,
) -> Path | None:
    print("\n" + "=" * 50)
    print("🟠 [Groq] Iniciando...")

    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("⚠️ [Groq] Pulei: GROQ_API_KEY não encontrada.")
        return None

    try:
        from groq import Groq
    except ImportError:
        print("❌ [Groq] Dependência ausente: instale com `pip install groq`.")
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    client = Groq(api_key=api_key)

    for attempt in range(1, attempts + 1):
        try:
            stream = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
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

            output_path = outdir / "resultado_groq.md"
            output_path.write_text(text, encoding="utf-8")
            print(f"\n✅ [Groq] Sucesso! Salvo em '{output_path}'.")
            return output_path

        except Exception as exc:  # noqa: BLE001 (CLI tool)
            print(f"\n⚠️ [Groq] Erro (tentativa {attempt}/{attempts}): {exc}")
            time.sleep(2)

    return None
