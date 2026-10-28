# Instalação no Linux (GNOME)

Feito para **GNOME Shell 45–51 em Wayland**. No Arch Linux:

```bash
# obrigatório
sudo pacman -S --needed python-gobject gtk4
# conversores (instale os que quiser; a roda se adapta)
sudo pacman -S --needed ffmpeg imagemagick libheif librsvg poppler qpdf \
    ghostscript perl-image-exiftool zbar pandoc-cli typst libreoffice-fresh

git clone https://github.com/rogersocruz/mexerica
cd mexerica
./install.sh          # instala em ~/.local, sem sudo
```

Depois disso, **saia e entre de novo na sessão**: no Wayland o GNOME Shell só
carrega uma extensão nova no login.

O que o `install.sh` faz:

- copia o pacote para `~/.local/share/mexerica` e o comando para
  `~/.local/bin/mexerica`;
- instala a extensão do GNOME Shell (`mexerica@rogersocruz.github.io`) e a
  habilita;
- instala o serviço D-Bus, o atalho no menu de apps (abre as
  [Configurações](Configuracoes.md)) e o autostart (`~/.config/autostart`);
- reinicia o serviço.

Para instalar como pacote do sistema, use o PKGBUILD:
`cd packaging/arch && makepkg -si`.

Outras distribuições: os mesmos programas pelos nomes de lá. O essencial é
PyGObject com GTK 4; o resto é opcional.

## Conferir e desinstalar

- `mexerica doctor` mostra o que foi encontrado (o mesmo que
  **Configurações > Sobre**).
- `./uninstall.sh` remove tudo o que o `install.sh` pôs. Log e cache ficam em
  `~/.cache/mexerica` e as configurações em `~/.config/mexerica`.

## Limitações do GNOME

- **Shift + arrastar no Nautilus normalmente força "mover".** Com a
  Mexerica ativa, o Shift abre a roda. Para mover entre discos, arraste sem
  Shift e escolha *Mover*, ou use Ctrl+X / Ctrl+V.
- **Shift+Alt não abre a roda se Alt+Shift troca o layout do teclado**
  (opção xkb `grp:alt_shift_toggle`). Remova a opção e troque o layout com
  Super+Espaço:
  `gsettings set org.gnome.desktop.input-sources xkb-options "[]"`.
- **Setas e Enter não funcionam durante o arraste**: o Mutter não entrega
  essas teclas a ninguém enquanto um arraste está em andamento.
