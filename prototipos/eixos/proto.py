"""Protótipos de design: América Latina (A e B) e Da Terra (A e B).
Usa as fontes, a textura e a marcação do bot/arte.py, sem alterar o bot (a trava visual continua valendo).
"""
from __future__ import annotations

import html
import io
import json
import sys
from pathlib import Path

RAIZ = Path("/home/claude/cbr-bot")
sys.path.insert(0, str(RAIZ / "bot"))
import arte  # noqa: E402
from arte import W, H, marcar, _pagina, PAPEL  # noqa: E402

OUT = Path(__file__).resolve().parent / "saida"
OUT.mkdir(exist_ok=True)


def icone(cor: str, top: int = 70) -> str:
    return arte.ICONE.format(top=top, cor=cor)


def broto(cor: str, x: int = 80, y: int = 66, tam: int = 38) -> str:
    """Ícone de broto (Da Terra): dois cotilédones sobre um caule, traço grosso como o ícone da CBR."""
    return (f'<svg style="position:absolute;z-index:6;left:{x}px;top:{y}px" width="{tam}" height="{tam}" viewBox="0 0 100 100" aria-hidden="true">'
            f'<g fill="none" stroke="{cor}" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M50 92 L50 46" stroke-width="10"/>'
            f'<path d="M50 52 C50 30 34 18 12 18 C12 40 28 52 50 52 Z" fill="{cor}" stroke-width="6"/>'
            f'<path d="M50 44 C50 22 66 8 90 8 C90 32 72 44 50 44 Z" fill="{cor}" stroke-width="6"/>'
            f'<path d="M30 92 L70 92" stroke-width="9"/></g></svg>')


def lockup(nome: str, cor_cbr: str, cor_nome: str, cor_vazado: str, x_cbr: int, largura_vb: int,
           left: int = 128, top: int = 50, escala: float = 0.75, extra: str = "") -> str:
    tam = round(118 * escala, 1)
    base = round(101 - (1 - escala) * 118 * 0.36, 1)
    w = round(largura_vb * 96 / 140)
    cbr = (f'<text x="{x_cbr}" y="{base}" font-family="Unbounded, Archivo, sans-serif" font-weight="900" '
           f'font-size="{tam}" letter-spacing="-4"')
    return (f'<svg style="position:absolute;z-index:6;left:{left}px;top:{top}px" width="{w}" height="96" viewBox="0 0 {largura_vb} 140" role="img" aria-label="{html.escape(nome)} CBR">'
            f'<defs><clipPath id="cbrclip">{cbr}>CBR</text></clipPath></defs>'
            f'{cbr} fill="{cor_cbr}">CBR</text>'
            f'<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="{cor_nome}">{html.escape(nome)}</text>'
            f'<g clip-path="url(#cbrclip)"><text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="{cor_vazado}">{html.escape(nome)}</text></g>'
            f'{extra}</svg>')


def papel(modo: str, op: float) -> str:
    return (f'<img src="{PAPEL.as_uri()}" alt="" style="position:absolute;z-index:5;left:0;top:0;width:{W}px;height:{H}px;'
            f'mix-blend-mode:{modo};opacity:{op};pointer-events:none">')


def bloco(partes: list[str], esq: int, fundo: int, direita: int = 50) -> str:
    return (f'<div id="bloco" data-limite="300" style="position:absolute;z-index:3;left:{esq}px;right:{direita}px;'
            f'bottom:{H - fundo}px">{"".join(partes)}</div>')


def titulo(p: dict, cor: str, dest: str, faixa=(55, 95), op=0.9, maxt=52, peso=640) -> str:
    return (f'<p id="titulo" data-max="{maxt}" data-min="44" style="margin:0;font-family:Fraunces,Georgia,serif;font-weight:{peso};'
            f'font-size:{maxt}px;line-height:1.05;letter-spacing:-1px;color:{cor}">'
            f'{marcar(p["titulo"], dest, cor, titulo=True, peso_destaque=peso + 100, estilo="marca_inclinada", faixa=faixa, opacidade=op)}</p>')


