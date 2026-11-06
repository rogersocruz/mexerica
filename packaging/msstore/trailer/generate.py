"""Build Store trailer assets using the existing logo, screenshot and Windows voices."""
import base64
import json
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
FFMPEG = r'C:\msys64\ucrt64\bin\ffmpeg.exe'
FFPROBE = r'C:\msys64\ucrt64\bin\ffprobe.exe'
RSVG = r'C:\msys64\ucrt64\bin\rsvg-convert.exe'

# Each cue describes visible content; the source video has no audio stream.
CUES = [
    (0, 1, 'Enviar.', 'Upload.'),
    (1, 2, 'Esperar.', 'Wait.'),
    (2, 3, 'Baixar.', 'Download.'),
    (3, 4.8, 'Ou só um gesto.', 'Or just one gesture.'),
    (5, 7, 'Selecione um arquivo no Explorador.', 'Select a file in File Explorer.'),
    (7, 11.5, 'Segure Shift. Arraste.\nEscolha um formato na roda.', 'Hold Shift. Drag.\nChoose a format on the wheel.'),
    (11.5, 15.3, 'Solte. Pronto.\nA cópia convertida aparece ao lado do original.', 'Drop. Done.\nThe converted copy appears next to the original.'),
    (15.3, 19, 'Mais de 40 formatos.\nFotos, vídeos, músicas, PDFs e documentos.', 'Over 40 formats.\nPhotos, videos, music, PDFs, and documents.'),
    (19, 21.5, 'Remover fundo.\nFundo fora. Um clique.', 'Remove backgrounds.\nOne click. Background gone.'),
    (21.5, 25.5, 'Prints que parecem produto.\nGradiente, cantos e sombra.', 'Screenshots ready to showcase.\nGradients, corners, and shadows.'),
    (25.5, 28.5, 'A mesma foto. Bem mais leve.\nDe 2,4 MB para 887 KB.', 'The same photo. Much smaller.\nFrom 2.4 MB to 887 KB.'),
    (28.5, 32, 'Arquivos sempre à mão.\nArraste arquivos da bolha flutuante.', 'Keep files within reach.\nDrag files from the floating bubble.'),
    (32, 35, 'Do seu jeito.\nCores, tamanho e o que aparece na roda.', 'Make it yours.\nColors, size, and what appears on the wheel.'),
    (35, 39, 'Tudo no seu computador.\nNenhum arquivo vai para a internet.', 'Everything runs on your computer.\nNo files are uploaded to the internet.'),
    (39, 42.5, 'Mexerica. Segure Shift. Arraste. Solte.\nGrátis e de código aberto. Na Microsoft Store.', 'Mexerica. Hold Shift. Drag. Drop.\nFree and open source. On the Microsoft Store.'),
]

# Separate, concise visual descriptions with space for natural speech.
AD = [
    (0, 4.8, 'Enviar, esperar, baixar. Ou só um gesto.', 'Upload, wait, download. Or just one gesture.'),
    (5, 11.5, 'No Explorador, um arquivo é arrastado com Shift. Uma roda aparece. O ponteiro escolhe um formato.', 'In File Explorer, a file is dragged with Shift. A wheel appears. The pointer selects a format.'),
    (11.5, 15.3, 'Ao soltar, a cópia convertida aparece ao lado do original.', 'On release, the converted copy appears next to the original.'),
    (15.3, 19, 'Mais de quarenta formatos de imagens, vídeos, áudio e documentos.', 'Over forty formats for images, video, audio, and documents.'),
    (19, 21.5, 'O fundo da imagem é removido.', 'The image background is removed.'),
    (21.5, 25.5, 'Uma captura ganha fundo em gradiente, cantos arredondados e sombra.', 'A screenshot gains a gradient background, rounded corners, and a shadow.'),
    (25.5, 28.5, 'Uma foto cai de dois vírgula quatro megabytes para oitocentos e oitenta e sete kilobytes.', 'A photo shrinks from two point four megabytes to eight hundred eighty-seven kilobytes.'),
    (28.5, 32, 'Arquivos saem de uma bolha flutuante para outra janela.', 'Files are dragged from a floating bubble into another window.'),
    (32, 35, 'A roda muda de cor e tamanho nas configurações.', 'The wheel changes color and size in settings.'),
    (35, 39, 'Um vídeo vira áudio no computador, sem enviar arquivos à internet.', 'Video converts to audio locally, without uploading files to the internet.'),
    (39, 42.5, 'Mexerica. Grátis e de código aberto. Na Microsoft Store.', 'Mexerica. Free and open source. On the Microsoft Store.'),
]


