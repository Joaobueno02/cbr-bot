"""Gera o HTML das artes da CBR a partir do post.json.

Cada editoria reproduz o layout dos posts de referência (pasta referencias/).
Marcação permitida nos textos:
  *texto*    -> cor de destaque da editoria (peso do título + 100)
  ==texto==  -> marca-texto amarelo
  **texto**  -> negrito (subtítulo e corpo)
  |          -> quebra de linha forçada no título
"""
from __future__ import annotations

import html
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTS_DIR = RAIZ / "assets" / "fonts"
PAPEL = RAIZ / "assets" / "papel.jpg"

W, H = 1080, 1350

# ---------------------------------------------------------------- estilos base

def _fontface() -> str:
    f = FONTS_DIR.as_uri()
    return f"""
@font-face{{font-family:'Fraunces';src:url('{f}/fraunces-latin-full-normal.woff2') format('woff2');font-weight:100 900;font-style:normal}}
@font-face{{font-family:'Fraunces';src:url('{f}/fraunces-latin-full-italic.woff2') format('woff2');font-weight:100 900;font-style:italic}}
@font-face{{font-family:'Archivo';src:url('{f}/archivo-latin-wght-normal.woff2') format('woff2');font-weight:100 900;font-style:normal}}
@font-face{{font-family:'Archivo';src:url('{f}/archivo-latin-wght-italic.woff2') format('woff2');font-weight:100 900;font-style:italic}}
@font-face{{font-family:'Unbounded';src:url('{f}/unbounded-latin-900-normal.woff2') format('woff2');font-weight:900;font-style:normal}}
"""

ICONE = (
    '<svg style="position:absolute;z-index:6;left:80px;top:{top}px" width="34" height="34" viewBox="0 0 100 100" aria-hidden="true">'
    '<g fill="none" stroke="{cor}" stroke-linecap="round"><path d="M43 16 A32 32 0 1 1 24 57" stroke-width="10"/>'
    '<path d="M25 63 L11 80" stroke-width="12"/><path d="M38 38 L82 82" stroke-width="10"/></g>'
    '<path d="M14 40 L40 14 L52 26 L26 52 Z" fill="{cor}"/></svg>'
)

LOCKUPS = {
    "politica": (
        '<svg style="position:absolute;z-index:6;left:128px;top:50px" width="378" height="96" viewBox="0 0 550 140" role="img" aria-label="Política CBR">'
        '<defs><clipPath id="cbrclip"><text x="196" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4">CBR</text></clipPath></defs>'
        '<text x="196" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#E0302A">CBR</text>'
        '<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#FFFFFF">POLÍTICA</text>'
        '<g clip-path="url(#cbrclip)"><text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010">POLÍTICA</text></g></svg>'
    ),
    "eleicoes": (
        '<svg style="position:absolute;z-index:6;left:128px;top:50px" width="358" height="96" viewBox="0 0 520 140" role="img" aria-label="Eleições CBR 2026">'
        '<defs><clipPath id="cbrclip"><text x="182" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4">CBR</text></clipPath></defs>'
        '<text x="182" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#FED700">CBR</text>'
        '<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#FFFFFF">EL</text>'
        '<g fill="#FED700"><rect x="61" y="41" width="30" height="8" rx="4"/><rect x="61" y="53.5" width="30" height="8" rx="4"/><rect x="61" y="66" width="30" height="8" rx="4"/></g>'
        '<text x="95" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#FFFFFF">IÇÕES</text>'
        '<text x="338" y="131" font-family="Archivo, sans-serif" font-weight="600" font-size="54" fill="#FFFFFF">2026</text>'
        '<g clip-path="url(#cbrclip)"><text x="95" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010">IÇÕES</text>'
        '<text x="338" y="131" font-family="Archivo, sans-serif" font-weight="600" font-size="54" fill="#101010">2026</text></g></svg>'
    ),
    "economia": (
        '<svg style="position:absolute;z-index:6;left:128px;top:50px" width="378" height="96" viewBox="0 0 550 140" role="img" aria-label="Economia CBR">'
        '<defs><clipPath id="cbrclip"><text x="214" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4">CBR</text></clipPath></defs>'
        '<text x="214" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#1646E0">CBR</text>'
        '<g fill="#1646E0"><rect x="0" y="41" width="30" height="8" rx="4"/><rect x="0" y="53.5" width="30" height="8" rx="4"/><rect x="0" y="66" width="30" height="8" rx="4"/></g>'
        '<text x="36" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010">CONOMIA</text>'
        '<g clip-path="url(#cbrclip)"><text x="36" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#ECEAE5">CONOMIA</text></g></svg>'
    ),
    "educacao": (
        '<svg style="position:absolute;z-index:6;left:128px;top:52px" width="360" height="76" viewBox="0 0 540 114" role="img" aria-label="Educação CBR">'
        '<defs><mask id="cbrmask" maskUnits="userSpaceOnUse" x="0" y="0" width="580" height="160"><rect x="0" y="0" width="580" height="160" fill="#000000"/>'
        '<text x="196" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#FFFFFF">CBR</text></mask></defs>'
        '<text x="196" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#56622C">CBR</text>'
        '<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010"><tspan font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="49" fill="#56622C">E</tspan>DUCAÇÃO</text>'
        '<g mask="url(#cbrmask)"><text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#FFFFFF"><tspan font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="49" fill="#FFFFFF">E</tspan>DUCAÇÃO</text></g></svg>'
    ),
    # aprovado pelo João em 16/10/2026 (opção A, "Pátria Grande")
    "america_latina": (
        '<svg style="position:absolute;z-index:6;left:128px;top:50px" width="473" height="96" viewBox="0 0 690 140" role="img" aria-label="América Latina CBR">'
        '<defs><clipPath id="cbrclip"><text x="372" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4">CBR</text></clipPath></defs>'
        '<text x="372" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#FF5A1F">CBR</text>'
        '<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#FFFFFF">AMÉRICA LATINA</text>'
        '<g clip-path="url(#cbrclip)"><text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010">AMÉRICA LATINA</text></g></svg>'
    ),
    "saude": (
        '<svg style="position:absolute;z-index:6;left:128px;top:52px" width="387" height="76" viewBox="0 0 580 114" role="img" aria-label="Saúde CBR">'
        '<text x="152" y="101" font-family="Unbounded, Archivo, sans-serif" font-weight="900" font-size="118" letter-spacing="-4" fill="#087A6D">CBR</text>'
        '<text x="0" y="74" font-family="Archivo, sans-serif" font-weight="600" font-size="46" letter-spacing="1" fill="#101010">SAÚD</text>'
        '<g fill="#087A6D" stroke="#ECEAE5" stroke-width="3" paint-order="stroke"><rect x="136" y="41" width="10" height="33" rx="4"/>'
        '<rect x="136" y="41" width="30" height="9" rx="4.5"/><rect x="136" y="53" width="27" height="9" rx="4.5"/><rect x="136" y="65" width="30" height="9" rx="4.5"/></g></svg>'
    ),
}