def chapeu(texto: str, cor: str, tam: int = 66, peso: int = 740) -> str:
    return (f'<p style="margin:0 0 14px;font-family:Fraunces,Georgia,serif;font-weight:{peso};font-size:{tam}px;line-height:1;'
            f'letter-spacing:-1px;text-transform:uppercase;color:{cor}">{html.escape(texto)}</p>')


def subtitulo(texto: str, cor: str, dest: str, negrito: str) -> str:
    return (f'<p style="margin:26px 0 0;font-family:Archivo,sans-serif;font-size:22px;line-height:1.42;color:{cor}">'
            f'{marcar(texto, dest, negrito)}</p>')


def credito(texto: str, cor: str) -> str:
    return (f'<p style="margin:0 0 22px;font-family:Archivo,sans-serif;font-weight:700;font-size:17px;letter-spacing:2px;'
            f'text-transform:uppercase;color:{cor}">{html.escape(texto)}</p>')


def foto_cheia(uri: str, pos: str, bg_rgb: str, bg: str, minimo: int, filtro: str = "") -> str:
    return (f'<div id="foto" data-min="{minimo}" style="position:absolute;z-index:1;left:0;right:0;top:0;height:{minimo}px;overflow:hidden">'
            f'<img src="{uri}" alt="" style="display:block;width:100%;height:100%;object-fit:cover;object-position:{pos};{filtro}">'
            f'<div style="position:absolute;left:0;right:0;top:0;height:240px;background:linear-gradient(to bottom,rgba({bg_rgb},.8) 0%,rgba({bg_rgb},0) 100%)"></div>'
            f'<div style="position:absolute;left:0;right:0;bottom:0;height:300px;background:linear-gradient(to bottom,rgba({bg_rgb},0) 0%,rgba({bg_rgb},.85) 60%,{bg} 100%)"></div></div>')


def barra(y: int, esq: int, base: str, ponta: str) -> str:
    larg = 1000 - esq - 40
    fim = esq + larg
    return (f'<div style="position:absolute;z-index:3;left:{esq}px;width:{larg}px;top:{y}px;height:4px;background:{base}"></div>'
            f'<div style="position:absolute;z-index:3;left:{fim - 110}px;width:110px;top:{y}px;height:4px;background:{ponta}"></div>')


# ------------------------------------------------------------------ AMÉRICA LATINA
AL_CORES = ["#FF5A1F", "#FED700", "#2BA84A", "#1E88E5", "#8E3FBF", "#E53935"]


def barra_tecida(y: int, esq: int, alto: int = 8) -> str:
    """Faixa 'tecida': blocos alternados nas cores do continente, como uma barra de tecido andino."""
    larg = 1000 - esq - 40
    blocos, x, i = [], 0, 0
    padrao = [26, 10, 26, 10, 54, 10]
    while x < larg:
        w = min(padrao[i % len(padrao)], larg - x)
        blocos.append(f'<div style="position:absolute;left:{x}px;top:0;width:{w}px;height:{alto}px;background:{AL_CORES[i % len(AL_CORES)]}"></div>')
        x += w + 4
        i += 1
    return f'<div style="position:absolute;z-index:3;left:{esq}px;top:{y}px;width:{larg}px;height:{alto}px">{"".join(blocos)}</div>'


def al_a(p: dict, uri: str) -> str:
    """A — 'Pátria Grande': escuro, foto cheia, laranja-urucum, selo de país e barra tecida."""
    bg, tx, sub, dest = "#101010", "#FFFFFF", "#C9C6C0", "#FF5A1F"
    esq = 120
    selo = (f'<p style="margin:0 0 20px;display:inline-flex;align-items:center;gap:10px;padding:8px 16px 8px 12px;'
            f'border:2px solid {dest};border-radius:40px;font-family:Archivo,sans-serif;font-weight:700;font-size:19px;'
            f'letter-spacing:3px;text-transform:uppercase;color:{tx}">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{dest};display:inline-block"></span>{html.escape(p["pais"])}</p>')
    partes = [f'<div>{selo}</div>', chapeu(p["chapeu"], dest), titulo(p, tx, dest)]
    if p.get("subtitulo"):
        partes.append(subtitulo(p["subtitulo"], sub, dest, tx))
    marca = icone(dest) + lockup("AMÉRICA LATINA", dest, tx, "#101010", 372, 690)
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx}">'
             f'{foto_cheia(uri, p.get("foto_posicao", "50% 40%"), "16,16,16", bg, 800)}{marca}'
             f'{bloco(partes, esq, 1262 - 40 - 110)}{barra_tecida(1258, esq)}{papel("overlay", .35)}</div>')
    return _pagina(corpo, bg)


