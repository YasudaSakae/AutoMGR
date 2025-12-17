from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automgr import prompt as prompt_lib
from automgr.paths import default_dados_path, default_outdir, default_template_path, ensure_dir
from automgr.providers import gemini, groq, openai_provider, openrouter


def _write_debug_prompt(outdir: Path, system_prompt: str, user_prompt: str) -> Path:
    ensure_dir(outdir)
    debug_path = outdir / "prompt_montado_debug.txt"
    debug_path.write_text(
        f"=== SYSTEM ===\n{system_prompt}\n\n=== USER ===\n{user_prompt}\n",
        encoding="utf-8",
    )
    return debug_path


def _load_and_build_prompts(args: argparse.Namespace) -> tuple[str, str]:
    dados_path = Path(args.dados) if args.dados else default_dados_path(Path.cwd())
    template_path = Path(args.template) if args.template else default_template_path(Path.cwd())

    dados = prompt_lib.load_json(dados_path)
    template_text = prompt_lib.load_text(template_path)

    json_indent = None if args.json_indent <= 0 else args.json_indent
    system_prompt, user_prompt = prompt_lib.build_prompts(
        dados,
        template_text,
        json_indent=json_indent,
    )
    return system_prompt, user_prompt


def cmd_run(args: argparse.Namespace) -> int:
    load_dotenv()

    outdir = Path(args.outdir) if args.outdir else default_outdir(Path.cwd())
    system_prompt, user_prompt = _load_and_build_prompts(args)

    debug_path = _write_debug_prompt(outdir, system_prompt, user_prompt)
    print(f"📝 Prompt montado. Debug em: {debug_path}")

    providers = args.provider or ["gemini", "groq", "openai"]

    if "gemini" in providers:
        gemini.run(
            system_prompt,
            user_prompt,
            outdir=outdir,
            models_to_try=args.gemini_model or None,
            temperature=args.temperature,
        )

    if "groq" in providers:
        groq.run(
            system_prompt,
            user_prompt,
            outdir=outdir,
            model=args.groq_model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            attempts=args.attempts,
        )

    if "openai" in providers:
        openai_provider.run(
            system_prompt,
            user_prompt,
            outdir=outdir,
            model=args.openai_model,
            temperature=args.temperature,
            attempts=args.attempts,
        )

    print("\n🏁 Fim das execuções.")
    return 0


def cmd_openrouter(args: argparse.Namespace) -> int:
    load_dotenv()

    outdir = Path(args.outdir) if args.outdir else default_outdir(Path.cwd())
    system_prompt, user_prompt = _load_and_build_prompts(args)

    debug_path = _write_debug_prompt(outdir, system_prompt, user_prompt)
    print(f"📝 Prompt montado. Debug em: {debug_path}")

    if args.model:
        openrouter.run_one(
            args.model,
            system_prompt,
            user_prompt,
            outdir=outdir,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            timeout=args.timeout,
        )
        return 0

    openrouter.run_menu(
        system_prompt,
        user_prompt,
        outdir=outdir,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
    )
    return 0


def cmd_gemini_batch(args: argparse.Namespace) -> int:
    load_dotenv()

    outdir = Path(args.outdir) if args.outdir else default_outdir(Path.cwd())
    system_prompt, user_prompt = _load_and_build_prompts(args)

    debug_path = _write_debug_prompt(outdir, system_prompt, user_prompt)
    print(f"📝 Prompt montado. Debug em: {debug_path}")

    gemini.run_batch(
        system_prompt,
        user_prompt,
        outdir=outdir,
        models=args.model or None,
        count_per_model=args.count,
        temperature=args.temperature,
        sleep_seconds=args.sleep,
    )
    return 0


def cmd_list_gemini_models(_: argparse.Namespace) -> int:
    load_dotenv()
    try:
        import os
        import google.generativeai as genai
    except ImportError:
        print("❌ Dependência ausente: instale com `pip install google-generativeai`.")
        return 2

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ GOOGLE_API_KEY não encontrada no ambiente/.env.")
        return 2

    genai.configure(api_key=api_key)

    print("🔍 Listando modelos do Gemini (generateContent)...")
    print("-" * 40)
    found = False
    for model in genai.list_models():
        if "generateContent" not in model.supported_generation_methods:
            continue
        print(f"✅ {model.name}")
        found = True

    if not found:
        print("⚠️ Nenhum modelo encontrado.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="automgr", description="AutoMGR - geração de MGR via IA")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_io_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument("--dados", help="Caminho do JSON de entrada (default: inputs/dados.json)")
        p.add_argument("--template", help="Caminho do template (default: inputs/prompt_template.txt)")
        p.add_argument("--outdir", help="Diretório de saída (default: outputs/)")
        p.add_argument(
            "--json-indent",
            type=int,
            default=2,
            help="Indentação do JSON no prompt (default: 2; use 0 para compacto/1 linha)",
        )

    run_p = sub.add_parser("run", help="Executa Gemini/Groq/OpenAI em sequência")
    add_common_io_flags(run_p)
    run_p.add_argument(
        "--provider",
        action="append",
        choices=["gemini", "groq", "openai"],
        help="Executa somente o(s) provider(s) escolhido(s) (repita a flag)",
    )
    run_p.add_argument("--temperature", type=float, default=0.2)
    run_p.add_argument("--max-tokens", type=int, default=4000)
    run_p.add_argument("--attempts", type=int, default=3)
    run_p.add_argument(
        "--gemini-model",
        action="append",
        help="Nome do modelo do Gemini para tentar (repita para múltiplos; default: lista recomendada)",
    )
    run_p.add_argument("--groq-model", default="llama-3.3-70b-versatile")
    run_p.add_argument("--openai-model", default="gpt-4o")
    run_p.set_defaults(func=cmd_run)

    or_p = sub.add_parser("openrouter", help="Executa via OpenRouter (menu ou --model)")
    add_common_io_flags(or_p)
    or_p.add_argument("--model", help="Slug do modelo (ex: deepseek/deepseek-chat). Se omitido, abre menu.")
    or_p.add_argument("--temperature", type=float, default=0.2)
    or_p.add_argument("--max-tokens", type=int, default=4000)
    or_p.add_argument("--timeout", type=int, default=120)
    or_p.set_defaults(func=cmd_openrouter)

    gb_p = sub.add_parser("gemini-batch", help="Gera várias versões usando Gemini (lote)")
    add_common_io_flags(gb_p)
    gb_p.add_argument(
        "--model",
        action="append",
        help="Nome do modelo do Gemini (repita para múltiplos; default: 2.5-pro e 2.0-flash)",
    )
    gb_p.add_argument("--count", type=int, default=3, help="Quantidade por modelo (default: 3)")
    gb_p.add_argument("--temperature", type=float, default=0.4, help="Temperatura (default: 0.4)")
    gb_p.add_argument("--sleep", type=float, default=2.0, help="Pausa entre gerações (segundos)")
    gb_p.set_defaults(func=cmd_gemini_batch)

    gm_p = sub.add_parser("list-gemini-models", help="Lista modelos do Gemini disponíveis na sua conta")
    gm_p.set_defaults(func=cmd_list_gemini_models)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
