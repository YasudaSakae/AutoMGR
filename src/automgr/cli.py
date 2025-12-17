from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from automgr import prompt as prompt_lib
from automgr.paths import default_dados_path, default_outdir, default_template_path, ensure_dir
from automgr.providers import gemini, groq, openai_provider, openrouter


def _parse_indexes(value: str, *, max_value: int) -> list[int] | None:
    raw = value.replace(" ", "")
    if not raw:
        return None

    indexes: list[int] = []
    for part in raw.split(","):
        if not part:
            return None

        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if not start_str.isdigit() or not end_str.isdigit():
                return None
            start = int(start_str)
            end = int(end_str)
            if start < 1 or end < 1 or start > max_value or end > max_value:
                return None
            step = 1 if end >= start else -1
            for idx in range(start, end + step, step):
                if idx not in indexes:
                    indexes.append(idx)
            continue

        if not part.isdigit():
            return None
        idx = int(part)
        if idx < 1 or idx > max_value:
            return None
        if idx not in indexes:
            indexes.append(idx)

    return indexes


def _select_models_interactively(
    provider_label: str,
    options: list[str],
    *,
    default: list[str] | None,
    allow_multiple: bool,
    allow_custom: bool = True,
    max_display: int = 30,
) -> list[str] | None:
    """
    Retorna:
      - None: manter padrão atual (default)
      - []: pular provider
      - [..]: modelos escolhidos
    """
    options = sorted({opt for opt in options if opt})
    if not options:
        print(f"⚠️ [{provider_label}] Nenhum modelo disponível para seleção.")
        return None

    filtered = options
    while True:
        print("\n" + "=" * 50)
        print(f"🎛️  Seleção de modelo — {provider_label}")
        if default:
            shown_default = ", ".join(default) if allow_multiple else default[0]
            print(f"Padrão atual: {shown_default}")

        print("Dicas: ENTER=manter padrão | s=pular | *=reset filtro | digite texto para filtrar")

        shown = filtered[:max_display]
        for i, model in enumerate(shown, start=1):
            print(f"{i:>2}) {model}")

        if len(filtered) > max_display:
            print(f"... mostrando {max_display} de {len(filtered)} (use filtro para reduzir)")

        prompt = "Escolha"
        if allow_multiple:
            prompt += " (n, n,n ou n-n)"
        prompt += ": "
        choice = input(prompt).strip()

        if choice == "":
            return None

        lower = choice.lower()
        if lower in {"s", "skip", "pular"}:
            return []
        if lower == "*":
            filtered = options
            continue

        indexes = _parse_indexes(choice, max_value=len(filtered))
        if indexes:
            selected = [filtered[i - 1] for i in indexes]
            if allow_multiple:
                return selected
            return [selected[0]]

        exact = next((m for m in options if m == choice), None)
        if exact:
            return [exact]

        matches = [m for m in options if lower in m.lower()]
        if matches:
            filtered = matches
            continue

        if allow_custom:
            confirm = input(f"Modelo '{choice}' não está na lista. Usar mesmo assim? [s/N]: ").strip().lower()
            if confirm in {"s", "sim", "y", "yes"}:
                return [choice]

        print("Opção inválida. Tente novamente.")


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

    providers = list(args.provider or ["gemini", "groq", "openai"])

    if args.select_models:
        if "gemini" in providers:
            available = gemini.list_models()
            selected = _select_models_interactively(
                "Gemini",
                available,
                default=args.gemini_model or gemini.DEFAULT_MODELS_TO_TRY,
                allow_multiple=True,
            )
            if selected == []:
                providers.remove("gemini")
            elif selected is not None:
                args.gemini_model = selected

        if "groq" in providers:
            available = groq.list_models()
            selected = _select_models_interactively(
                "Groq",
                available,
                default=[args.groq_model],
                allow_multiple=False,
            )
            if selected == []:
                providers.remove("groq")
            elif selected is not None:
                args.groq_model = selected[0]

        if "openai" in providers:
            available = openai_provider.list_models()
            selected = _select_models_interactively(
                "OpenAI",
                available,
                default=[args.openai_model],
                allow_multiple=False,
            )
            if selected == []:
                providers.remove("openai")
            elif selected is not None:
                args.openai_model = selected[0]

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

    if args.select_model:
        available = openrouter.list_models()
        selected = _select_models_interactively(
            "OpenRouter",
            available,
            default=getattr(openrouter, "DEFAULT_MODELS_FLAT", None),
            allow_multiple=False,
        )
        if selected == []:
            return 0
        if selected is not None:
            openrouter.run_one(
                selected[0],
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
    print("🔍 Listando modelos do Gemini (generateContent)...")
    print("-" * 40)
    models = gemini.list_models(only_gemini=False)
    if not models:
        print("⚠️ Nenhum modelo encontrado (verifique a API key).")
        return 2

    for model in models:
        print(f"✅ {model}")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    selected_providers = args.provider or ["gemini", "groq", "openai", "openrouter"]
    text_filter = (args.filter or "").strip().lower()

    def apply_filter(items: list[str]) -> list[str]:
        if not text_filter:
            return items
        return [item for item in items if text_filter in item.lower()]

    for provider in selected_providers:
        print("\n" + "=" * 60)
        print(f"📦 Provider: {provider}")
        print("-" * 60)

        if provider == "gemini":
            models = apply_filter(gemini.list_models(only_gemini=args.only_gemini))
        elif provider == "groq":
            models = apply_filter(groq.list_models())
        elif provider == "openai":
            models = apply_filter(openai_provider.list_models(only_chat=not args.all_openai_models))
        elif provider == "openrouter":
            models = apply_filter(openrouter.list_models())
        else:
            print("⚠️ Provider inválido.")
            continue

        if not models:
            print("⚠️ Nenhum modelo encontrado.")
            continue

        limit = args.limit if args.limit and args.limit > 0 else None
        shown = models[:limit] if limit else models

        for model in shown:
            print(f"✅ {model}")

        if limit and len(models) > limit:
            print(f"... (+{len(models) - limit} modelos; aumente com --limit)")

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
        "--select-models",
        action="store_true",
        help="Mostra um menu para escolher modelos (interativo)",
    )
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
    or_p.add_argument(
        "--select-model",
        action="store_true",
        help="Lista modelos do OpenRouter e permite escolher (pode ser bem grande)",
    )
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

    models_p = sub.add_parser("models", help="Lista modelos disponíveis por provider")
    models_p.add_argument(
        "--provider",
        action="append",
        choices=["gemini", "groq", "openai", "openrouter"],
        help="Filtra por provider (repita a flag). Default: todos",
    )
    models_p.add_argument("--filter", help="Filtro por substring (ex: 'gemini-2.5', 'llama', 'deepseek')")
    models_p.add_argument("--limit", type=int, default=50, help="Quantos itens mostrar (default: 50; 0=sem limite)")
    models_p.add_argument(
        "--only-gemini",
        action="store_true",
        help="(Gemini) mostra apenas modelos 'models/gemini*'",
    )
    models_p.add_argument(
        "--all-openai-models",
        action="store_true",
        help="(OpenAI) inclui modelos além dos de chat (pode ficar bem grande)",
    )
    models_p.set_defaults(func=cmd_models)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
