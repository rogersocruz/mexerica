# Flutuar

A ação **FLOAT** (roda de **Ações**, Shift + Ctrl) guarda os arquivos numa
bolha sempre visível, para você arrastá-los depois para qualquer lugar: um
e-mail, um chat, outra pasta, um site.

```
        ╭────────╮
       │  [ícone] │(×)   ← fechar, às 3 horas
        ╰────────╯
       relatório.pdf      ← nome; arraste aqui para mover a bolha
```

- **O ícone é o mesmo que o seu computador mostra**: a miniatura (fotos,
  vídeos, PDF), o ícone do tipo de arquivo, ou, para um atalho ou programa,
  o ícone do programa. No Windows vem do Explorer; no GNOME, do Nautilus.
- **O nome embaixo** é o nome de exibição do sistema (um atalho aparece sem o
  `.lnk`; extensões seguem a configuração do Explorer).
- **× às 3 horas** fecha a bolha sem fazer nada.
- **Arrastar a bolha** leva os arquivos. Terminado o arraste, a bolha some.
- **Arrastar o nome** move a bolha pela tela.
- **Vários arquivos:** a bolha mostra o ícone do primeiro, um contador no
  canto e "N arquivos" embaixo; arrastar leva todos.
- A bolha fica acima das outras janelas. No Windows ela nasce sob o ponteiro;
  no GNOME, quem decide a posição é o GNOME.
- O ponteiro sobre a bolha acende um anel na cor do estilo.

## No Windows

O arraste que sai da bolha é o arraste nativo do Windows, o mesmo do
Explorer: aparece a miniatura do Windows, qualquer programa aceita o arquivo
e, **parando sobre um botão da barra de tarefas**, a janela daquele programa
vem para a frente para você soltar lá.

Enquanto esse arraste acontece, o Windows segura o serviço até o drop. Por
isso **a roda não abre num arraste que começa na bolha** (no GNOME abre).
