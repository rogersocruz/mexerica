# Linha de comando

O motor não depende da interface: tudo o que a roda faz também roda pelo
terminal. No Windows o comando `mexerica` é instalado no PATH do usuário
(abra um terminal novo depois de instalar).

```bash
mexerica                      # serviço (ou, com ele rodando, abre as Configurações)
mexerica list foto.heic       # o que cada roda ofereceria para o arquivo
mexerica list --group tools *.mp4
mexerica run to-jpg *.heic    # converte sem interface
mexerica run vid-25mb video.mov
mexerica run img-crop foto.jpg   # operação com janela: pede ao serviço para abri-la
mexerica doctor               # programas encontrados e quem converte o Office
mexerica --version
```

- Os ids das operações estão em [Operações](Operacoes.md). `run` aceita
  também os itens escondidos da roda e os presets fora dela.
- As regras são as mesmas da roda: nunca sobrescreve, temporário oculto,
  pasta de saída e qualidade do JPG das [Configurações](Configuracoes.md).
- `run` imprime os arquivos gerados (ou o texto, para metadados e QR code) e
  termina com código 1 se algo falhar; o erro sai no stderr.
- As ações de interface (copiar caminho, terminal, copiar/mover, flutuar) só
  funcionam pela roda.
- `-v` mostra o log no terminal.

Serviço:

- `mexerica --gapplication-service` (Linux, autostart e D-Bus) e
  `mexerica daemon` (Windows, atalho da pasta Inicializar) sobem o serviço
  sem abrir janela.

Isso permite reaproveitar o motor em scripts, Nautilus Scripts ou num menu de
serviço do Dolphin.
