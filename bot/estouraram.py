"""O que estourou acima da própria página (pedido do João, 04/11/2026).

Adaptado da ideia do yt-viral (youtube-agent-skill, MIT): número bruto mede o tamanho da página,
não o assunto. Aqui cada post do benchmark é medido contra a MEDIANA DA PRÓPRIA PÁGINA NO MESMO
FORMATO (Reels contra Reels, feed contra feed), e o resultado passa pela lente da CBR:

- tira bicho, esporte, entretenimento, curiosidade e crime sem dimensão política (regras do
  bot/triagem.py mais uma lista de bichos e fofoca);
- marca a editoria provável e os termos da lente (trabalho, bolso, direito, extrema-direita...);
- cruza com o que já publicamos (registro/posts.jsonl) e com o radar (radar/atual.json):
  "já demos", "o radar tem (N veículos)" ou "não está no radar";
- mede os nossos posts do dia contra a NOSSA mediana de alcance, para ver o que rendeu acima
  do normal da CBR e não só contra páginas grandes.

Entrada: radar/benchmark.json (bot/benchmark.py). Saída: radar/estouraram.json e um resumo na tela.
Roda logo depois do benchmark no manutencao.yml; não chama API nenhuma.

Uso: python bot/estouraram.py [--min 3.0] [--top 10]
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from triagem import EDITORIAS, FORA, LENTE, SALVA_FORA, norm, parecido, tem, tokens  # noqa: E402

try:  # fórmula do gancho (a 1ª frase), com a mesma régua dos nossos títulos; ideia do ig-hook-extractor (MIT)
    from conferir_titulo import formula as formula_titulo
except Exception:  # sem o conferidor, segue sem a fórmula
    formula_titulo = lambda _t: None  # noqa: E731

BENCH = RAIZ / "radar" / "benchmark.json"
ATUAL = RAIZ / "radar" / "atual.json"
POSTS = RAIZ / "registro" / "posts.jsonl"
SAIDA = RAIZ / "radar" / "estouraram.json"
MIN_POSTS = 4  # com menos posts no formato, a mediana não diz nada

# além das regras da triagem: o que viraliza em página grande e não é pauta nossa
FORA_EXTRA = {
    "bicho": ["cachorr*", "cao ", "caes", "cadel*", "pitbull", "gato ", "gatos", "gatinh*", "felin*", "pet ", "pets",
              "filhote*", "passarinho", "papagaio", "cavalo", "vaca ", "macaco*", "capivara*"],
    "fofoca": ["ex-bbb", "namorad*", "casamento", "noivado", "separacao", "affair", "look", "maquiagem", "beleza",
               "fofoca", "polemica com", "celebridade*", "cantora", "cantor", "ator ", "atriz"],
    "historia de afeto": ["emocionante", "emociona*", "fofura", "sonho de", "realiza o sonho", "comovente", "viraliza*"],
}


def classificar(texto: str) -> dict:
    t = norm(texto)
    salva = tem(t, SALVA_FORA)
    fora = {k: v for k, v in {**FORA, **FORA_EXTRA}.items() if tem(t, v)}
    eds = sorted(((len(tem(t, v)), k) for k, v in EDITORIAS.items()), reverse=True)
    return {
        "fora": None if (salva or not fora) else sorted(fora)[0],
        "editoria": eds[0][1] if eds and eds[0][0] else None,
        "lente": tem(t, LENTE)[:6],
    }


def nossos_publicados() -> list[tuple[str, set[str]]]:
    if not POSTS.exists():
        return []
    linhas = [json.loads(l) for l in POSTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [(p.get("id", ""), tokens((p.get("titulo") or "").replace("*", ""))) for p in linhas[-80:]]


def radar_grupos() -> list[tuple[set[str], dict]]:
    try:
        a = json.loads(ATUAL.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [(tokens(g.get("manchete") or ""), g) for g in a.get("grupos", [])[:3000]]


def cruzar(texto: str, publicados, grupos) -> dict:
    tk = tokens(texto[:220])
    for pid, ptk in publicados:  # título curto contra legenda longa: 3+ palavras em comum e 40% do título
        if len(tk & ptk) >= 3 and parecido(tk, ptk, 0.4):
            return {"situacao": "ja_demos", "post": pid}
    melhor = None
    for gtk, g in grupos:
        if parecido(tk, gtk, 0.45):
            n = int(g.get("temperatura") or 0)
            if not melhor or n > int(melhor.get("temperatura") or 0):
                melhor = g
    if melhor:
        return {"situacao": "no_radar", "veiculos": int(melhor.get("temperatura") or 0),
                "manchete": (melhor.get("manchete") or "")[:140], "link": melhor.get("link_direto")}
    return {"situacao": "fora_do_radar"}


def medianas(posts: list[dict]) -> dict:
    por = {}
    for p in posts:
        if p.get("interacoes") is not None:
            por.setdefault(p.get("formato") or "?", []).append(p["interacoes"])
    geral = [v for vs in por.values() for v in vs]
    m = {f: statistics.median(vs) for f, vs in por.items() if len(vs) >= MIN_POSTS}
    if len(geral) >= MIN_POSTS:
        m["_geral"] = statistics.median(geral)
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=float, default=5.0, help="múltiplo mínimo sobre a mediana da página")
    ap.add_argument("--top", type=int, default=10)
    a = ap.parse_args()
    try:
        b = json.loads(BENCH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"sem benchmark legível: {e}")
        return 0
    publicados, grupos = nossos_publicados(), radar_grupos()

    na_lente, fora, puladas = [], [], []
    for nome, perfil in (b.get("perfis") or {}).items():
        posts = perfil.get("posts") or []
        med = medianas(posts)
        if not med:
            puladas.append(nome)
            continue
        for p in posts:
            base = med.get(p.get("formato")) or med.get("_geral")
            if not base or p.get("interacoes") is None:
                continue
            mult = p["interacoes"] / base
            if mult < a.min:
                continue
            texto = p.get("inicio_legenda") or ""
            c = classificar(texto)
            item = {"pagina": nome, "multiplo": round(mult, 1), "formato": p.get("formato"),
                    "interacoes": p["interacoes"], "por_mil_seguidores": p.get("por_mil_seguidores"),
                    "quando": p.get("quando"), "link": p.get("link"), "miniatura": p.get("miniatura"),
                    "inicio": texto[:200], **c}
            item["editoria_provavel"] = item.pop("editoria")
            item["formula"] = formula_titulo(re.split(r"(?<=[.!?])\s", texto.strip(), maxsplit=1)[0][:200])
            if c["fora"]:
                fora.append(item)
            elif not c["lente"]:  # rendeu, mas sem nada da lente da CBR (trabalho, bolso, direito, poder)
                continue
            else:
                item["cbr"] = cruzar(texto, publicados, grupos)
                na_lente.append(item)
    na_lente.sort(key=lambda x: -x["multiplo"])
    fora.sort(key=lambda x: -x["multiplo"])

    # nossos posts contra a nossa mediana de alcance
    cbr = (b.get("cbr") or {}).get("posts") or []
    alc = [p.get("reach") for p in cbr if p.get("reach") is not None]
    nosso = {"posts": len(cbr)}
    if len(alc) >= MIN_POSTS:
        m = statistics.median(alc) or 1
        lst = sorted(({"titulo": (p.get("titulo") or "").replace("*", ""), "hora": p.get("hora"),
                       "editoria": p.get("editoria"), "alcance": p.get("reach"), "envios": p.get("shares"),
                       "multiplo": round((p.get("reach") or 0) / m, 1), "link": p.get("link")} for p in cbr),
                     key=lambda x: -x["multiplo"])
        nosso.update(mediana_alcance=m, acima=[x for x in lst if x["multiplo"] >= 2][:5],
                     abaixo=[x for x in lst if x["multiplo"] <= 0.5][-5:])

    pautas = [x for x in na_lente if x["cbr"]["situacao"] != "ja_demos" and x["lente"]][:5]
    saida = {
        "quando": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "benchmark_quando": b.get("quando"),
        "criterio": f"interações / mediana da própria página no mesmo formato (mín. {MIN_POSTS} posts); "
                    f"corte {a.min}x; sinal, não prova de por que o post rendeu",
        "na_lente": na_lente[:a.top],
        "pautas_que_nao_demos": pautas,
        "fora_da_linha": fora[:5],
        "formulas_que_estouraram": dict(sorted(
            {f: sum(1 for x in na_lente if x.get("formula") == f) for f in {x.get("formula") for x in na_lente}
             if f}.items(), key=lambda kv: -kv[1])),
        "paginas_sem_dados": puladas,
        "cbr": nosso,
    }
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"estouraram ({a.min}x+ da mediana da própria página): {len(na_lente)} na lente, {len(fora)} fora da linha")
    for x in na_lente[:a.top]:
        s = x["cbr"]
        sit = {"ja_demos": f"já demos ({s.get('post')})", "fora_do_radar": "fora do radar"}.get(
            s["situacao"], f"no radar ({s.get('veiculos')} veíc.)")
        print(f"  {x['multiplo']:>5}x {x['pagina']:<20} {x['formato']:<6} {x['editoria_provavel'] or '-':<14} {sit:<28} {x['inicio'][:70]}")
    if nosso.get("acima"):
        print(f"CBR acima de 2x a nossa mediana ({nosso['mediana_alcance']}):")
        for x in nosso["acima"]:
            print(f"  {x['multiplo']:>5}x alcance {x['alcance']:<5} {x['titulo'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
