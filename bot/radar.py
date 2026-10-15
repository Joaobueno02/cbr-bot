"""Radar de notícias: lê todos os feeds de bot/fontes.json (RSS dos veículos, imprensa
internacional, institutos de pesquisa, portais universitários e buscas do Google Notícias)
e agrupa as manchetes do mesmo assunto.

Saídas (pasta radar/):
  atual.json         TODOS os assuntos das últimas 26 h, agrupados; cada grupo traz quantos
                     veículos diferentes deram a notícia ("temperatura"), a seção
                     (nacional/internacional/pesquisa/universidades), quando o radar viu o
                     assunto pela primeira vez ("detectado") e os links
  novos.md           resumo legível: todo assunto que o radar viu pela 1ª vez nas últimas 3 h,
                     por seção e temperatura — é o que o boletim e a CBR leem primeiro
  top.md             os 150 assuntos mais quentes das últimas 26 h
  saude_fontes.json  feeds que falharam ou vieram vazios
  vistos.json        memória do radar (link → quando foi visto pela 1ª vez), 30 h
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import mktime

import feedparser
import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "radar"
FONTES = json.loads((RAIZ / "bot" / "fontes.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
JANELA = timedelta(hours=26)
NOVOS_HORAS = 3
TOP = 150
BRT = timezone(timedelta(hours=-3))
PARADAS = set("a o e de do da dos das em no na nos nas um uma para por com que se ao à às "
              "após diz sobre contra mais é foi ser vai como entre até sem pelo pela "
              "the of to in and for on is at by with from as after says new".split())

# seção de cada fonte, pelo nome em fontes.json
INTERNACIONAL = ("nyt", "guardian", "france 24", "al jazeera", "el país", "bbc mundo", "rfi",
                 "le monde (inglês)", "inglês", "espanhol", "eua", "reuters", "ap brasil",
                 "bloomberg", "ft brasil", "wsj", "mundo", "dw brasil")
PESQUISA = ("fapesp", "ciência", "bori", "ibge", "ipea", "fiocruz", "inpe", "embrapa", "capes",
            "pesquisa científica", "institutos de pesquisa")
UNIVERSIDADE = ("universidade", "unesp", "usp", "unicamp")
SECOES = [("nacional", "Brasil"), ("internacional", "Internacional"),
          ("pesquisa", "Pesquisa, ciência e institutos"), ("universidades", "Universidades")]


def secao_da_fonte(nome: str) -> str:
    n = nome.lower()
    if any(k in n for k in UNIVERSIDADE):
        return "universidades"
    if any(k in n for k in PESQUISA):
        return "pesquisa"
    if any(k in n for k in INTERNACIONAL):
        return "internacional"
    return "nacional"


def normalizar(t: str) -> set[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return {w for w in t.split() if len(w) > 2 and w not in PARADAS}


def ler(args: tuple[str, str, bool]) -> tuple[str, list[dict], str | None]:
    nome, url, google = args
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        r.raise_for_status()
        f = feedparser.parse(r.content)
    except Exception as e:
        return nome, [], f"{type(e).__name__}"
    if not f.entries:
        return nome, [], "feed vazio ou inválido"
    itens, limite, secao = [], datetime.now(timezone.utc) - JANELA, secao_da_fonte(nome)
    for e in f.entries:
        t = e.get("published_parsed") or e.get("updated_parsed")
        quando = datetime.fromtimestamp(mktime(t), timezone.utc) if t else None
        if quando and quando < limite:
            continue
        titulo = re.sub(r"\s+", " ", e.get("title", "")).strip()
        veiculo = nome
        if google:
            # Google Notícias põe " - Veículo" no fim do título
            m = re.match(r"^(.*) - ([^-]+)$", titulo)
            if m:
                titulo, veiculo = m.group(1).strip(), m.group(2).strip()
        if not titulo:
            continue
        itens.append({"titulo": titulo, "veiculo": veiculo, "link": e.get("link"), "secao": secao,
                      "quando": quando.strftime("%Y-%m-%dT%H:%M:%SZ") if quando else None,
                      "resumo": re.sub("<[^>]+>", "", e.get("summary", ""))[:280]})
    return nome, itens, None


def agrupar(itens: list[dict]) -> list[dict]:
    grupos: list[dict] = []
    indice: dict[str, list[int]] = {}   # palavra → grupos que a contêm (evita comparar tudo com tudo)
    for it in sorted(itens, key=lambda x: x["quando"] or ""):
        tok = normalizar(it["titulo"])
        if len(tok) < 3:
            continue
        candidatos = Counter(i for w in tok for i in indice.get(w, ()))
        melhor, nota = None, 0.0
        for i, inter in candidatos.items():
            if inter < 3:
                continue
            j = inter / max(1, min(len(tok), len(grupos[i]["_tok"])))
            if j > nota:
                melhor, nota = i, j
        if melhor is not None and nota >= 0.45:
            g = grupos[melhor]
            g["itens"].append(it)
            for w in tok - g["_tok"]:
                indice.setdefault(w, []).append(melhor)
            g["_tok"] |= tok
        else:
            grupos.append({"_tok": set(tok), "itens": [it]})
            for w in tok:
                indice.setdefault(w, []).append(len(grupos) - 1)
    saida = []
    for g in grupos:
        veiculos = sorted({i["veiculo"] for i in g["itens"]})
        datas = [i["quando"] for i in g["itens"] if i["quando"]]
        secoes = Counter(i["secao"] for i in g["itens"])
        secao = max(secoes, key=lambda s: (secoes[s], s != "nacional"))
        saida.append({
            "manchete": g["itens"][0]["titulo"], "secao": secao,
            "veiculos": veiculos, "temperatura": len(veiculos),
            "primeira_vez": min(datas) if datas else None, "ultima_vez": max(datas) if datas else None,
            "detectado": min(i["_visto"] for i in g["itens"]),
            "resumo": next((i["resumo"] for i in g["itens"] if i["resumo"]), "")[:200],
            "links": [{"veiculo": i["veiculo"], "titulo": i["titulo"], "link": i["link"]} for i in g["itens"][:8]],
        })
    saida.sort(key=lambda g: g["ultima_vez"] or "", reverse=True)   # mais recente primeiro...
    saida.sort(key=lambda g: -g["temperatura"])                       # ...dentro da mesma temperatura
    return saida


def chave(it: dict) -> str:
    base = (it["link"] or it["titulo"]).split("?")[0]
    return hashlib.sha1(base.encode()).hexdigest()[:14]


def hora(iso: str | None) -> str:
    if not iso:
        return "?"
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).astimezone(BRT).strftime("%d/%m %Hh%M")


def linha(g: dict) -> str:
    v = ", ".join(g["veiculos"][:5]) + (f" +{len(g['veiculos']) - 5}" if len(g["veiculos"]) > 5 else "")
    s = f"- **[{g['temperatura']}]** {g['manchete']} — {v} · publicado {hora(g['primeira_vez'])} · {g['links'][0]['link']}"
    outros = [l["titulo"] for l in g["links"][1:3] if l["titulo"] != g["manchete"]]
    if outros:
        s += "\n  - também: " + " | ".join(outros)
    return s


def markdown(titulo: str, grupos: list[dict], por_secao: bool) -> str:
    out = [f"# {titulo}", "", "[N] = número de veículos diferentes que deram o assunto (temperatura).", ""]
    if not por_secao:
        out += [linha(g) for g in grupos]
        return "\n".join(out) + "\n"
    for sec, nome in SECOES:
        lista = [g for g in grupos if g["secao"] == sec]
        out += [f"## {nome} ({len(lista)})", ""] + [linha(g) for g in lista] + [""]
    return "\n".join(out) + "\n"


def main() -> None:
    PASTA.mkdir(exist_ok=True)
    tarefas = [(n, u, False) for n, u in FONTES["rss"].items()] + \
              [(n, u, True) for n, u in FONTES["google_news"].items()]
    itens, falhas, por_fonte = [], {}, {}
    with ThreadPoolExecutor(max_workers=16) as ex:
        for nome, lido, erro in ex.map(ler, tarefas):
            itens += lido
            por_fonte[nome] = len(lido)
            if erro:
                falhas[nome] = erro

    agora_dt = datetime.now(timezone.utc)
    agora = agora_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    arq_vistos = PASTA / "vistos.json"
    try:
        vistos = json.loads(arq_vistos.read_text(encoding="utf-8"))
    except Exception:
        vistos = {}
    primeira_rodada = not vistos

    ja, unicos = set(), []
    for it in itens:
        k = chave(it)
        if k in ja:
            continue
        ja.add(k)
        # na 1ª rodada (sem memória) vale a data de publicação, para não marcar tudo como novo
        vistos.setdefault(k, (it["quando"] or agora) if primeira_rodada else agora)
        it["_visto"] = vistos[k]
        unicos.append(it)
    limite = (agora_dt - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vistos = {k: v for k, v in vistos.items() if v >= limite or k in ja}
    arq_vistos.write_text(json.dumps(vistos, separators=(",", ":")) + "\n", encoding="utf-8")

    grupos = agrupar(unicos)
    (PASTA / "atual.json").write_text(json.dumps({
        "quando": agora, "janela_horas": 26, "manchetes": len(unicos), "assuntos": len(grupos),
        "grupos": grupos}, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")

    corte = (agora_dt - timedelta(hours=NOVOS_HORAS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    novos = [g for g in grupos if g["detectado"] >= corte]
    (PASTA / "novos.md").write_text(markdown(
        f"Radar CBR — assuntos novos nas últimas {NOVOS_HORAS} h (gerado {hora(agora)}, {len(novos)} assuntos)",
        novos, True), encoding="utf-8")
    (PASTA / "top.md").write_text(markdown(
        f"Radar CBR — os {TOP} assuntos mais quentes das últimas 26 h (gerado {hora(agora)})",
        grupos[:TOP], False), encoding="utf-8")

    total = len(tarefas)
    (PASTA / "saude_fontes.json").write_text(json.dumps({
        "quando": agora, "fontes": total, "ok": total - len(falhas), "falhas": falhas,
        "manchetes_por_fonte": dict(sorted(por_fonte.items(), key=lambda x: x[1]))},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"radar: {len(unicos)} manchetes, {len(grupos)} assuntos, {len(novos)} novos, "
          f"{len(falhas)}/{total} fontes com falha")


if __name__ == "__main__":
    main()