# "da roça" (aprovada pelo João em 16/10/2026, paleta café e folha): CBR com o nome escrito à mão embaixo
def _marca_roca(c: dict) -> str:
    fonte = (FONTS_DIR / "permanent-marker-latin-400-normal.woff2").as_uri()
    risco = (f'<svg style="position:absolute;left:-6px;bottom:-18px" width="100%" height="18" viewBox="0 0 300 18" preserveAspectRatio="none">'
             f'<path d="M3 11 C 60 4, 120 15, 180 8 S 270 6, 297 10" fill="none" stroke="{c["risco"]}" stroke-width="4.5" stroke-linecap="round"/></svg>')
    return (f"<style>@font-face{{font-family:'PermanentMarker';src:url('{fonte}') format('woff2')}}</style>"
            f'<div style="position:absolute;z-index:6;left:80px;top:46px;line-height:1">'
            f'<div style="font-family:Unbounded,Archivo,sans-serif;font-weight:900;font-size:84px;letter-spacing:-4px;color:{c["destaque"]}">CBR</div>'
            f'<div id="mao" style="position:relative;display:inline-block;margin:-8px 0 0 64px;font-family:PermanentMarker,cursive;font-size:58px;'
            f'color:{c["destaque"]};{'text-shadow:0 2px 10px rgba(0,0,0,.55);' if c.get('tema') == 'escuro' else ''}transform:rotate(-5deg);transform-origin:left center;white-space:nowrap">'
            f'da roça{risco}</div></div>')


def _sulcos(c: dict, esquerda: int) -> str:
    """Da roça: linhas de plantio sob a barra."""
    return "".join(
        f'<div style="position:absolute;z-index:3;left:{esquerda + i * 22}px;top:{c["barra_y"] + 10}px;width:12px;height:4px;'
        f'border-radius:2px;background:{c["risco"]};opacity:{.9 - i * .07:.2f}"></div>' for i in range(12))


MARCA_SIMPLES = (
    '<div style="position:absolute;z-index:6;left:80px;top:60px;display:flex;align-items:center;gap:12px">'
    '<svg width="34" height="34" viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="#E3AD16" stroke-linecap="round">'
    '<path d="M43 16 A32 32 0 1 1 24 57" stroke-width="10"/><path d="M25 63 L11 80" stroke-width="12"/><path d="M38 38 L82 82" stroke-width="10"/></g>'
    '<path d="M14 40 L40 14 L52 26 L26 52 Z" fill="#E3AD16"/></svg>'
    '<span style="font-family:Unbounded,Archivo,sans-serif;font-weight:900;font-size:30px;line-height:1;letter-spacing:-1px;color:{cor}">CBR</span></div>'
)

