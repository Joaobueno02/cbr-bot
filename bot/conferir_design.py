"""Conferência automática do design (roda no Actions logo depois do render).

Pedido do João (16/10/2026): a revisão da estética é tão rigorosa quanto a da notícia. Este
script mede o que dá para medir na arte e grava em post.json > "design_auto"; o revisor de
design (subagente, seção 6 do manual) parte daqui e olha o resto a olho, recorte por recorte.

Mede, em cada arte-N.html renderizada:
  - título: linhas, palavra órfã na última linha, tamanho final da letra (no mínimo = texto longo demais)
  - subtítulo: linhas e palavra órfã
  - destaque *...* presente no título e se quebrou entre linhas
  - texto saindo da margem direita
  - contraste da marca do topo com o fundo da foto (marca branca sobre céu claro some)
  - foto: resolução real x tamanho exibido (ampliação = foto borrada) e nitidez
  - chapéu (até 3 palavras), tamanho do título (até ~110) e do subtítulo (até ~260)

"graves" > 0 = a arte não pode seguir; corrija (texto, foto_posicao ou foto) e renderize de novo.
Uso: python bot/conferir_design.py [--fila fila]
"""
from __future__ import annotations

import argparse
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

RAIZ = Path(__file__).resolve().parent.parent

MEDIR_JS = r"""
() => {
  function linhas(el) {
    if (!el) return null;
    const r = document.createRange(), palavras = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (w.nextNode()) {
      const n = w.currentNode, re = /\S+/g; let m;
      while ((m = re.exec(n.data))) {
        r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        const rs = r.getClientRects();
        for (const b of rs) palavras.push({p: m[0], top: b.top, left: b.left, right: b.right,
          destaque: !!n.parentElement.closest('.mk, [style*="font-weight:7"], [style*="font-weight:8"], [style*="font-weight:9"]')});
      }
    }
    const cs = getComputedStyle(el), fs = parseFloat(cs.fontSize);
    const grupos = [];
    for (const p of palavras) {
      const g = grupos.find(g => Math.abs(g.top - p.top) < fs * 0.5);
      if (g) { g.palavras.push(p.p); g.right = Math.max(g.right, p.right); g.left = Math.min(g.left, p.left); g.dest.push(p.destaque); }
      else grupos.push({top: p.top, palavras: [p.p], left: p.left, right: p.right, dest: [p.destaque]});
    }
    grupos.sort((a, b) => a.top - b.top);
    const box = el.getBoundingClientRect();
    return {fonte: fs, largura: box.width, linhas: grupos.map(g => ({texto: g.palavras.join(' '), palavras: g.palavras.length,
            largura: Math.round(g.right - g.left), destaque: g.dest}))};
  }
  const tit = document.getElementById('titulo');
  const bloco = document.getElementById('bloco');
  const ps = bloco ? [...bloco.querySelectorAll('p')] : [];
  const sub = ps.length && ps[ps.length - 1] !== tit && ps.indexOf(tit) < ps.length - 1 ? ps[ps.length - 1] : null;
  let maisDireita = 0;
  if (bloco) for (const e of bloco.querySelectorAll('*')) maisDireita = Math.max(maisDireita, e.getBoundingClientRect().right);
  const b = bloco ? bloco.getBoundingClientRect() : null;
  const ant = tit ? tit.previousElementSibling : null;
  const chap = ant && ant.tagName === 'P' && parseFloat(getComputedStyle(ant).fontSize) >= 40 ? ant : null;
  return {titulo: linhas(tit), subtitulo: linhas(sub), chapeu: linhas(chap), mais_direita: Math.round(maisDireita),
          bloco: b ? {topo: Math.round(b.top), fundo: Math.round(b.bottom)} : null};
}
"""

# esconde marca e ícone (z-index 6) para medir o fundo atrás deles
SEM_MARCA_JS = "() => { for (const e of document.querySelectorAll('[style*=\"z-index:6\"]')) e.style.visibility='hidden'; }"
ESCURAS = {"politica", "eleicoes", "saude", "gerais", "america_latina", "roca"}


