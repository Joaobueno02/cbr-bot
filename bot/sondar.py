"""Sonda fotos candidatas: para cada fila/<id>/sondar.json com {"urls": [...], "status": "sondar"},
abre cada URL (página de matéria ou imagem direta), encontra as imagens e mede a resolução real.

Resultado em fila/<id>/fotos.json: lista ordenada por área, cada item com url, largura, altura,
origem (og:image, srcset, img...) e a página de onde veio. Também salva miniaturas
fila/<id>/candidatas/NN.jpg (600 px) para conferir o conteúdo da foto.
"""
from __future__ import annotations

import io
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests
from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
MAX_POR_PAGINA = 20


class Coletor(HTMLParser):
    def __init__(self, base: str):
        super().__init__()
        self.base = base
        self.achados: list[tuple[str, str, int]] = []  # (url, origem, largura declarada)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and (a.get("property") or a.get("name") or "").lower() in ("og:image", "og:image:url", "twitter:image", "og:image:secure_url"):
            if a.get("content"):
                self.achados.append((urljoin(self.base, a["content"]), "meta", 9999))
        if tag in ("img", "source"):
            for chave in ("srcset", "data-srcset"):
                if a.get(chave):
                    for parte in a[chave].split(","):
                        bits = parte.strip().split()
                        if bits:
                            w = int(re.sub(r"\D", "", bits[1]) or 0) if len(bits) > 1 and bits[1].endswith("w") else 0
                            self.achados.append((urljoin(self.base, bits[0]), "srcset", w))
            for chave in ("src", "data-src", "data-original", "data-lazy-src"):
                if a.get(chave) and not a[chave].startswith("data:"):
                    w = int(a.get("width", "0") or 0) if str(a.get("width", "0")).isdigit() else 0
                    self.achados.append((urljoin(self.base, a[chave]), tag, w))
        if tag == "a" and a.get("href") and re.search(r"\.(jpe?g|png|webp)(\?|$)", a["href"], re.I):
            self.achados.append((urljoin(self.base, a["href"]), "link", 0))


def medir(url: str, referer: str) -> dict | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Referer": referer}, timeout=30)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content))
        im.load()
        return {"url": url, "largura": im.width, "altura": im.height, "bytes": len(r.content), "_im": im}
    except Exception:
        return None


def sondar(pasta: Path) -> None:
    arq = pasta / "sondar.json"
    pedido = json.loads(arq.read_text(encoding="utf-8"))
    resultados, vistos, erros = [], set(), []
    for url in pedido.get("urls", []):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            r.raise_for_status()
        except Exception as e:
            erros.append(f"{url}: {type(e).__name__}")
            continue
        tipo = r.headers.get("content-type", "")
        if tipo.startswith("image/"):
            candidatos = [(url, "direta", 0)]
        elif "json" in tipo and '"imageinfo"' in r.text:
            # busca da API do Wikimedia Commons: guarda autor e licença como "origem"
            candidatos = []
            for pg in (r.json().get("query", {}).get("pages", {}) or {}).values():
                for ii in pg.get("imageinfo", []):
                    meta = ii.get("extmetadata", {})
                    autor = re.sub(r"<[^>]+>", "", meta.get("Artist", {}).get("value", "")).strip()
                    lic = meta.get("LicenseShortName", {}).get("value", "")
                    alvo = ii.get("thumburl") or ii.get("url")
                    if alvo:
                        candidatos.append((alvo, f"commons · {pg.get('title','')} · {autor} · {lic}"[:240], 0))
        else:
            c = Coletor(url)
            c.feed(r.text)
            candidatos = sorted(c.achados, key=lambda x: -x[2])
            # respostas JSON (ex.: API do Wikimedia) ou páginas sem <img>: pega URLs de imagem soltas no texto
            soltas = re.findall(r"https?://[^\s\"'<>,]+\.(?:jpe?g|png|webp)(?:\?[^\s\"'<>,]*)?", r.text.replace("\\/", "/"), re.I)
            # no Wikimedia, fica só com as miniaturas grandes (2000px), não com o original de 20 MB
            candidatos += [(u, "texto", 0) for u in soltas if "upload.wikimedia" not in u or "/thumb/" in u]
        n = 0
        for cand, origem, _ in candidatos:
            if cand in vistos or re.search(r"\.(svg|gif)(\?|$)|logo|icon|sprite|avatar|banner", cand, re.I):
                continue
            vistos.add(cand)
            m = medir(cand, url)
            n += 1
            if m and m["largura"] >= 400:
                m.update(origem=origem, pagina=url)
                resultados.append(m)
            if n >= MAX_POR_PAGINA:
                break
    resultados.sort(key=lambda m: -(m["largura"] * m["altura"]))
    (pasta / "candidatas").mkdir(exist_ok=True)
    saida = []
    for i, m in enumerate(resultados[:15], start=1):
        im = m.pop("_im").convert("RGB")
        im.thumbnail((600, 600))
        im.save(pasta / "candidatas" / f"{i:02d}.jpg", quality=80)
        m["miniatura"] = f"candidatas/{i:02d}.jpg"
        saida.append(m)
    (pasta / "fotos.json").write_text(json.dumps({
        "quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "candidatas": saida, "erros": erros}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pedido["status"] = "sondado"
    arq.write_text(json.dumps(pedido, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{pasta.name}: {len(saida)} candidatas, {len(erros)} erros")


def main() -> None:
    for arq in sorted((RAIZ / "fila").glob("*/sondar.json")):
        if json.loads(arq.read_text(encoding="utf-8")).get("status") == "sondar":
            sondar(arq.parent)


if __name__ == "__main__":
    main()
