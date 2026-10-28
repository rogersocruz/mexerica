"""Execução das operações.

Regras de segurança:
- Nunca sobrescreve: o destino ganha " (2)", " (3)"... se já existir.
- Escreve primeiro num diretório temporário oculto na mesma pasta e só
  então move para o nome final (sem arquivo pela metade se falhar).
- Se a pasta de origem não for gravável, salva em ~/Downloads.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import formats as F
from .ops import ALL, DIR, EACH, FILE, TEXT, Ctx, Op

log = logging.getLogger("mexerica")


@dataclass
class Result:
    outputs: list[Path] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    ext = F.full_ext(path)
    base = F.stem(path) if ext else path.name
    n = 2
    while True:
        name = f"{base} ({n}).{ext}" if ext else f"{base} ({n})"
        cand = path.with_name(name)
        if not cand.exists():
            return cand
        n += 1


def _hidden_tmp(folder: Path) -> Path:
    work = Path(tempfile.mkdtemp(prefix=".mexerica-", dir=folder))
    if sys.platform == "win32":
        # no Windows o ponto no nome não esconde a pasta
        import ctypes
        ctypes.windll.kernel32.SetFileAttributesW(str(work), 0x2)  # HIDDEN
    return work


def _dest_dir(src: Path) -> tuple[Path, Path]:
    """Pasta de destino e o temporário oculto dentro dela."""
    parent = src.parent
    if os.access(parent, os.W_OK):
        try:
            return parent, _hidden_tmp(parent)
        except OSError:
            pass    # no Windows o os.access não olha as permissões (ACL)
    fallback = Path.home() / "Downloads"
    fallback.mkdir(exist_ok=True)
    return fallback, _hidden_tmp(fallback)


def _run_step(step, ctx: Ctx) -> None:
    if callable(step):
        step(ctx)
        return
    log.info("$ %s", " ".join(map(str, step)))
    proc = subprocess.run(step, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-6:]
        raise RuntimeError("\n".join(tail) or f"código {proc.returncode}")


def _run_one(op: Op, src: Path, srcs: list[Path], res: Result) -> None:
    dest_dir, work = _dest_dir(src)
    try:
        final = unique_path(dest_dir / op.output_name(src))
        tmp_out = work / ("saida" if op.result == DIR else
                          "saida." + (F.full_ext(final) or "bin"))
        ctx = Ctx(src=src, srcs=srcs, work=work, out=tmp_out)
        assert op.build is not None
        for step in op.build(ctx):
            _run_step(step, ctx)
        if op.result == TEXT:
            res.texts.extend(ctx.text)
            return
        if not tmp_out.exists():
            raise RuntimeError("a operação não gerou saída")
        if op.result == DIR and _collapse_single(tmp_out, final, res):
            return
        final = unique_path(final)  # pode ter surgido enquanto convertia
        shutil.move(str(tmp_out), str(final))
        res.outputs.append(final)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _collapse_single(tmp_dir: Path, final: Path, res: Result) -> bool:
    """Se uma operação de pasta gerou um único arquivo (PDF de 1 página ->
    PNG), entrega o arquivo solto em vez de uma pasta com um item."""
    items = list(tmp_dir.iterdir())
    if len(items) != 1 or not items[0].is_file():
        return False
    item = items[0]
    name = F.stem(final).removesuffix(" Pages") + item.suffix
    target = unique_path(final.with_name(name))
    shutil.move(str(item), str(target))
    res.outputs.append(target)
    return True


def run(op: Op, paths: list[Path],
        progress: Callable[[int, int], None] | None = None) -> Result:
    """Executa `op` sobre `paths`. Bloqueante (o app chama numa thread)."""
    paths = [Path(p) for p in paths]
    res = Result()
    if op.mode == ALL:
        try:
            _run_one(op, paths[0], paths, res)
        except Exception as exc:  # noqa: BLE001 - reportado ao usuário
            log.exception("falha em %s", op.id)
            res.errors.append((paths[0], str(exc)))
        return res
    if op.mode != EACH:
        raise ValueError(f"operação {op.id} é tratada pelo app")
    for i, src in enumerate(paths):
        if progress:
            progress(i, len(paths))
        try:
            _run_one(op, src, [src], res)
        except Exception as exc:  # noqa: BLE001
            log.exception("falha em %s (%s)", op.id, src)
            res.errors.append((src, str(exc)))
    if progress:
        progress(len(paths), len(paths))
    return res


__all__ = ["Result", "run", "unique_path", "FILE", "DIR", "TEXT"]