ESCURO = dict(bg="#101010", texto="#FFFFFF", sub="#C9C6C0", rodape="#8C8984",
              barra="rgba(255,255,255,0.22)", barra_solida="#484848", barra_y=1262, papel="overlay", papel_op=0.35,
              grad_rgb="16,16,16", tema="escuro")
CLARO = dict(bg="#ECEAE5", texto="#101010", sub="#4E4B47", rodape="#4E4B47",
             barra="rgba(16,16,16,0.16)", barra_solida="#CBC9C4", barra_y=1278, papel="multiply", papel_op=0.16,
             grad_rgb="236,234,229", tema="claro")

EDITORIAS = {
    "politica": dict(ESCURO, destaque="#E0302A", icone="#E0302A", icone_top=70, marca="lockup", esquerda=80, credito="rodape", foto_min=880),
    "eleicoes": dict(ESCURO, destaque="#FED700", icone="#FED700", icone_top=70, marca="lockup", esquerda=120, credito="rodape", foto_min=780),
    "saude":    dict(CLARO, destaque="#087A6D", icone="#E3AD16", icone_top=72, marca="lockup", esquerda=120, credito="topo", foto_min=780),
    "gerais":   dict(ESCURO, destaque="#E0302A", icone=None, icone_top=60, marca="simples", esquerda=120, credito="topo", foto_min=760),
    "america_latina": dict(ESCURO, destaque="#FF5A1F", icone="#FF5A1F", icone_top=70, marca="lockup", esquerda=120, credito="rodape", foto_min=800),
    # grade branca (pedido do João, 28/10/2026): papel creme, folha escura e café
    "roca": dict(CLARO, bg="#F2EBDD", texto="#1E1610", sub="#5A4A3A", rodape="#5A4A3A", barra="rgba(30,22,16,0.16)",
                 barra_solida="#D9CCB4", papel_op=0.2, grad_rgb="242,235,221", destaque="#4F7A1C", risco="#8A6A45", icone=None, icone_top=70, marca="roca",
                 esquerda=120, credito="rodape", foto_min=800,
                 foto_filtro="filter:saturate(1.08) sepia(.12) contrast(1.04)"),
    "economia": dict(CLARO, destaque="#1646E0", icone="#E3AD16", icone_top=72, marca="lockup", esquerda=120, credito="topo", foto_min=760),
    "educacao": dict(CLARO, destaque="#56622C", icone="#E3AD16", icone_top=72, marca="lockup", esquerda=120, credito="topo", foto_min=780),
}

TITULO_MAX = {"politica": 70, "eleicoes": 58, "saude": 60, "gerais": 58, "economia": 60, "educacao": 76, "america_latina": 58, "roca": 58}

MARCA_TEXTO = "background:linear-gradient(to bottom,rgba(227,173,22,0) 58%,rgba(227,173,22,.6) 58%,rgba(227,173,22,.6) 92%,rgba(227,173,22,0) 92%)"

# ---------------------------------------------------------------- marcação

def _sem_quebra(t: str) -> str:
    """Impede quebra entre moeda e número e entre número e unidade (R$ 140 milhões)."""
    t = re.sub(r"(R\$|US\$|€) ", "\\1\u00a0", t)
    t = re.sub(r"(\d) (mil|milhões|milhão|bilhões|bilhão|trilhões|%)", "\\1\u00a0\\2", t)
    return t


def _nowrap(trecho: str) -> str:
    """Só segura numa linha destaques curtos (valores, 1-3 palavras); longos podem quebrar."""
    return ";white-space:nowrap" if len(trecho) <= 22 else ""


def marcar(texto: str, destaque: str, cor_negrito: str, titulo: bool = False, peso_destaque: int = 900,
           estilo: str = "cor", faixa: tuple = (55, 95), opacidade: float = 0.9) -> str:
    t = _sem_quebra(html.escape(texto or "", quote=False))
    t = re.sub(r"==(.+?)==", lambda m: f'<span style="{MARCA_TEXTO}">{m.group(1)}</span>', t)
    t = re.sub(r"\*\*(.+?)\*\*", lambda m: f'<b style="color:{cor_negrito};font-weight:700">{m.group(1)}</b>', t)
    if estilo == "marca_inclinada":
        # faixa de marca-texto inclinada (só a faixa; a letra continua reta), palavra por palavra
        rgb = tuple(int(destaque[i:i + 2], 16) for i in (1, 3, 5))
        cor = f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{opacidade})"
        def faixa_inclinada(m):
            palavras = m.group(1).split(" ")
            pedacos = []
            for i, w in enumerate(palavras):
                ult = i == len(palavras) - 1
                pedacos.append(f'<span class="mk{" mk-ult" if ult else ""}">{w}</span>')
            return (f'<span style="font-weight:{peso_destaque};--mk:{cor};--mk-top:{faixa[0]}%;--mk-bot:{100 - faixa[1]}%'
                    f'{_nowrap(m.group(1))}">{" ".join(pedacos)}</span>')
        t = re.sub(r"\*(.+?)\*", faixa_inclinada, t)
    elif estilo == "marca":
        # marca-texto na cor da editoria; o texto mantém a cor do título
        rgb = tuple(int(destaque[i:i + 2], 16) for i in (1, 3, 5))
        fundo = (f"background:linear-gradient(to bottom,rgba({rgb[0]},{rgb[1]},{rgb[2]},0) {faixa[0]}%,"
                 f"rgba({rgb[0]},{rgb[1]},{rgb[2]},.9) {faixa[0]}%,rgba({rgb[0]},{rgb[1]},{rgb[2]},.9) {faixa[1]}%,"
                 f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0) {faixa[1]}%);padding:0 .08em;margin:0 -.04em;"
                 f"-webkit-box-decoration-break:clone;box-decoration-break:clone")
        t = re.sub(r"\*(.+?)\*", lambda m: f'<span style="font-weight:{peso_destaque};{fundo}{_nowrap(m.group(1))}">{m.group(1)}</span>', t)
    else:
        t = re.sub(r"\*(.+?)\*", lambda m: f'<span style="font-weight:{peso_destaque};color:{destaque}{_nowrap(m.group(1))}">{m.group(1)}</span>', t)
    if titulo:
        t = t.replace("|", "<br>")
    return t


