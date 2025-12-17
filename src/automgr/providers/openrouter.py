from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "1": {
        "nome": "DeepSeek V3 (Recomendado)",
        "slug": "deepseek/deepseek-chat",
        "desc": "Custo-benefício excelente.",
    },
    "2": {
        "nome": "Qwen 2.5 72B Instruct",
        "slug": "qwen/qwen-2.5-72b-instruct",
        "desc": "Ótimo para instruções técnicas e JSON.",
    },
    "3": {
        "nome": "Llama 3.3 70B (Meta)",
        "slug": "meta-llama/llama-3.3-70b-instruct",
        "desc": "Estável e confiável.",
    },
    "4": {
        "nome": "DeepSeek R1 (Raciocínio)",
        "slug": "deepseek/deepseek-r1",
        "desc": "Bom para auditoria lógica e consistência.",
    },
    "5": {
        "nome": "Mistral Small 3 (24B)",
        "slug": "mistralai/mistral-small-24b-instruct-2501",
        "desc": "Barato e bem competente para lógica.",
    },
}


def _safe_name(model_slug: str) -> str:
    return model_slug.split("/")[-1].replace("-", "_").replace(".", "")


def run_one(
    model_slug: str,
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: int = 120,
) -> Path | None:
    print(f"\n🚀 [OpenRouter] Iniciando: {model_slug}")

    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ [OpenRouter] Erro: configure OPENROUTER_API_KEY no .env.")
        return None

    try:
        from openai import OpenAI
    except ImportError:
        print("❌ [OpenRouter] Dependência ausente: instale com `pip install openai`.")
        return None

    outdir.mkdir(parents=True, exist_ok=True)

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    text = ""
    print("   ⏳ Gerando resposta (streaming)...")
    print("-" * 40)

    stream = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "https://automgr.local",
            "X-Title": "AutoMGR Script",
        },
        model=model_slug,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta is not None:
            print(delta, end="", flush=True)
            text += delta

    print("\n" + "-" * 40)

    filename = f"resultado_openrouter_{_safe_name(model_slug)}.md"
    output_path = outdir / filename
    output_path.write_text(text, encoding="utf-8")
    print(f"\n✅ [OpenRouter] Sucesso! Salvo em '{output_path}'.")
    return output_path


def run_menu(
    system_prompt: str,
    user_prompt: str,
    *,
    outdir: Path,
    models: dict[str, dict[str, str]] = DEFAULT_MODELS,
    temperature: float = 0.2,
    max_tokens: int = 4000,
    timeout: int = 120,
) -> list[Path]:
    print("\n=== MENU (OPENROUTER) ===")
    for key, info in models.items():
        print(f"{key}) {info['nome']} — {info['desc']}")

    choice = input("\nDigite o número (ou 'todas'): ").strip().lower()
    outputs: list[Path] = []

    if choice == "todas":
        for key, info in models.items():
            path = run_one(
                info["slug"],
                system_prompt,
                user_prompt,
                outdir=outdir,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            if path:
                outputs.append(path)
        return outputs

    if choice in models:
        info = models[choice]
        path = run_one(
            info["slug"],
            system_prompt,
            user_prompt,
            outdir=outdir,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return [path] if path else []

    if "/" in choice:
        path = run_one(
            choice,
            system_prompt,
            user_prompt,
            outdir=outdir,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        return [path] if path else []

    print("Opção inválida.")
    return []

