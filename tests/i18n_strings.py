"""Os textos que passam pela tradução (i18n._), achados no código-fonte.

Conta como texto traduzível o literal passado a `_()`, `N_()`, `plural()`
e aos helpers que traduzem sozinhos (label, _hint, _section, _page, _row,
say, SliderRow, row, Segmented, dropdown, EditorWindow) e os textos das
listas de opções no nível do módulo marcadas com N_. Usado pelo
test_i18n.py; rodar direto lista o que falta no catálogo inglês:

    python tests/i18n_strings.py
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "mexerica"
# helper -> posições dos argumentos que são texto
HELPERS = {"_": (0,), "N_": (0,), "plural": (1, 2), "label": (0,),
           "_hint": (0,), "_section": (0,), "_page": (0, 1), "_row": (0, 1),
           "say": (0,), "SliderRow": (0,), "row": (0,)}
# super().__init__(app, op, título, ..., primary=...) das janelas de edição
LIST_HELPERS = {"Segmented", "dropdown"}
# listas de opções (rótulo na posição 0) das janelas de edição
OPTION_LISTS = {"ASPECTS", "SIZES", "WEIGHTS", "TARGETS", "HEIGHTS",
                "BG_RATIOS"}


def _strings(node) -> list[str]:
    """Literais de texto dentro de uma expressão (ternários e somas)."""
    out = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            out.append(sub.value)
        if isinstance(sub, ast.JoinedStr):
            return out                     # f-string: não é um texto fixo
    return out


def _name(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def collect() -> dict[str, list[str]]:
    """{texto: [arquivo:linha, ...]}"""
    found: dict[str, list[str]] = {}

    def add(text: str, where: str) -> None:
        if text.strip() and any(c.isalpha() for c in text):
            found.setdefault(text, []).append(where)

    for path in sorted(ROOT.rglob("*.py")):
        if path.name == "i18n_en.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel = path.relative_to(ROOT.parent).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = _name(node.func)
                where = f"{rel}:{node.lineno}"
                if name in HELPERS:
                    for i in HELPERS[name]:
                        if i < len(node.args):
                            # say/label com texto montado (concatenação)
                            # traduzem o resultado: só literais simples
                            arg = node.args[i]
                            if isinstance(arg, ast.Constant):
                                add(arg.value, where) if isinstance(
                                    arg.value, str) else None
                            elif isinstance(arg, ast.IfExp):
                                for s in _strings(arg):
                                    add(s, where)
                elif name in LIST_HELPERS and node.args and \
                        isinstance(node.args[0], (ast.List, ast.Tuple)):
                    for s in _strings(node.args[0]):
                        add(s, where)
                elif name == "__init__" and isinstance(node.func,
                                                       ast.Attribute) and \
                        isinstance(node.func.value, ast.Call) and \
                        _name(node.func.value.func) == "super" and \
                        "editors" in rel:
                    # super().__init__(app, op, título, ..., primary=...)
                    if len(node.args) > 2:
                        for s in _strings(node.args[2]):
                            add(s, where)
                    for kw in node.keywords:
                        if kw.arg == "primary":
                            for s in _strings(kw.value):
                                add(s, where)
                    if len(node.args) > 3 and isinstance(node.args[3],
                                                         ast.Constant) \
                            and isinstance(node.args[3].value, str):
                        add(node.args[3].value, where)   # _OrganizerWindow
            elif isinstance(node, (ast.Assign, ast.AnnAssign)) and \
                    "editors" in rel and \
                    any(isinstance(t, ast.Name) and t.id in OPTION_LISTS
                        for t in (node.targets if isinstance(node, ast.Assign)
                                  else [node.target])) and \
                    isinstance(node.value, (ast.List, ast.Tuple)):
                for item in node.value.elts:
                    if isinstance(item, ast.Tuple) and item.elts and \
                            isinstance(item.elts[0], ast.Constant):
                        add(item.elts[0].value, f"{rel}:{node.lineno}")
    return found


def data_strings() -> list[str]:
    """Textos que vêm de dados: nomes e dicas das operações, programas,
    estilos, estados do Desbloquear e passos dos atalhos."""
    from mexerica import theme as TH
    from mexerica.desktop import hotkeys
    from mexerica.editors.pdf import PdfUnlockWindow
    from mexerica.engine import tools as T
    from mexerica.engine.ops import ALL_OPS
    out = []
    for op in ALL_OPS:
        out += [op.label, op.hint]
    out += [w for _n, w in T.PROGRAMS + T.MODULES]
    out += [p["name"] for p in TH.STYLES.values()]
    out += list(PdfUnlockWindow.STATES.values())
    out += [hotkeys.STEPS]
    return [s for s in out if s and any(c.isalpha() for c in s)]


def missing() -> list[str]:
    from mexerica.i18n_en import EN
    texts = set(collect()) | set(data_strings())
    return sorted(t for t in texts if t not in EN and not _same(t))


def _same(text: str) -> bool:
    """Textos iguais nos dois idiomas (nomes de formato, siglas, marcas)."""
    import re
    from mexerica.i18n_en import SAME
    return (text in SAME or not any(c.islower() for c in text)
            or bool(re.fullmatch(r"[\d ,.≤]+(p|px|KB|MB|kbps)?", text)))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT.parent))
    found = collect()
    for text in missing():
        print(repr(text), "  #", ", ".join(found.get(text, ["dados"])[:2]))
