# Política de privacidade da Mexerica

*Última atualização: 26 de novembro de 2026*

A Mexerica é um conversor de arquivos que roda inteiramente no seu
computador.

## O que a Mexerica coleta

**Nada.** A Mexerica não coleta, não armazena em servidores e não envia
para a internet nenhum dado pessoal, arquivo, nome de arquivo, uso ou
telemetria. Ela não tem conta, anúncios nem análise de uso.

## O que fica no seu computador

- **Seus arquivos:** a Mexerica lê os arquivos que você arrasta para a
  roda ou abre pelo menu de contexto, e grava o resultado ao lado do
  original (ou na pasta que você escolher nas Configurações). Nenhum
  arquivo sai do computador.
- **Configurações:** `%APPDATA%\Mexerica\settings.json` (Windows) ou
  `~/.config/mexerica/settings.json` (Linux).
- **Histórico e log:** os últimos trabalhos e o log de erros ficam em
  `%LOCALAPPDATA%\Mexerica\cache` (Windows) ou `~/.cache/mexerica`
  (Linux), só para mostrar na janela Início e para diagnóstico. Você pode
  apagar essas pastas quando quiser.
- **Atalhos de teclado do Windows:** se você pedir, a Mexerica desliga os
  atalhos Alt+Shift e Ctrl+Shift de troca de teclado e guarda os valores
  originais em `%LOCALAPPDATA%\Mexerica\layout-hotkeys.json`, para poder
  devolvê-los.

- **Desfoque próprio (opcional):** com *Configurações > Aparência >
  Desfoque de fundo > Próprio*, a Mexerica tira uma imagem do monitor no
  instante em que a roda abre, para desfocar o fundo atrás dela. A imagem
  fica só na memória, não é gravada em disco e é descartada quando a roda
  fecha.
- **Seleção do Explorer:** para juntar PDFs na ordem da lista e para as
  ações do botão direito, a Mexerica lê quais arquivos estão selecionados
  ou visíveis na janela do Explorer de onde você arrastou. Isso acontece
  só no momento da ação e não sai do computador.

## Rede

A Mexerica só usa a internet quando **você pede** para baixar um formato
extra (*Configurações > Sobre > Formatos extras*): o programa daquele
formato é baixado dos repositórios oficiais (MSYS2 ou winget no Windows; o
gerenciador de pacotes do sistema no Linux). Nada é enviado além do pedido
de download. Na versão da Microsoft Store, essa opção não baixa nada.

## Programas de terceiros

Para converter, a Mexerica chama programas locais (ffmpeg, ImageMagick,
Ghostscript, pandoc, entre outros) e, se estiver instalado, o Microsoft
Office ou o LibreOffice. Todos rodam no seu computador, sem enviar nada.

## Contato

Dúvidas sobre privacidade: abra uma issue em
<https://github.com/rogersocruz/mexerica/issues>.