def timestamp(seconds):
    ms = round(seconds * 1000)
    return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02}.{ms % 1000:03}'


def prepare():
    logo = base64.b64encode((ROOT / 'data/icons/io.github.rogersocruz.Mexerica.svg').read_bytes()).decode()
    wheel = base64.b64encode((ROOT / '.github/assets/wheel-convert.png').read_bytes()).decode()
    for lang, column, headline, subline, badge in [
        ('pt-BR', 2, ['Segure Shift.', 'Arraste. Solte.'], 'Converta arquivos com um gesto.', 'Tudo no seu computador'),
        ('en-US', 3, ['Hold Shift.', 'Drag. Drop.'], 'Convert files with a gesture.', 'Everything runs locally'),
    ]:
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1920" height="1080" viewBox="0 0 1920 1080">
<defs><radialGradient id="bg" cx="85%" cy="45%" r="85%"><stop stop-color="#493020"/><stop offset=".6" stop-color="#211b24"/><stop offset="1" stop-color="#111016"/></radialGradient></defs>
<rect width="1920" height="1080" fill="url(#bg)"/>
<circle cx="1510" cy="525" r="430" fill="none" stroke="#ff9d50" stroke-opacity=".12" stroke-width="2"/>
<image x="1060" y="160" width="820" height="820" xlink:href="data:image/png;base64,{wheel}"/>
<image x="114" y="100" width="94" height="94" xlink:href="data:image/svg+xml;base64,{logo}"/>
<g font-family="Segoe UI, sans-serif" fill="#fff4e9">
<text x="228" y="163" font-size="54" font-weight="700">Mexerica</text>
<text x="128" y="410" font-size="100" font-weight="700">{escape(headline[0])}</text>
<text x="128" y="535" font-size="100" font-weight="700" fill="#ffab65">{escape(headline[1])}</text>
<text x="132" y="635" font-size="37" fill="#d8c8be">{escape(subline)}</text>
<rect x="132" y="738" width="548" height="66" rx="33" fill="#ffab65" fill-opacity=".12" stroke="#ffab65" stroke-opacity=".35"/>
<circle cx="166" cy="771" r="7" fill="#ffab65"/>
<text x="191" y="782" font-size="29">{escape(badge)}</text>
<text x="132" y="963" font-size="28" fill="#aa9ca2">MICROSOFT STORE · WINDOWS</text>
</g></svg>'''
        source = OUT / f'thumbnail.{lang}.svg'
        source.write_text(svg, encoding='utf-8')
        subprocess.run([RSVG, '-o', str(OUT / f'thumbnail.{lang}.png'), str(source)], check=True)
        vtt = 'WEBVTT\n\nNOTE Visual text and actions; source trailer has no audio.\n\n'
        for index, cue in enumerate(CUES, 1):
            vtt += f'{index}\n{timestamp(cue[0])} --> {timestamp(cue[1])}\n{cue[column]}\n\n'
        (OUT / f'captions.{lang}.vtt').write_text(vtt, encoding='utf-8')
    (OUT / 'audio-script.json').write_text(json.dumps([
        {'start': a, 'end': b, 'pt-BR': pt, 'en-US': en} for a, b, pt, en in AD
    ], ensure_ascii=False, indent=2), encoding='utf-8')


def mix():
    for lang in ('pt-BR', 'en-US'):
        command = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y']
        filters, labels = [], []
        for i, (start, end, _, _) in enumerate(AD):
            wav = OUT / 'work' / f'{lang}-{i}.wav'
            duration = float(subprocess.check_output([FFPROBE, '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(wav)]))
            speed = max(1, duration / (end - start - .15))
            if speed > 2:
                raise ValueError(f'Speech too fast: {lang} cue {i}: {speed}')
            command += ['-i', str(wav)]
            filters.append(f'[{i}:a]atempo={speed:.5f},adelay={round(start * 1000)}:all=1[a{i}]')
            labels.append(f'[a{i}]')
        filters.append(''.join(labels) + f'amix=inputs={len(AD)}:normalize=0,apad,atrim=duration=42.5[out]')
        command += ['-filter_complex', ';'.join(filters), '-map', '[out]', '-c:a', 'libmp3lame', '-b:a', '192k', str(OUT / f'audio-description.{lang}.mp3')]
        subprocess.run(command, check=True)


if __name__ == '__main__':
    import sys
    mix() if '--mix' in sys.argv else prepare()
