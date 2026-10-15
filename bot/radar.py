"""Radar de notícias: lê de hora em hora todos os feeds de bot/fontes.json (RSS dos veículos
e buscas do Google Notícias) e agrupa as manchetes do mesmo assunto.

Saídas:
  radar/atual.json        manchetes das últimas 26 h, agrupadas por assunto; cada grupo traz
                          quantos veículos diferentes deram a notícia ("temperatura"), a
                          primeira vez que apareceu e os links
  radar/saude_fontes.json feeds que falharam ou vieram vazios, para corrigir em fontes.json

As tarefas agendadas (boletim e CBR) leem radar/atual.json no início de cada rodada, para não
depender só da busca na web.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import mktime

import feedparser
import requests

RAIZ = Path(__file__).resolve().parent.parent
FONTES = json.loads((RAIZ / "bot" / "fontes.json").read_text(encoding="utf-8"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
JANELA = timedelta(hours=26)
PARADAS = set("a o e de do da dos das em no na nos nas um uma para por com que se ao à às "
              "após diz após sobre contra mais é foi ser vai como entre até sem pelo pela".split())


def normalizar(t: str) -> set[str]:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    return {w for w in t.split() if len(w) > 2 and w not in PARADAS}


def ler(nome: str, url: str, google: bool) -> tuple[list[dict], str | None]:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
        r.raise_for_status()
        f = feedparser.parse(r.content)
    except Exception as e:
        return [], f"{type(e).__name__}"
    if not f.entries:
        return [], "feed vazio ou inválido"
    itens, limite = [], datetime.now(timezone.utc) - JANELA
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
        itens.append({"titulo": titulo, "veiculo": veiculo, "link": e.get("link"),
                      "quando": quando.strftime("%Y-%m-%dT%H:%M:%SZ") if quando else None,
                      "resumo": re.sub("<[^>]+>", "", e.get("summary", ""))[:280]})
    return itens, None


def agrupar(itens: list[dict]) -> list[dict]:
    grupos: list[dict] = []
    for it in sorted(itens, key=lambda x: x["quando"] or ""):
        tok = normalizar(it["titulo"])
        if len(tok) < 3:
            continue
        melhor, nota = None, 0.0
        for g in grupos:
            inter = len(tok & g["_tok"])
            j = inter / max(1, min(len(tok), len(g["_tok"])))
            if inter >= 3 and j > nota:
                melhor, nota = g, j
        if melhor and nota >= 0.45:
            melhor["itens"].append(it)
            melhor["_tok"] |= tok
        else:
            grupos.append({"_tok": set(tok), "itens": [it]})
    saida = []
    for g in grupos:
        veiculos = sorted({i["veiculo"] for i in g["itens"]})
        datas = [i["quando"] for i in g["itens"] if i["quando"]]
        saida.append({
            "manchete": g["itens"][0]["titulo"], "veiculos": veiculos, "temperatura": len(veiculos),
            "primeira_vez": min(datas) if datas else None, "ultima_vez": max(datas) if datas else None,
            "links": [{"veiculo": i["veiculo"], "titulo": i["titulo"], "link": i["link"]} for i in g["itens"][:12]],
        })
    saida.sort(key=lambda g: g["ultima_vez"] or "", reverse=True)   # mais recente primeiro...
    saida.sort(key=lambda g: -g["temperatura"])                       # ...dentro da mesma temperatura
    return saida


def main() -> None:
    itens, falhas = [], {}
    for nome, url in FONTES["rss"].items():
        lido, erro = ler(nome, url, False)
        itens += lido
        if erro:
            falhas[nome] = erro
    for nome, url in FONTES["google_news"].items():
        lido, erro = ler(nome, url, True)
        itens += lido
        if erro:
            falhas[nome] = erro
    vistos, unicos = set(), []
    for it in itens:
        chave = (it["link"] or it["titulo"]).split("?")[0]
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(it)
    grupos = agrupar(unicos)
    agora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pasta = RAIZ / "radar"
    pasta.mkdir(exist_ok=True)
    (pasta / "atual.json").write_text(json.dumps({
        "quando": agora, "janela_horas": 26, "manchetes": len(unicos), "assuntos": len(grupos),
        "grupos": grupos[:400]}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    total = len(FONTES["rss"]) + len(FONTES["google_news"])
    (pasta / "saude_fontes.json").write_text(json.dumps({
        "quando": agora, "fontes": total, "ok": total - len(falhas), "falhas": falhas},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"radar: {len(unicos)} manchetes, {len(grupos)} assuntos, {len(falhas)} fontes com falha")


if __name__ == "__main__":
    main()
