"""Renderiza as artes de todos os posts da fila com status "renderizar".

Para cada fila/<id>/post.json:
  1. baixa a(s) foto(s) de `foto_url` (e de cada slide de carrossel que tenha foto)
  2. valida a foto (abre, mede resolução; menos de 1000 px de largura vira aviso)
  3. em Educação, tenta recortar a pessoa do fundo (rembg); se falhar, usa a foto num círculo
  4. gera HTML e tira screenshot 1080x1350 com Chromium -> arte-N.jpg
  5. grava status "renderizado" (ou "erro_render" com o motivo) e o relatório em render.json

Uso: python bot/render.py [--fila fila] [--id <id>]
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import arte  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
LARGURA_MIN = 1000   # abaixo disso a foto é recusada (fica borrada no 1080 px)


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def baixar_foto(url: str, destino: Path) -> dict:
    """Baixa e normaliza a foto para JPEG RGB. Retorna metadados."""
    if url.startswith("repo:"):
        dados = (RAIZ / url[5:]).read_bytes()
    elif url.startswith("file://"):
        dados = Path(url[7:]).read_bytes()
    else:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": url}, timeout=40)
        r.raise_for_status()
        dados = r.content
    im = Image.open(io.BytesIO(dados))
    im.load()
    if im.mode not in ("RGB", "L"):
        fundo = Image.new("RGB", im.size, (16, 16, 16))
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
            fundo.paste(im, mask=im.split()[-1])
            im = fundo
        else:
            im = im.convert("RGB")
    im = im.convert("RGB")
    im.save(destino, "JPEG", quality=95)
    w, h = im.size
    if w < LARGURA_MIN:
        raise ValueError(f"foto com {w}x{h}; o mínimo é {LARGURA_MIN} px de largura. Escolha outra foto (use a sonda).")
    return {"largura": w, "altura": h, "aviso": None}


def recortar(foto: Path, destino: Path) -> bool:
    try:
        from rembg import remove  # import tardio: só Educação precisa
    except Exception:
        return False
    try:
        out = remove(Image.open(foto))
        bbox = out.getbbox()
        if not bbox:
            return False
        out.crop(bbox).save(destino, "PNG")
        return True
    except Exception:
        return False


def quadro_vertical(arte_jpg: Path, saida: Path) -> None:
    """Arte 1080x1350 num quadro 1080x1920 (Story/Reels) sem faixas aparentes (ajuste do João, 26/10/2026):
    embaixo, a cor de fundo da própria arte (a faixa abaixo da barra não tem texto), então a arte continua sem
    emenda; em cima, a faixa de 0 a 40 px da arte (acima da marca) esticada e desfocada, com a borda da arte
    esfumada. No feed (4:5) e no grid aparece só a arte; na tela cheia, a arte parece ocupar o quadro todo."""
    from PIL import ImageDraw, ImageFilter
    arte_im = Image.open(arte_jpg).convert("RGB")
    largura, altura, topo_arte = 1080, 1920, 285
    cor_fundo = arte_im.crop((0, 1310, 1080, 1350)).resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    quadro = Image.new("RGB", (largura, altura), cor_fundo)
    topo = arte_im.crop((0, 0, 1080, 40)).resize((1080, topo_arte + 60), Image.BILINEAR)
    quadro.paste(topo.filter(ImageFilter.GaussianBlur(24)), (0, 0))
    mascara = Image.new("L", arte_im.size, 255)
    desenho = ImageDraw.Draw(mascara)
    for y in range(40):
        desenho.line([(0, y), (arte_im.width, y)], fill=int(255 * y / 40))
    quadro.paste(arte_im, (0, topo_arte), mascara)
    quadro.save(saida, "JPEG", quality=95)


# Qualidade do vídeo (ajuste do João, 28/10/2026): o Reels saía mais mole que o post do feed. Causas: zoom de
# 3,5% reamostrando a arte quadro a quadro, cor em faixa cheia (yuvj/pc, bt470bg) que o Instagram converte mal
# e ~1,5 Mbps de origem. Agora: zoom de 1,5%, faixa de TV bt709 marcada no arquivo e CRF 18.
COR_TV = "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p"
TAGS_COR = ["-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def gerar_reels(quadro: Path, saida: Path, segundos: int = 12) -> None:
    """Vídeo 1080x1920 com zoom lento e suave (1,5%) sobre o quadro vertical, H.264 + faixa de áudio muda
    (a trilha da editoria entra depois, por bot/trilha.py)."""
    import subprocess
    quadros = segundos * 30
    filtro = (f"scale=2160:3840:flags=lanczos,zoompan=z='1+0.015*on/{quadros}':x='iw/2-(iw/zoom/2)':"
              f"y='ih/2-(ih/zoom/2)':d={quadros}:s=1080x1920:fps=30,{COR_TV}")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(quadro),
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-t", str(segundos), "-vf", filtro, "-c:v", "libx264", "-profile:v", "high",
           "-preset", "medium", "-crf", "18", *TAGS_COR, "-c:a", "aac", "-b:a", "128k",
           "-movflags", "+faststart", "-shortest", str(saida)]
    subprocess.run(cmd, check=True)


# Reels animado (aprovado pelo João em 28/10/2026): a arte é capturada em 3 camadas. Só a foto se move (zoom
# lento de 8%); marca fixa; título, texto, barra e rodapé entram subindo e aparecendo entre 0,4 s e 1,1 s.
# As letras nunca são reamostradas, então ficam tão nítidas quanto no feed.
CAMADAS_REELS = {
    "fundo": "body>div>*:not(#foto):not(img){visibility:hidden!important}",
    "marca": "#foto,#bloco,#barra,body>div>img{visibility:hidden!important} html,body,body>div{background:transparent!important}",
    "texto": "body>div>*:not(#bloco):not(#barra){visibility:hidden!important} html,body,body>div{background:transparent!important}",
}


def camadas_reels(pagina, html_path: Path, pasta: Path) -> tuple[Path, Path, Path]:
    """Captura as 3 camadas do Reels animado a partir do mesmo HTML da arte, já no quadro vertical 1080x1920."""
    html = html_path.read_text(encoding="utf-8")
    saidas = {}
    for nome, css in CAMADAS_REELS.items():
        h = pasta / f"reels-{nome}.html"
        h.write_text(html.replace("</style>", css + "</style>", 1), encoding="utf-8")
        pagina.goto(h.as_uri())
        pagina.wait_for_function("window.__fit !== undefined", timeout=30000)
        png = pagina.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}, type="png",
                                omit_background=nome != "fundo")
        img = Image.open(io.BytesIO(png))
        if nome == "fundo":
            plano = pasta / "reels-fundo.jpg"
            img.convert("RGB").save(plano, "JPEG", quality=95)
            saidas[nome] = pasta / "reels-fundo-v.jpg"
            quadro_vertical(plano, saidas[nome])
        else:
            q = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
            q.paste(img.convert("RGBA"), (0, 285))  # mesma posição da arte em quadro_vertical
            saidas[nome] = pasta / f"reels-{nome}.png"
            q.save(saidas[nome])
    return saidas["fundo"], saidas["marca"], saidas["texto"]


def gerar_reels_camadas(fundo: Path, marca: Path, texto: Path, saida: Path, segundos: int = 12) -> None:
    """Vídeo 1080x1920: foto com zoom de 8% (centro um pouco acima do meio, onde ficam os rostos), marca fixa e
    bloco de texto + barra entrando, H.264 + faixa de áudio muda (a trilha entra depois, por bot/trilha.py)."""
    import subprocess
    quadros = segundos * 30
    filtro = (f"[0]scale=2160:3840:flags=lanczos,zoompan=z='1+0.08*on/{quadros}':x='iw/2-(iw/zoom/2)':"
              f"y='ih*0.42-(ih/zoom*0.42)':d={quadros}:s=1080x1920:fps=30[bg];"
              f"[bg][1]overlay=0:0[b2];"
              f"[2]format=rgba,fade=t=in:st=0.4:d=0.7:alpha=1[tx];"
              f"[b2][tx]overlay=x=0:y='if(lt(t,0.4),60,if(lt(t,1.1),60*(1-(t-0.4)/0.7),0))'[v];[v]{COR_TV}[out]")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(fundo), "-loop", "1", "-i", str(marca),
           "-loop", "1", "-i", str(texto), "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-filter_complex", filtro, "-map", "[out]", "-map", "3:a", "-t", str(segundos), "-r", "30",
           "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18", *TAGS_COR,
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(saida)]
    subprocess.run(cmd, check=True)


def gerar_reels_slides(quadros: list[Path], saida: Path, por_slide: float = 4.0, transicao: float = 0.5) -> None:
    """Carrossel em Reels (pedido do João, 27/10/2026): os quadros verticais dos slides em sequência,
    4 s cada, com transição suave, H.264 + faixa de áudio muda (a música entra pela API na publicação)."""
    import subprocess
    n = len(quadros)
    entradas = []
    for q in quadros:
        entradas += ["-loop", "1", "-t", str(por_slide + transicao), "-i", str(q)]
    if n == 1:
        filtro, rotulo = f"[0]{COR_TV}[out]", "[out]"
    else:
        partes, anterior, desloc = [], "[0]", por_slide
        for k in range(1, n):
            rot = f"[v{k}]"
            partes.append(f"{anterior}[{k}]xfade=transition=fade:duration={transicao}:offset={desloc}{rot}")
            anterior, desloc = rot, desloc + por_slide
        partes.append(f"{anterior}{COR_TV}[out]")
        filtro, rotulo = ";".join(partes), "[out]"
    total = por_slide * n + transicao
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *entradas,
           "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
           "-filter_complex", filtro, "-map", rotulo, "-map", f"{n}:a", "-t", str(total), "-r", "30",
           "-c:v", "libx264", "-profile:v", "high", "-preset", "medium", "-crf", "18", *TAGS_COR,
           "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", "-shortest", str(saida)]
    subprocess.run(cmd, check=True)


def capturar(pagina, html_path: Path, saida: Path) -> dict:
    pagina.goto(html_path.as_uri())
    pagina.wait_for_function("window.__fit !== undefined", timeout=30000)
    fit = pagina.evaluate("window.__fit")
    png = pagina.screenshot(clip={"x": 0, "y": 0, "width": 1080, "height": 1350}, type="png")
    Image.open(io.BytesIO(png)).convert("RGB").save(saida, "JPEG", quality=95, subsampling=0)
    return fit


def processar(pasta: Path, pagina) -> None:
    arq = pasta / "post.json"
    post = json.loads(arq.read_text(encoding="utf-8"))
    rel = {"quando": agora(), "artes": [], "avisos": []}
    try:
        for padrao in ("arte-*.jpg", "quadro-*.jpg", "story.jpg", "reels.mp4", "reels-*"):
            for velha in pasta.glob(padrao):
                velha.unlink()
        rod = post.get("rodape") or ""
        if len(rod) > 95:
            raise ValueError(f"rodapé com {len(rod)} caracteres; o máximo é 95 (uma linha)")
        if post.get("formato", "unico") == "unico":
            meta = baixar_foto(post["foto_url"], pasta / "foto.jpg")
            rel["foto"] = meta
            if meta["aviso"]:
                rel["avisos"].append(meta["aviso"])
            uri = (pasta / "foto.jpg").as_uri()
            recorte = False
            if post["editoria"] == "educacao" and post.get("recorte", True):
                recorte = recortar(pasta / "foto.jpg", pasta / "foto-recorte.png")
                if recorte:
                    uri = (pasta / "foto-recorte.png").as_uri()
                else:
                    rel["avisos"].append("recorte automático falhou; foto usada dentro do círculo")
            html_path = pasta / "arte-1.html"
            html_path.write_text(arte.post_unico(post, uri, recorte), encoding="utf-8")
            fit = capturar(pagina, html_path, pasta / "arte-1.jpg")
            rel["artes"].append({"arquivo": "arte-1.jpg", **fit})
            # versão vertical: vai para os Stories quando a collab for aceita, e é a base do Reels
            quadro_vertical(pasta / "arte-1.jpg", pasta / "story.jpg")
            rel["story"] = "story.jpg"
            if post.get("bombastica") or post.get("reels"):  # Reels comum (20/10/2026) usa o mesmo quadro aprovado
                try:
                    gerar_reels_camadas(*camadas_reels(pagina, html_path, pasta), pasta / "reels.mp4")
                    rel["reels"] = {"video": "reels.mp4", "capa": "story.jpg", "animado": True}
                except Exception as e:  # o Reels animado nunca segura o post: cai para o zoom simples
                    rel["avisos"].append(f"Reels animado falhou ({type(e).__name__}: {e}); saiu o zoom simples")
                    gerar_reels(pasta / "story.jpg", pasta / "reels.mp4")
                    rel["reels"] = {"video": "reels.mp4", "capa": "story.jpg", "animado": False}
                finally:
                    for temp in pasta.glob("reels-*"):
                        temp.unlink()
        else:
            for i, s in enumerate(post["slides"], start=1):
                uri = None
                if s.get("foto_url"):
                    meta = baixar_foto(s["foto_url"], pasta / f"foto-{i}.jpg")
                    if meta["aviso"]:
                        rel["avisos"].append(f"slide {i}: {meta['aviso']}")
                    uri = (pasta / f"foto-{i}.jpg").as_uri()
                html_path = pasta / f"arte-{i}.html"
                html_path.write_text(arte.slide(s, uri, post.get("editoria", "gerais")), encoding="utf-8")
                fit = capturar(pagina, html_path, pasta / f"arte-{i}.jpg")
                rel["artes"].append({"arquivo": f"arte-{i}.jpg", **fit})
            if post.get("reels") and rel["artes"]:  # carrossel que também sai como Reels (27/10/2026)
                quadros = []
                for a in rel["artes"]:
                    q = pasta / a["arquivo"].replace("arte-", "quadro-")
                    quadro_vertical(pasta / a["arquivo"], q)
                    quadros.append(q)
                quadro_vertical(pasta / "arte-1.jpg", pasta / "story.jpg")
                rel["story"] = "story.jpg"
                gerar_reels_slides(quadros, pasta / "reels.mp4")
                rel["reels"] = {"video": "reels.mp4", "capa": "story.jpg"}
        sem_fonte = [a["arquivo"] for a in rel["artes"] if a.get("fontes_ok") is False]
        estouros = [a["arquivo"] for a in rel["artes"] if not a.get("ok") and a.get("fontes_ok") is not False]
        ign = sorted({k for k in post if k in ("titulo_max", "bloco_subir", "barra_invertida", "cbr_escala", "peso_titulo",
                                              "destaque_estilo", "destaque_faixa", "destaque_opacidade", "cor_destaque", "sem_rodape")})
        if ign:
            rel["avisos"].append(f"campos visuais ignorados (o padrão da editoria vence): {', '.join(ign)}")
        if sem_fonte:
            post["status"] = "erro_render"
            rel["erro"] = f"fontes da identidade não carregaram em {', '.join(sem_fonte)}; a arte sairia com outra fonte. Renderize de novo."
        elif estouros:
            post["status"] = "erro_render"
            rel["erro"] = f"texto não coube mesmo no tamanho mínimo: {', '.join(estouros)}. Encurte título/apoio."
        else:
            post["status"] = "renderizado"
    except Exception as e:  # erro de download, imagem inválida etc.
        post["status"] = "erro_render"
        rel["erro"] = f"{type(e).__name__}: {e}"
        rel["trace"] = traceback.format_exc(limit=3)
    post["render"] = rel
    arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{pasta.name}: {post['status']} {rel.get('erro','')}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fila", default=str(RAIZ / "fila"))
    ap.add_argument("--id")
    a = ap.parse_args()
    pastas = []
    for arq in sorted(Path(a.fila).glob("*/post.json")):
        if a.id and arq.parent.name != a.id:
            continue
        st = json.loads(arq.read_text(encoding="utf-8")).get("status")
        if st == "renderizar":
            pastas.append(arq.parent)
    if not pastas:
        print("nada para renderizar")
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--allow-file-access-from-files"])
        pagina = nav.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for pasta in pastas:
            processar(pasta, pagina)
        nav.close()


if __name__ == "__main__":
    main()
