"""Menu de contexto do Explorer: "Ações da Mexerica" roda isto com o item
clicado (desktop/context.py registra). Abre a roda de ações no ponteiro com
a seleção da janela do Explorer. O pacote é achado pela pasta deste
arquivo (o registro não deixa definir variáveis de ambiente)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mexerica.__main__ import main  # noqa: E402

sys.exit(main(["wheel", "--group", "actions", "--explorer", *sys.argv[1:]]))