def luminancia(im: Image.Image) -> tuple[float, float]:
    g = im.convert("L")
    st = ImageStat.Stat(g)
    return st.mean[0] / 255, st.stddev[0] / 255


def nitidez(foto: Path, largura_exibida: int = 1080) -> float:
    im = Image.open(foto).convert("L")
    if im.width > largura_exibida:
        im = im.resize((largura_exibida, round(im.height * largura_exibida / im.width)))
    return round(ImageStat.Stat(im.filter(ImageFilter.FIND_EDGES)).var[0], 1)


def conferir_arte(pagina, pasta: Path, n: int, post: dict, slide: dict | None) -> dict:
    html_path = pasta / f"arte-{n}.html"
    pagina.goto(html_path.as_uri())
    pagina.wait_for_function("window.__fit !== undefined", timeout=30000)
    fit = pagina.evaluate("window.__fit")
    m = pagina.evaluate(MEDIR_JS)
    graves, avisos = [], []
    t = m.get("titulo") or {}
    lin = t.get("linhas") or []
    if lin:
        ult = lin[-1]
        if len(lin) > 1 and ult["palavras"] == 1:
            graves.append(f"título com palavra órfã na última linha: \"{ult['texto']}\" — reescreva ou use | para quebrar")
        elif len(lin) > 1 and ult["largura"] < 0.22 * t["largura"]:
            avisos.append(f"última linha do título muito curta (\"{ult['texto']}\")")
        if len(lin) > 4:
            graves.append(f"título com {len(lin)} linhas (máximo 4): encurte")
        for i, l in enumerate(lin[:-1]):
            if re.search(r"(R\$|US\$|nº|n\.º|\d)$", l["texto"]) and re.match(r"^(\d|mil|milh|bilh|%)", lin[i + 1]["texto"]):
                graves.append(f"número quebrado entre linhas do título: \"{l['texto']}\" / \"{lin[i + 1]['texto']}\"")
        com_dest = [i for i, l in enumerate(lin) if any(l["destaque"])]
        if "*" not in (slide or post).get("titulo", ""):
            avisos.append("título sem destaque *...* (o padrão pede o número ou a palavra-chave destacada)")
        elif len(com_dest) > 2:
            avisos.append("destaque espalhado por mais de 2 linhas: encurte o trecho entre *")
    if fit.get("tamanho", 99) <= 46:
        graves.append(f"título no tamanho mínimo ({fit.get('tamanho')} px): texto longo demais para o padrão, encurte")
    ch = (m.get("chapeu") or {}).get("linhas") or []
    if len(ch) > 1:
        graves.append(f"chapéu quebrou em {len(ch)} linhas: use 1 a 3 palavras curtas")
    s = m.get("subtitulo") or {}
    sl = s.get("linhas") or []
    if sl:
        if len(sl) > 1 and sl[-1]["palavras"] == 1:
            avisos.append(f"subtítulo com palavra órfã: \"{sl[-1]['texto']}\"")
        if len(sl) > 4:
            graves.append(f"subtítulo com {len(sl)} linhas (máximo 4): encurte")
    if m.get("mais_direita", 0) > 1040:
        graves.append(f"texto passa da margem direita (x={m['mais_direita']})")
    if not fit.get("ok"):
        graves.append("o encaixe do texto falhou (fit.ok = false)")
    if post.get("editoria") == "roca" and slide is None:
        carregadas = pagina.evaluate("[...document.fonts].filter(f => f.status === 'loaded').map(f => f.family.replace(/[\"']/g, ''))")
        if "PermanentMarker" not in carregadas:
            graves.append("a letra manuscrita do \"da roça\" não carregou: renderize de novo")

    # contraste da marca do topo
    medidas = {"titulo_tamanho": fit.get("tamanho"), "titulo_linhas": len(lin), "subtitulo_linhas": len(sl),
               "topo_bloco": fit.get("topo_bloco")}
    ed = post.get("editoria", "")
    if slide is None:
        pagina.evaluate(SEM_MARCA_JS)
        png = pagina.screenshot(clip={"x": 80, "y": 46, "width": 480, "height": 100}, type="png")
        lum, desvio = luminancia(Image.open(io.BytesIO(png)))
        medidas["fundo_marca"] = {"luminancia": round(lum, 2), "variacao": round(desvio, 2)}
        if ed in ESCURAS and lum > 0.55:
            graves.append(f"marca do topo sobre fundo claro demais (luminância {lum:.2f}): a marca branca some; ajuste foto_posicao ou troque a foto")
        elif ed in ESCURAS and lum > 0.42:
            avisos.append(f"fundo da marca do topo meio claro (luminância {lum:.2f}): confira a leitura da marca")
        elif ed not in ESCURAS and lum < 0.35:
            graves.append(f"marca do topo sobre fundo escuro demais (luminância {lum:.2f})")
        if desvio > 0.25:
            avisos.append(f"fundo da marca muito movimentado (variação {desvio:.2f}): confira a leitura")

    # foto
    foto = pasta / ("foto.jpg" if slide is None else f"foto-{n}.jpg")
    if foto.exists():
        im = Image.open(foto)
        alt_exib = (fit.get("topo_bloco") or 800) + 40
        escala = max(1080 / im.width, alt_exib / im.height)
        medidas["foto"] = {"largura": im.width, "altura": im.height, "ampliacao": round(escala, 2), "nitidez": nitidez(foto)}
        if escala > 1.15:
            graves.append(f"foto ampliada {escala:.2f}x para caber (fica borrada): use foto maior")
        elif escala > 1.0:
            avisos.append(f"foto levemente ampliada ({escala:.2f}x)")
        if medidas["foto"]["nitidez"] < 120:
            avisos.append(f"foto com pouca nitidez (bordas {medidas['foto']['nitidez']}): confira se está borrada ou tremida")
    return {"arquivo": f"arte-{n}.jpg", "graves": graves, "avisos": avisos, "medidas": medidas}


