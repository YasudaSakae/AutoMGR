from __future__ import annotations

import os
import time
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODELS_TO_TRY = [
    "models/gemini-2.5-pro",
    "models/gemini-1.5-pro",
    "models/gemini-2.0-flash",
]

DEFAULT_BATCH_MODELS = [
    "models/gemini-2.5-pro",
    "models/gemini-2.0-flash",
]


def _safe_name(model_name: str) -> str:
    return model_name.split("/")[-1].replace("-", "_").replace(".", "")


def list_models(*, only_gemini: bool = True) -> list[str]:
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️ [Gemini] Não foi possível listar: GOOGLE_API_KEY não encontrada.")
        return []

    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ [Gemini] Dependência ausente: instale com `pip install google-generativeai`.")
        return []

    try:
        genai.configure(api_key=api_key)
        models: list[str] = []
        for model in genai.list_models():
            if "generateContent" not in model.supported_generation_methods:
                continue
            if only_gemini and not model.name.startswith("models/gemini"):
                continue
            models.append(model.name)
        return sorted(set(models))
    except Exception as exc:  # noqa: BLE001
        print(f"❌ [Gemini] Erro ao listar modelos: {exc}")
        return []


def run(
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    models_to_try: list[str] | None = None,
    temperature: float = 0.2,
) -> Path | None:
    print("\n" + "=" * 50)
    print("🔵 [Gemini] Iniciando...")

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️ [Gemini] Pulei: GOOGLE_API_KEY não encontrada.")
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ [Gemini] Dependência ausente: instale com `pip install google-generativeai`.")
        return None

    outdir.mkdir(parents=True, exist_ok=True)
    genai.configure(api_key=api_key)

    candidates = models_to_try or DEFAULT_MODELS_TO_TRY
    for model_name in candidates:
        print(f"   👉 Tentando modelo: {model_name}")
        try:
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ]

            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_prompt,
                safety_settings=safety_settings,
            )

            print("   ⏳ Gerando resposta (streaming)...")
            stream = model.generate_content(
                user_prompt,
                stream=True,
                generation_config=genai.types.GenerationConfig(temperature=temperature),
            )

            text = ""
            print("-" * 30)
            for chunk in stream:
                if getattr(chunk, "text", None):
                    print(chunk.text, end="", flush=True)
                    text += chunk.text
            print("\n" + "-" * 30)

            output_path = outdir / "resultado_gemini.md"
            output_path.write_text(text, encoding="utf-8")
            print(f"\n✅ [Gemini] Sucesso! Salvo em '{output_path}'.")
            return output_path

        except Exception as exc:  # noqa: BLE001 (CLI tool)
            msg = str(exc).lower()
            if "404" in msg or "not found" in msg:
                continue
            print(f"\n❌ [Gemini] Erro ({model_name}): {exc}")
            time.sleep(1)

    print("❌ [Gemini] Nenhum modelo funcionou (verifique sua API key/permissões).")
    return None


def run_batch(
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    models: list[str] | None = None,
    count_per_model: int = 3,
    temperature: float = 0.4,
    sleep_seconds: float = 2.0,
) -> list[Path]:
    print("\n" + "=" * 50)
    print("🔵 [Gemini] Lote de gerações...")

    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("⚠️ [Gemini] Pulei: GOOGLE_API_KEY não encontrada.")
        return []

    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ [Gemini] Dependência ausente: instale com `pip install google-generativeai`.")
        return []

    outdir.mkdir(parents=True, exist_ok=True)
    genai.configure(api_key=api_key)

    selected_models = models or DEFAULT_BATCH_MODELS
    outputs: list[Path] = []

    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    for model_name in selected_models:
        print("\n" + "-" * 50)
        print(f"🚀 [Gemini] Modelo: {model_name} | {count_per_model} variações")

        try:
            model = genai.GenerativeModel(
                model_name,
                system_instruction=system_prompt,
                safety_settings=safety_settings,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [Gemini] Erro ao configurar modelo {model_name}: {exc}")
            continue

        for i in range(1, count_per_model + 1):
            filename = f"resultado_gemini_{_safe_name(model_name)}_{i:02d}.md"
            output_path = outdir / filename
            print(f"📄 Gerando {i}/{count_per_model} → {output_path.name}")

            try:
                stream = model.generate_content(
                    user_prompt,
                    stream=True,
                    generation_config=genai.types.GenerationConfig(temperature=temperature),
                )

                text = ""
                for chunk in stream:
                    if getattr(chunk, "text", None):
                        text += chunk.text

                output_path.write_text(text, encoding="utf-8")
                outputs.append(output_path)

                if i < count_per_model:
                    time.sleep(max(0.0, sleep_seconds))

            except Exception as exc:  # noqa: BLE001
                print(f"❌ [Gemini] Falha na geração {i}/{count_per_model}: {exc}")
                time.sleep(1)

    return outputs
