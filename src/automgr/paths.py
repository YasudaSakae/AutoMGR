from __future__ import annotations

from pathlib import Path


def find_file(candidates: list[Path]) -> Path:
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Nenhum arquivo encontrado: " + ", ".join(str(p) for p in candidates))


def default_dados_path(project_root: Path) -> Path:
    return find_file(
        [
            project_root / "inputs" / "dados.json",
            project_root / "dados.json",
        ]
    )


def default_template_path(project_root: Path) -> Path:
    return find_file(
        [
            project_root / "inputs" / "prompt_template.txt",
            project_root / "prompt_template.txt",
        ]
    )


def default_outdir(project_root: Path) -> Path:
    return project_root / "outputs"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