def conferir(pasta: Path, pagina) -> None:
    arq = pasta / "post.json"
    post = json.loads(arq.read_text(encoding="utf-8"))
    rel = post.get("render") or {}
    if post.get("status") != "renderizado" or not rel.get("artes"):
        return
    if (post.get("design_auto") or {}).get("render_quando") == rel.get("quando"):
        return
    artes, graves, avisos = [], [], []
    if post.get("formato", "unico") == "unico":
        artes.append(conferir_arte(pagina, pasta, 1, post, None))
    else:
        for i, s in enumerate(post.get("slides", []), start=1):
            artes.append(conferir_arte(pagina, pasta, i, post, s))
    # texto (vale para o post inteiro)
    ch = post.get("chapeu") or ""
    if len(ch.split()) > 3:
        avisos.append(f"chapéu com {len(ch.split())} palavras (padrão: 1 a 3)")
    tit = re.sub(r"[*=|]", "", post.get("titulo") or "")
    if len(tit) > 115:
        avisos.append(f"título com {len(tit)} caracteres (padrão: até ~110)")
    sub = re.sub(r"[*=]", "", post.get("subtitulo") or "")
    if len(sub) > 265:
        avisos.append(f"subtítulo com {len(sub)} caracteres (padrão: até ~260)")
    total = sum(len(a["graves"]) for a in artes)
    post["design_auto"] = {"quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "render_quando": rel.get("quando"), "graves": total,
                           "avisos_gerais": avisos, "artes": artes}
    arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{pasta.name}: design_auto {total} grave(s), {sum(len(a['avisos']) for a in artes) + len(avisos)} aviso(s)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fila", default=str(RAIZ / "fila"))
    a = ap.parse_args()
    pastas = [p.parent for p in sorted(Path(a.fila).glob("*/post.json"))
              if any(p.parent.glob("arte-*.html"))]
    if not pastas:
        print("nada para conferir")
        return
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(args=["--allow-file-access-from-files"])
        pagina = nav.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for pasta in pastas:
            try:
                conferir(pasta, pagina)
            except Exception as e:  # a conferência nunca derruba o pipeline
                print(f"{pasta.name}: conferência falhou: {type(e).__name__}: {e}")
        nav.close()


if __name__ == "__main__":
    main()
