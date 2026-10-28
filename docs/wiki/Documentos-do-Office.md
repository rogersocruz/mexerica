# Documentos do Office

DOCX, XLSX, PPTX, ODT, ODS, ODP, RTF e afins **não exigem o LibreOffice**.
Quem converte cada documento é escolhido nesta ordem
(`mexerica/engine/office.py`):

1. **Microsoft Office** (Windows): Word, Excel e PowerPoint por automação,
   sem abrir janela. É a conversão mais fiel para os formatos da Microsoft, e
   o **Word transforma PDF em DOCX editável**.
2. **LibreOffice**, se estiver instalado. É o único que abre **Pages, Keynote,
   Numbers e WordPerfect**.
3. **pandoc + typst**, sem nenhum dos dois (instalados pelo `-Converters`):
   - textos (DOCX, ODT, RTF) viram PDF, ODT, RTF e TXT;
   - planilhas (XLSX, CSV) e apresentações (PPTX) viram PDF **com o
     conteúdo** (texto, tabelas, imagens), **sem o layout** de página, de
     planilha ou de slide.

Markdown, HTML, TXT e EPUB para PDF: com Office, o pandoc gera um DOCX e o
Office faz o PDF; sem Office, o typst faz o PDF direto.

A roda só oferece o que alguém na máquina consegue converter: sem Office, por
exemplo, uma planilha `.ods` não mostra nada, e um `.xlsx` só mostra PDF.

`mexerica doctor` e **Configurações > Sobre** mostram quem converte cada tipo
nesta máquina:

```
Textos → PDF: Microsoft Office
Planilhas → PDF: Microsoft Office
Apresentações → PDF: Microsoft Office
```

## O que se perde sem o LibreOffice

| Situação | O que fica de fora |
|---|---|
| Com Microsoft Office | Só os formatos da Apple (Pages, Keynote, Numbers) e o WordPerfect |
| Sem Office nenhum, com pandoc + typst | Layout de planilhas e apresentações no PDF; abrir ODS, ODP, XLS, PPT e DOC; XLSX para CSV/ODS |

Para esses casos: `install.cmd -Office` (Windows) ou `libreoffice-fresh`
(Arch).

## Cuidados com o Office que você está usando

A automação pode pegar o Word, o Excel ou o PowerPoint que você está usando.
Por isso a Mexerica:

- nunca mexe na visibilidade nem fecha um Office com outros documentos
  abertos; devolve os avisos do Office como estavam;
- dispensa a pergunta do Word ao abrir PDF só durante a conversão;
- abre CSV em UTF-8 por uma cópia com BOM (o Excel leria os acentos errado);
- usa uma senha falsa: documento protegido dá erro, em vez de esperar uma
  senha numa janela invisível;
- dá 300 s de limite; se o Office travar, encerra só o processo que ela
  mesma abriu, e limpa a marca de "erro grave" que o Office põe no arquivo.