def al_b(p: dict, uri: str) -> str:
    """B — 'Continente': papel claro, foto com corte diagonal, rosa-mexicano e o país em letra grande."""
    bg, tx, sub, dest = "#ECEAE5", "#101010", "#4E4B47", "#E4007C"
    esq = 120
    corte = 720
    foto = (f'<div style="position:absolute;z-index:1;left:0;top:0;width:{W}px;height:{corte + 90}px;'
            f'clip-path:polygon(0 0,100% 0,100% 78%,0 100%);overflow:hidden">'
            f'<img src="{uri}" alt="" style="width:100%;height:100%;object-fit:cover;object-position:{p.get("foto_posicao", "50% 40%")}">'
            f'<div style="position:absolute;left:0;right:0;top:0;height:220px;background:linear-gradient(to bottom,rgba(16,16,16,.55),rgba(16,16,16,0))"></div></div>'
            # faixa rosa acompanhando a diagonal
            f'<div style="position:absolute;z-index:2;left:0;top:0;width:{W}px;height:{corte + 104}px;background:{dest};'
            f'clip-path:polygon(0 {corte + 90}px,100% {round((corte + 90) * .78)}px,100% {round((corte + 90) * .78) + 14}px,0 {corte + 104}px)"></div>'
            # etiqueta do país apoiada na diagonal
            f'<p style="position:absolute;z-index:3;left:{esq - 14}px;top:{corte + 2}px;margin:0;padding:10px 22px 12px;background:{dest};'
            f'font-family:Unbounded,Archivo,sans-serif;font-weight:900;font-size:46px;line-height:1;letter-spacing:-1px;color:#FFFFFF;'
            f'transform:rotate(-6.1deg);transform-origin:left bottom;text-transform:uppercase">{html.escape(p["pais"])}</p>')
    partes = []
    if p.get("credito_foto"):
        partes.append(credito(p["credito_foto"], sub))
    partes += [chapeu(p["chapeu"], dest, 60), titulo(p, tx, dest, faixa=(64, 100), op=.35)]
    if p.get("subtitulo"):
        partes.append(subtitulo(p["subtitulo"], sub, dest, tx))
    marca = icone("#FFFFFF") + lockup("AMÉRICA LATINA", dest, "#FFFFFF", "#101010", 372, 690)
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx}">'
             f'{foto}{marca}{bloco(partes, esq, 1278 - 40 - 40)}{barra(1278, esq, dest, "#CBC9C4")}{papel("multiply", .16)}</div>')
    return _pagina(corpo, bg)


# ------------------------------------------------------------------ DA TERRA
def terra_a(p: dict, uri: str) -> str:
    """A — 'Raiz': terra escura, foto cheia e quente, amarelo-milho e broto verde."""
    bg, tx, sub, dest, verde = "#17130E", "#F6F0E4", "#CFC4B2", "#E9A23B", "#86B34A"
    esq = 120
    partes = [chapeu(p["chapeu"], dest), titulo(p, tx, dest)]
    if p.get("subtitulo"):
        partes.append(subtitulo(p["subtitulo"], sub, dest, tx))
    marca = broto(verde, 78, 64) + lockup("DA TERRA", dest, tx, bg, 250, 560)
    sulcos = "".join(  # linhas de plantio sob a barra
        f'<div style="position:absolute;z-index:3;left:{esq + i * 22}px;top:1272px;width:12px;height:4px;border-radius:2px;background:{verde};opacity:{.9 - i * .07:.2f}"></div>'
        for i in range(12))
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx}">'
             f'{foto_cheia(uri, p.get("foto_posicao", "50% 40%"), rgb, bg, 800, "filter:saturate(1.08) sepia(.12) contrast(1.04)")}{marca}'
             f'{bloco(partes, esq, 1262 - 40 - 110)}{barra(1258, esq, dest, cores["base_barra"])}{sulcos}{papel("overlay", .4)}</div>')
    return _pagina(corpo, bg)


