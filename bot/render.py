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
LARGURA_MIN = 1000


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
    return {"largura": w, "altura": h, "aviso": None if w >= LARGURA_MIN else f"foto pequena ({w}x{h}); pode ficar borrada"}


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
        for velha in pasta.glob("arte-*.jpg"):
            velha.unlink()
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
        else:
            for i, s in enumerate(post["slides"], start=1):
                uri = None
                if s.get("foto_url"):
                    meta = baixar_foto(s["foto_url"], pasta / f"foto-{i}.jpg")
                    if meta["aviso"]:
                        rel["avisos"].append(f"slide {i}: {meta['aviso']}")
                    uri = (pasta / f"foto-{i}.jpg").as_uri()
                html_path = pasta / f"arte-{i}.html"
                html_path.write_text(arte.slide(s, uri), encoding="utf-8")
                fit = capturar(pagina, html_path, pasta / f"arte-{i}.jpg")
                rel["artes"].append({"arquivo": f"arte-{i}.jpg", **fit})
        estouros = [a["arquivo"] for a in rel["artes"] if not a.get("ok")]
        if estouros:
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