# ---------------------------------------------------------------- script de encaixe
# Diminui o título até o bloco de texto caber entre o limite superior e a barra.
# Expõe window.__fit = {ok, tamanho, topo_bloco}.
FIT_JS = """
async function encaixar(){
  await document.fonts.ready;
  const bloco=document.getElementById('bloco'), tit=document.getElementById('titulo');
  const limite=parseFloat(bloco.dataset.limite), maxT=parseFloat(tit.dataset.max), minT=parseFloat(tit.dataset.min);
  let t=maxT, ok=false;
  for(;t>=minT;t-=2){
    tit.style.fontSize=t+'px';
    // nenhuma linha do título pode estourar a largura
    const largo = tit.scrollWidth <= tit.clientWidth + 1;
    if(bloco.getBoundingClientRect().top>=limite && largo){ok=true;break;}
  }
  const topo=bloco.getBoundingClientRect().top;
  const foto=document.getElementById('foto');
  if(foto){ const minimo=parseFloat(foto.dataset.min); foto.style.height=Math.max(minimo, topo+40)+'px'; }
  const carregadas=new Set(); document.fonts.forEach(f=>{ if(f.status==='loaded') carregadas.add(f.family.replace(/["']/g,'')); });
  const fontes_ok=['Fraunces','Archivo','Unbounded'].every(n=>carregadas.has(n));
  window.__fit={ok:ok && fontes_ok, tamanho:t, topo_bloco:Math.round(topo), fontes_ok:fontes_ok, fontes:[...carregadas]};
}
encaixar();
"""


SONDA_FONTES = ('<div aria-hidden="true" style="position:absolute;left:-9999px;top:0;font-size:10px">'
                '<span style="font-family:Fraunces;font-weight:640">a</span>'
                '<span style="font-family:Archivo">a</span>'
                '<span style="font-family:Unbounded;font-weight:900">a</span></div>')