def selo_terra(cor: str, fundo: str, x: int, y: int, d: int = 210) -> str:
    texto = "AGRICULTURA FAMILIAR · DA TERRA · CBR · "
    return (f'<svg style="position:absolute;z-index:4;left:{x}px;top:{y}px;transform:rotate(-12deg)" width="{d}" height="{d}" viewBox="0 0 200 200" aria-hidden="true">'
            f'<defs><path id="circ" d="M100,100 m-74,0 a74,74 0 1,1 148,0 a74,74 0 1,1 -148,0"/></defs>'
            f'<circle cx="100" cy="100" r="97" fill="{fundo}"/><circle cx="100" cy="100" r="90" fill="none" stroke="{cor}" stroke-width="2"/>'
            f'<circle cx="100" cy="100" r="54" fill="none" stroke="{cor}" stroke-width="2"/>'
            f'<text font-family="Archivo, sans-serif" font-weight="700" font-size="15.2" letter-spacing="2.6" fill="{cor}">'
            f'<textPath href="#circ">{texto}</textPath></text>'
            f'<g transform="translate(64,62) scale(.72)" fill="none" stroke="{cor}" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M50 92 L50 46" stroke-width="10"/><path d="M50 52 C50 30 34 18 12 18 C12 40 28 52 50 52 Z" fill="{cor}" stroke-width="6"/>'
            f'<path d="M50 44 C50 22 66 8 90 8 C90 32 72 44 50 44 Z" fill="{cor}" stroke-width="6"/></g></svg>')


def terra_b(p: dict, uri: str) -> str:
    """B — 'Feira': papel kraft, foto em arco, verde-roça e selo redondo de agricultura familiar."""
    bg, tx, sub, dest, ouro = "#EBDDBA", "#2A1D10", "#5B4A36", "#2F7D32", "#C98A1B"
    esq = 120
    arco = (f'<div style="position:absolute;z-index:1;left:110px;top:176px;width:860px;height:600px;border-radius:430px 430px 0 0;'
            f'border:3px solid {dest};transform:translate(14px,14px)"></div>'
            f'<div style="position:absolute;z-index:2;left:110px;top:176px;width:860px;height:600px;border-radius:430px 430px 0 0;overflow:hidden">'
            f'<img src="{uri}" alt="" style="width:100%;height:100%;object-fit:cover;object-position:{p.get("foto_posicao", "50% 40%")};filter:saturate(1.05)"></div>')
    partes = []
    if p.get("credito_foto"):
        partes.append(credito(p["credito_foto"], sub))
    partes += [chapeu(p["chapeu"], dest, 60), titulo(p, tx, dest, faixa=(64, 100), op=.4)]
    if p.get("subtitulo"):
        partes.append(subtitulo(p["subtitulo"], sub, dest, tx))
    marca = broto(dest, 78, 64) + lockup("DA TERRA", dest, tx, bg, 250, 560)
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx}">'
             f'{arco}{selo_terra(dest, bg, 790, 120)}{marca}{bloco(partes, esq, 1278 - 40 - 70)}'
             f'{barra(1278, esq, dest, "#CDBF9F")}{papel("multiply", .22)}</div>')
    return _pagina(corpo, bg)


def render(nome: str, html_txt: str) -> Path:
    from playwright.sync_api import sync_playwright
    from PIL import Image
    h = OUT / f"{nome}.html"
    h.write_text(html_txt, encoding="utf-8")
    with sync_playwright() as pw:
        nav = pw.chromium.launch(args=["--allow-file-access-from-files"])
        pg = nav.new_page(viewport={"width": W, "height": H})
        pg.goto(h.as_uri())
        pg.wait_for_function("window.__fit !== undefined", timeout=30000)
        fit = pg.evaluate("window.__fit")
        png = pg.screenshot(clip={"x": 0, "y": 0, "width": W, "height": H}, type="png")
        nav.close()
    j = OUT / f"{nome}.jpg"
    Image.open(io.BytesIO(png)).convert("RGB").save(j, "JPEG", quality=92)
    print(nome, fit)
    return j


