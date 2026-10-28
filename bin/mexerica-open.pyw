"""Menu de contexto do Explorer: "Converter com a Mexerica" roda isto com o
arquivo clicado. O install.ps1 põe este arquivo na pasta do app, que o
Python acrescenta ao sys.path: o pacote é achado sem PYTHONPATH (o
registro não deixa definir variáveis de ambiente)."""
import sys

from mexerica.__main__ import main

sys.exit(main(["open", *sys.argv[1:]]))
