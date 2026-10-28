"""Gera docs/wiki/Operacoes.md a partir de mexerica/engine/ops.py.

Rode depois de mudar as operações:  python docs/gerar_operacoes.py
(precisa do GTK, como o serviço: no Windows, o Python do MSYS2)
"""
import sys
from pathlib import Path

repo = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo))

from mexerica import theme as TH  # noqa: E402
from mexerica.engine.ops import (ACTION, ALL, ALL_OPS, DIR, EDITOR, TEXT,  # noqa: E402
                                 ACTIONS, CONVERT, TOOLS)
from mexerica.settings_window import section_of  # noqa: E402

GROUPS = [(CONVERT, "Converter (Shift)",
           "Formatos de saída. A conversão pura só troca a extensão do nome."),
          (TOOLS, "Ferramentas (Shift + Alt)",
           "Processam mantendo o tipo. As que têm … abrem uma janela "
           "(veja [Janelas de edição](Janelas-de-edicao.md))."),
          (ACTIONS, "Ações (Shift + Ctrl)",
           "Ações de arquivo, sem conversão.")]


def what(op) -> str:
    label = op.label.rstrip("…")
    text = f"Converte para {label}" if op.group == CONVERT and \
        label.isupper() else label
    return f"{text} — {op.hint}" if op.hint else text


def details(op) -> str:
    notes = []
    if op.mode == EDITOR:
        notes.append("abre janela")
    if op.mode == ALL:
        notes.append("vários arquivos → um resultado"
                     + (f" (mín. {op.min_files})" if op.min_files > 1 else ""))
    if op.result == DIR:
        notes.append("gera uma pasta")
    if op.result == TEXT:
        notes.append("mostra/copia texto")
    if op.suffix:
        notes.append(f"sufixo “{op.suffix.strip()}”")
    if not op.in_wheel:
        notes.append("fora da roda por padrão")
    return "; ".join(notes) or "—"


def needs(op) -> str:
    if op.needs:
        return ", ".join(f"`{n}`" for n in op.needs)
    if op.mode == ACTION:
        return "—"
    if op.id.endswith(("-doc", "-sheet", "-slides")) or op.id in (
            "to-pdf-text", "pdf-to-docx") or op.id.startswith("to-pdf-"):
        return "Office ([quem converte](Documentos-do-Office.md))"
    return "—"


lines = ["<!-- Gerada a partir de mexerica/engine/ops.py: não edite à mão. -->",
         "# Operações", "",
         "Tudo o que as rodas oferecem. Cada item só aparece quando serve "
         "para o(s) arquivo(s) arrastado(s) **e** o programa dele está "
         "instalado; em [Configurações](Configuracoes.md) dá para tirar itens "
         "da roda ou pôr os que vêm fora dela.", "",
         "A coluna **id** é o nome para a [linha de comando]"
         "(Linha-de-comando.md): `mexerica run <id> arquivos…`.", ""]
for group, title, intro in GROUPS:
    lines += [f"## {title}", "", intro, ""]
    sections: dict[str, list] = {}
    for op in ALL_OPS:
        if op.group == group:
            sections.setdefault(section_of(op), []).append(op)
    for name, ops in sections.items():
        lines += [f"### {name}", "",
                  "| Na roda | O que faz | Detalhes | id | Precisa de |",
                  "|---|---|---|---|---|"]
        for op in ops:
            lines.append(f"| **{TH.wheel_label(op)}** | {what(op)} | "
                         f"{details(op)} | `{op.id}` | {needs(op)} |")
        lines.append("")
out = repo / "docs" / "wiki" / "Operacoes.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(out, sum(1 for line in lines if line.startswith("| **")), "operações")