# ------------------------------------------------------------------ CAMPO, com nome escrito à mão
FONTES_MAO = {
    "PermanentMarker": "fonts/fontsource-permanent-marker-5.3.0/package/files/permanent-marker-latin-400-normal.woff2",
    "CaveatBrush": "fonts/fontsource-caveat-brush-5.3.0/package/files/caveat-brush-latin-400-normal.woff2",
}


def marca_mao(nome: str, fonte: str, cor_cbr: str, cor_mao: str, tam_mao: int, cor_mao_txt: str = "#F6F0E4") -> str:
    uri = (Path(__file__).resolve().parent.parent / FONTES_MAO[fonte]).as_uri()
    ff = f"<style>@font-face{{font-family:'{fonte}';src:url('{uri}') format('woff2')}}</style>"
    # traço à mão sob o nome (curva levemente torta)
    risco = (f'<svg style="position:absolute;left:-6px;bottom:-18px" width="100%" height="18" viewBox="0 0 300 18" preserveAspectRatio="none">'
             f'<path d="M3 11 C 60 4, 120 15, 180 8 S 270 6, 297 10" fill="none" stroke="{cor_mao}" stroke-width="4.5" stroke-linecap="round"/></svg>')
    return (ff + f'<div style="position:absolute;z-index:6;left:80px;top:46px;line-height:1">'
            f'<div style="font-family:Unbounded,Archivo,sans-serif;font-weight:900;font-size:84px;letter-spacing:-4px;color:{cor_cbr}">CBR</div>'
            f'<div style="position:relative;display:inline-block;margin:-8px 0 0 64px;font-family:{fonte};font-size:{tam_mao}px;'
            f'color:{cor_mao_txt};text-shadow:0 2px 10px rgba(0,0,0,.55);transform:rotate(-5deg);transform-origin:left center;white-space:nowrap">{html.escape(nome)}{risco}</div></div>')


def campo_mao(p: dict, uri: str) -> str:
    cores = {"bg": "#17130E", "tx": "#F6F0E4", "sub": "#CFC4B2", "dest": "#E9A23B", "verde": "#9BC45A",
             "base_barra": "#3B342A", "mao": "#F6F0E4", **p.get("cores", {})}
    bg, tx, sub, dest, verde = cores["bg"], cores["tx"], cores["sub"], cores["dest"], cores["verde"]
    rgb = ",".join(str(int(bg[i:i + 2], 16)) for i in (1, 3, 5))
    esq = 120
    partes = [chapeu(p["chapeu"], dest), titulo(p, tx, dest)]
    if p.get("subtitulo"):
        partes.append(subtitulo(p["subtitulo"], sub, dest, tx))
    marca = marca_mao(p["nome_eixo"], p["fonte_mao"], dest, verde, p.get("tam_mao", 54), cores["mao"])
    sulcos = "".join(
        f'<div style="position:absolute;z-index:3;left:{esq + i * 22}px;top:1272px;width:12px;height:4px;border-radius:2px;background:{verde};opacity:{.9 - i * .07:.2f}"></div>'
        for i in range(12))
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx}">'
             f'{foto_cheia(uri, p.get("foto_posicao", "50% 40%"), rgb, bg, 800, "filter:saturate(1.08) sepia(.12) contrast(1.04)")}{marca}'
             f'{bloco(partes, esq, 1262 - 40 - 110)}{barra(1258, esq, dest, cores["base_barra"])}{sulcos}{papel("overlay", .4)}</div>')
    return _pagina(corpo, bg)


if __name__ == "__main__":
    cfg = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for item in cfg:
        fn = globals()[item["layout"]]
        render(item["nome"], fn(item, Path(item["foto"]).resolve().as_uri()))