def _pagina(corpo: str, bg: str) -> str:
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<style>{_fontface()}
html,body{{margin:0;padding:0;background:{bg}}}
*{{box-sizing:border-box}}
[style*="Fraunces"]{{font-variation-settings:'SOFT' 0,'WONK' 0}}
.grade{{background-image:linear-gradient(rgba(86,98,44,.16) 1px,transparent 1px),linear-gradient(90deg,rgba(86,98,44,.16) 1px,transparent 1px);background-size:40px 40px}}
#titulo{{text-wrap:pretty}}
.mk{{position:relative;z-index:0}}
.mk::before{{content:'';position:absolute;z-index:-1;left:-.04em;right:-.21em;top:var(--mk-top);bottom:var(--mk-bot);background:var(--mk);transform:skewX(-16deg)}}
.mk-ult::before{{right:-.1em}}
</style></head><body>{corpo}{SONDA_FONTES}<script>{FIT_JS}</script></body></html>"""


def _marca(ed: str, c: dict, escala_cbr: float = 1.0) -> str:
    if c["marca"] == "simples":
        return MARCA_SIMPLES.format(cor=c["texto"])
    if c["marca"] == "roca":
        return _marca_roca(c)
    lockup = LOCKUPS[ed]
    if escala_cbr != 1.0:
        # reduz só o "CBR" grande, mantendo-o centrado na altura do nome da editoria
        tam = round(118 * escala_cbr, 1)
        base = round(101 - (1 - escala_cbr) * 118 * 0.36, 1)
        lockup = re.sub(r'y="101"( font-family="Unbounded, Archivo, sans-serif" font-weight="900") font-size="118"',
                        f'y="{base}"\\1 font-size="{tam}"', lockup)
    original = EDITORIAS[ed]["destaque"]
    if c["destaque"] != original:
        lockup = lockup.replace(original, c["destaque"])
    return ICONE.format(top=c["icone_top"], cor=c["icone"]) + lockup


def _papel(c: dict) -> str:
    return (f'<img src="{PAPEL.as_uri()}" alt="" style="position:absolute;z-index:5;left:0;top:0;width:{W}px;height:{H}px;'
            f'mix-blend-mode:{c["papel"]};opacity:{c["papel_op"]};pointer-events:none">')


def _barra(c: dict, esquerda: int, invertida: bool = False) -> str:
    y = c["barra_y"]
    largura = 1000 - esquerda - 40  # termina em x=960 (120) ou 1000 (80)
    fim = esquerda + largura
    base, ponta = (c["destaque"], c["barra_solida"]) if invertida else (c["barra"], c["destaque"])
    return (f'<div style="position:absolute;z-index:3;left:{esquerda}px;width:{largura}px;top:{y}px;height:4px;background:{base}"></div>'
            f'<div style="position:absolute;z-index:3;left:{fim-110}px;width:110px;top:{y}px;height:4px;background:{ponta}"></div>')


CORES_CONTINENTE = ["#FF5A1F", "#FED700", "#2BA84A", "#1E88E5", "#8E3FBF", "#E53935"]


def _barra_tecida(c: dict, esquerda: int, alto: int = 8) -> str:
    """América Latina: faixa de blocos coloridos, como uma barra de tecido andino."""
    larg = 1000 - esquerda - 40
    blocos, x, i = [], 0, 0
    padrao = [26, 10, 26, 10, 54, 10]
    while x < larg:
        w = min(padrao[i % len(padrao)], larg - x)
        blocos.append(f'<div style="position:absolute;left:{x}px;top:0;width:{w}px;height:{alto}px;background:{CORES_CONTINENTE[i % len(CORES_CONTINENTE)]}"></div>')
        x += w + 4
        i += 1
    return f'<div style="position:absolute;z-index:3;left:{esquerda}px;top:{c["barra_y"] - 4}px;width:{larg}px;height:{alto}px">{"".join(blocos)}</div>'


def _selo_pais(pais: str, cor: str, texto: str) -> str:
    return (f'<div><p style="margin:0 0 20px;display:inline-flex;align-items:center;gap:10px;padding:8px 16px 8px 12px;'
            f'border:2px solid {cor};border-radius:40px;font-family:Archivo,sans-serif;font-weight:700;font-size:19px;'
            f'letter-spacing:3px;text-transform:uppercase;color:{texto}">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{cor};display:inline-block"></span>{html.escape(pais)}</p></div>')


def _foto_padrao(c: dict, foto_uri: str, posicao: str, alt: str) -> str:
    g = c["grad_rgb"]
    return (f'<div id="foto" data-min="{c["foto_min"]}" style="position:absolute;z-index:1;left:0;right:0;top:0;height:{c["foto_min"]}px;overflow:hidden">'
            f'<img src="{foto_uri}" alt="{html.escape(alt)}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:{posicao}'
            f'{";" + c["foto_filtro"] if c.get("foto_filtro") else ""}">'
            f'<div style="position:absolute;left:0;right:0;top:0;height:240px;background:linear-gradient(to bottom,rgba({g},.8) 0%,rgba({g},0) 100%)"></div>'
            f'<div style="position:absolute;left:0;right:0;bottom:0;height:300px;background:linear-gradient(to bottom,rgba({g},0) 0%,rgba({g},.85) 60%,{c["bg"]} 100%)"></div>'
            f'</div>')


def _foto_educacao(c: dict, foto_uri: str, recorte: bool, posicao: str, alt: str) -> str:
    g = c["grad_rgb"]
    if recorte:
        img = (f'<img src="{foto_uri}" alt="{html.escape(alt)}" style="position:absolute;left:50%;bottom:-10px;transform:translateX(-50%);'
               f'height:700px;max-width:1140px;object-fit:contain;object-position:bottom">')
    else:
        img = (f'<div style="position:absolute;left:160px;top:250px;width:860px;height:860px;border-radius:50%;overflow:hidden">'
               f'<img src="{foto_uri}" alt="{html.escape(alt)}" style="width:100%;height:100%;object-fit:cover;object-position:{posicao}"></div>')
    return (f'<div id="foto" data-min="{c["foto_min"]}" style="position:absolute;z-index:1;left:0;right:0;top:0;height:{c["foto_min"]}px;overflow:hidden">'
            f'<div class="grade" style="position:absolute;left:0;top:0;width:1080px;height:1350px"></div>'
            f'<div style="position:absolute;left:160px;top:250px;width:860px;height:860px;border-radius:50%;background:#56622C"></div>'
            f'<div style="position:absolute;left:110px;top:200px;width:960px;height:960px;border-radius:50%;border:3px solid #E3AD16"></div>'
            f'{img}'
            f'<div style="position:absolute;left:0;right:0;bottom:0;height:150px;background:linear-gradient(to bottom,rgba({g},0) 0%,{c["bg"]} 85%)"></div>'
            f'</div>')


# Padrão visual aprovado pelo João em 15/10/2026 (post da PEC da Segurança).
# Cada editoria pode ter os seus; o post.json ainda pode sobrescrever qualquer item.
PADRAO_COMUM = {
    "titulo_max": 52, "bloco_subir": 110, "barra_invertida": True, "cbr_escala": 0.75,
    "peso_titulo": 640, "destaque_estilo": "marca_inclinada", "destaque_faixa": [55, 95],
    "sem_rodape": True,
}
PADROES = {
    "politica": {**PADRAO_COMUM, "cor_destaque": "#D0021B"},
    "gerais":   {**PADRAO_COMUM, "cor_destaque": "#D0021B"},
    "eleicoes": {**PADRAO_COMUM},
    "saude":    {**PADRAO_COMUM, "destaque_faixa": [64, 100], "destaque_opacidade": 0.45},
    "america_latina": {**PADRAO_COMUM},
    "roca": {**PADRAO_COMUM, "destaque_faixa": [64, 100], "destaque_opacidade": 0.45},
    # fundo claro (economia, educação, saúde, da roça): faixa mais baixa e translúcida, senão parece texto riscado
    "economia": {**PADRAO_COMUM, "destaque_faixa": [64, 100], "destaque_opacidade": 0.45},
    "educacao": {**PADRAO_COMUM, "destaque_faixa": [64, 100], "destaque_opacidade": 0.45},
}


def post_unico(post: dict, foto_uri: str, recorte: bool = False) -> str:
    """Arte de post único (1080x1350) no padrão da editoria."""
    # o padrão da editoria SEMPRE vence: o post.json não consegue mudar tamanho, peso, cor,
    # posição, barra ou rodapé (trava contra arte fora da identidade no meio do dia)
    padrao = PADROES.get(post["editoria"], {})
    ignoradas = sorted(k for k in post if k in padrao and post[k] != padrao[k])
    post = {**post, **padrao, "_ignoradas": ignoradas}
    ed = post["editoria"]
    c = dict(EDITORIAS[ed])
    cor_nova = post.get("cor_destaque")
    if cor_nova:
        c["destaque"] = cor_nova
        if c.get("icone") == EDITORIAS[ed]["destaque"]:
            c["icone"] = cor_nova
    esq = c["esquerda"]
    d = c["destaque"]
    posicao = post.get("foto_posicao", "50% 40%")
    alt = post.get("alt", "")

    foto = _foto_educacao(c, foto_uri, recorte, posicao, alt) if ed == "educacao" else _foto_padrao(c, foto_uri, posicao, alt)

    partes = []
    credito = post.get("credito_foto", "")
    if c["credito"] == "topo" and credito:
        partes.append(f'<p style="margin:0 0 26px;font-family:Archivo,sans-serif;font-weight:700;font-size:17px;letter-spacing:2px;text-transform:uppercase;color:{c["sub"]}">{html.escape(credito)}</p>')
    if ed == "america_latina" and post.get("pais"):
        partes.append(_selo_pais(post["pais"], d, c["texto"]))
    if post.get("chapeu"):
        tam = 60 if ed == "economia" else 66
        partes.append(f'<p style="margin:0 0 14px;font-family:Fraunces,Georgia,serif;font-weight:{min(900, int(post.get("peso_titulo", 800)) + 100)};font-size:{tam}px;line-height:1;letter-spacing:-1px;text-transform:uppercase;color:{d}">{html.escape(post["chapeu"])}</p>')
    maxt = int(post.get("titulo_max", TITULO_MAX[ed]))
    peso = int(post.get("peso_titulo", 800))
    partes.append(f'<p id="titulo" data-max="{maxt}" data-min="44" style="margin:0;font-family:Fraunces,Georgia,serif;font-weight:{peso};font-size:{maxt}px;line-height:1.05;letter-spacing:-1px;color:{c["texto"]}">'
                  f'{marcar(post["titulo"], d, c["texto"], titulo=True, peso_destaque=min(900, peso + 100), estilo=post.get("destaque_estilo", "cor"), faixa=tuple(post.get("destaque_faixa", (55, 95))),
                         opacidade=float(post.get("destaque_opacidade", 0.9)))}</p>')
    if post.get("subtitulo"):
        partes.append(f'<p style="margin:26px 0 0;font-family:Archivo,sans-serif;font-size:24px;line-height:1.42;color:{c["sub"]}">{marcar(post["subtitulo"], d, c["texto"])}</p>')

    fundo_bloco = c["barra_y"] - 40 - int(post.get("bloco_subir", 0))
    limite = 300  # o bloco nunca sobe acima disso
    bloco = (f'<div id="bloco" data-limite="{limite}" style="position:absolute;z-index:3;left:{esq}px;right:50px;'
             f'bottom:{H - fundo_bloco}px">{"".join(partes)}</div>')

    rodape = ""
    texto_rodape = "" if post.get("sem_rodape") else (post.get("rodape") or (credito if c["credito"] == "rodape" else ""))
    if texto_rodape:
        rodape = (f'<p style="position:absolute;z-index:3;left:{esq}px;right:80px;top:{c["barra_y"]+18}px;margin:0;font-family:Archivo,sans-serif;'
                  f'font-weight:700;font-size:14px;letter-spacing:2px;text-transform:uppercase;color:{c["rodape"]}">{html.escape(texto_rodape)}</p>')

    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{c["bg"]};color:{c["texto"]};font-family:Archivo,sans-serif">'
             f'{foto}{_marca(ed, c, float(post.get("cbr_escala", 1.0)))}{bloco}'
             f'{_barra_tecida(c, esq) if ed == "america_latina" else _barra(c, esq, bool(post.get("barra_invertida")))}'
             f'{_sulcos(c, esq) if ed == "roca" else ""}{rodape}{_papel(c)}</div>')
    return _pagina(corpo, c["bg"])


# ---------------------------------------------------------------- carrossel crítico
# Modelo: carrossel "33 milhões ficaram em casa". Tipos de slide:
#   capa   -> foto no topo, chamada vermelha, título grande, apoio, fonte
#   texto  -> fundo escuro ou claro, chamada + título + parágrafo
#   lista  -> chamada + título + itens numerados
#   barras -> chamada + título + barras horizontais (rotulo, valor, pct 0-100, destaque)

VERMELHO = "#D0021B"
VERMELHO_CLARO = "#A60D19"
OURO = "#E3AD16"


def _rodape_carrossel(fonte: str, escuro: bool, seg_cor: str | None = None) -> str:
    cor = "#C9C6C0" if escuro else "#4E4B47"
    linha = "rgba(255,255,255,0.3)" if escuro else "rgba(16,16,16,0.3)"
    seg = seg_cor or (OURO if escuro else VERMELHO_CLARO)
    txt = f'<p style="margin:0 0 16px;font-family:Archivo,sans-serif;font-size:18px;line-height:1.4;color:{cor}">{html.escape(fonte)}</p>' if fonte else ""
    return (f'<div style="position:absolute;z-index:4;left:80px;right:80px;bottom:56px">{txt}'
            f'<div style="position:relative;height:1px;background:{linha}"><div style="position:absolute;left:0;top:-1px;width:96px;height:3px;background:{seg}"></div></div></div>')


def slide(s: dict, foto_uri: str | None = None, editoria: str = "gerais") -> str:
    """Slide de carrossel. Gerais: modelo crítico (vermelho, CBR simples).
    Demais editorias (regra do João, 20/10/2026): mesma estética do post único da editoria
    (marca, cor de destaque e fundo), em qualquer formato."""
    tipo = s.get("tipo", "texto")
    ed = editoria if editoria in EDITORIAS else "gerais"
    propria = ed != "gerais"
    if propria:
        # todos os slides no fundo da editoria (claro em Economia/Educação/Saúde/da roça, escuro no resto)
        c = dict(EDITORIAS[ed])
        escuro = c.get("tema") == "escuro"
        bg, tx, sub, dest = c["bg"], c["texto"], c["sub"], c["destaque"]
    else:
        c = None
        escuro = s.get("fundo", "escuro") != "claro" or tipo == "capa"
        bg = "#101010" if escuro else "#ECEAE5"
        tx = "#FFFFFF" if escuro else "#101010"
        sub = "#C9C6C0" if escuro else "#4E4B47"
        dest = VERMELHO if escuro else VERMELHO_CLARO
    chamada = (f'<p style="margin:0;font-family:Archivo,sans-serif;font-weight:700;font-size:20px;letter-spacing:3px;text-transform:uppercase;color:{dest}">'
               f'{html.escape(s.get("chamada", ""))}</p>') if s.get("chamada") else ""
    maxt = 72 if tipo != "capa" else 66   # fixo: o post.json não muda o tamanho
    titulo = (f'<p id="titulo" data-max="{maxt}" data-min="44" style="margin:18px 0 0;font-family:Fraunces,Georgia,serif;font-weight:640;'
              f'font-size:{maxt}px;line-height:1.02;letter-spacing:-1.5px;color:{tx}">'
              f'{marcar(s.get("titulo", ""), dest, tx, titulo=True, peso_destaque=740, estilo="marca_inclinada", faixa=(55, 95) if escuro else (64, 100), opacidade=0.9 if escuro else 0.45)}</p>')
    apoio = (f'<p style="margin:22px 0 0;font-family:Archivo,sans-serif;font-size:26px;line-height:1.4;color:{sub}">'
             f'{marcar(s.get("texto", ""), dest, tx)}</p>') if s.get("texto") else ""

    extra = ""
    if tipo == "lista":
        itens = "".join(
            f'<div style="display:flex;gap:22px;align-items:baseline;padding:16px 0;border-top:1px solid {"rgba(255,255,255,0.22)" if escuro else "rgba(16,16,16,0.2)"}">'
            f'<span style="font-family:Archivo,sans-serif;font-weight:800;font-size:22px;color:{dest};flex:0 0 auto">{i+1:02d}</span>'
            f'<span style="font-family:Archivo,sans-serif;font-size:27px;line-height:1.32;color:{tx}">{marcar(it, dest, tx)}</span></div>'
            for i, it in enumerate(s.get("itens", [])))
        extra = f'<div style="margin-top:34px;display:flex;flex-direction:column">{itens}</div>'
    elif tipo == "barras":
        linhas = []
        for b in s.get("barras", []):
            pct = max(0.0, min(100.0, float(b["pct"])))
            larg = int(920 * pct / 100)
            cor = dest if b.get("destaque", True) else ("#FFFFFF" if escuro else "#101010")
            cor_txt = "#101010" if cor == "#FFFFFF" else "#FFFFFF"
            linhas.append(
                f'<div style="display:flex;flex-direction:column;gap:8px"><p style="margin:0;font-family:Archivo,sans-serif;font-weight:600;font-size:24px;color:{tx}">{html.escape(b["rotulo"])}</p>'
                f'<div style="width:{larg}px;min-width:140px;height:50px;background:{cor};display:flex;align-items:center;justify-content:flex-end;padding-right:16px">'
                f'<span style="font-family:Archivo,sans-serif;font-weight:800;font-size:26px;color:{cor_txt}">{html.escape(b["valor"])}</span></div></div>')
        extra = f'<div style="margin-top:44px;display:flex;flex-direction:column;gap:20px">{"".join(linhas)}</div>'

    if tipo == "capa":
        g = c["grad_rgb"] if c else "16,16,16"
        topo_op = ".8" if c else ".55"
        filtro = (c.get("foto_filtro") or "filter:contrast(1.05) saturate(.85)") if c else "filter:contrast(1.05) saturate(.85)"
        foto = (f'<div id="foto" data-min="760" style="position:absolute;left:0;right:0;top:0;height:930px;overflow:hidden">'
                f'<img src="{foto_uri}" alt="{html.escape(s.get("alt", ""))}" style="display:block;width:100%;height:100%;object-fit:cover;object-position:{s.get("foto_posicao","50% 40%")};{filtro}">'
                f'<div style="position:absolute;inset:0;background:linear-gradient(to bottom,rgba({g},{topo_op}) 0%,rgba({g},0) {"20" if c else "16"}%,rgba({g},0) 48%,rgba({g},.85) 80%,{bg} 100%)"></div></div>') if foto_uri else ""
        bloco = f'<div id="bloco" data-limite="420" style="position:absolute;z-index:2;left:80px;right:80px;bottom:200px">{chamada}{titulo}{apoio}</div>'
    else:
        foto = ""
        topo_int = 168 if not c else (230 if ed == "roca" else 190)
        bloco = f'<div id="bloco" data-limite="160" style="position:absolute;z-index:2;left:80px;right:80px;top:{topo_int}px">{chamada}{titulo}{apoio}{extra}</div>'

    papel = (f'<img src="{PAPEL.as_uri()}" alt="" style="position:absolute;z-index:5;left:0;top:0;width:{W}px;height:{H}px;'
             f'mix-blend-mode:{"overlay" if escuro else "multiply"};opacity:{0.35 if escuro else 0.55};pointer-events:none">')
    corpo = (f'<div style="width:{W}px;height:{H}px;position:relative;overflow:hidden;background:{bg};color:{tx};font-family:Archivo,sans-serif">'
             f'{foto}{bloco}{_rodape_carrossel(s.get("fonte", ""), escuro, dest if c else None)}{papel}'
             f'{_marca(ed, c, 0.75) if c else MARCA_SIMPLES.format(cor=tx)}</div>')
    pagina = _pagina(corpo, bg)
    if tipo != "capa":
        # slides internos crescem de cima pra baixo: o encaixe mede o fim do bloco contra o rodapé
        pagina = pagina.replace("bloco.getBoundingClientRect().top>=limite", "bloco.getBoundingClientRect().bottom<=1350-150")
    return pagina


def _marcar_carrossel(texto: str, dest: str, tx: str) -> str:
    # no carrossel o destaque do título é itálico na cor, como no modelo
    t = _sem_quebra(html.escape(texto or "", quote=False))
    t = re.sub(r"==(.+?)==", lambda m: f'<span style="{MARCA_TEXTO}">{m.group(1)}</span>', t)
    t = re.sub(r"\*(.+?)\*", lambda m: f'<span style="font-style:italic;font-weight:800;color:{dest}">{m.group(1)}</span>', t)
    return t.replace("|", "<br>")
