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
  pauta.md           O ARQUIVO CURTO QUE SE LÊ PRIMEIRO: parceiros de hoje cruzados com o radar,
                     assuntos em alta (ganharam veículos em 3 h) e novos por seção, com
                     "na pauta desde" para quem roda de hora em hora saber o que é novo para ele
  pauta_estado.json  memória da pauta (temperatura por assunto, entrada na pauta)
  pauta_itens.json   a mesma pauta em JSON, para a triagem por IA (bot/triagem.py)
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
                 "le monde", "inglês", "espanhol", "eua", "reuters", "ap brasil", "bloomberg",
                 "ft brasil", "wsj", "mundo", "dw brasil", "washington", "cnn internacional",
                 "economist", "afp", "página/12", "clarín", "la jornada", "infobae", "telesur",
                 "prensa latina", "venezuela", "argentina", "china", "oriente", "rússia", "europa")
PESQUISA = ("fapesp", "ciência", "bori", "ibge", "ipea", "fiocruz", "inpe", "embrapa", "capes",
            "pesquisa científica", "institutos de pesquisa", "dieese", "fgv", "(dados)", "(órgãos)",
            "clima e ambiente", "sbpc")
UNIVERSIDADE = ("universidade", "unesp", "usp", "unicamp", "institutos federais", "hospitais universitários",
                "descobertas")
SECOES = [("nacional", "Brasil"), ("internacional", "Internacional"),
          ("pesquisa", "Pesquisa, ciência e institutos"), ("universidades", "Universidades")]

# Temas por palavra-chave na manchete (independem da fonte). Viram as seções C de
# América Latina e Da Terra na pauta (eixos novos pedidos pelo João em 16/10/2026).
TEMAS = {
    "america_latina": ("América Latina", {
        "argentina", "argentino", "argentinos", "milei", "venezuela", "venezuelano", "maduro", "colombia",
        "colombiano", "petro", "chile", "chileno", "boric", "kast", "mexico", "mexicano", "sheinbaum",
        "bolivia", "boliviano", "peru", "peruano", "equador", "ecuador", "cuba", "cubano", "haiti", "uruguai",
        "uruguay", "paraguai", "paraguay", "nicaragua", "honduras", "guatemala", "panama", "bukele", "caribe",
        "caracas", "bogota", "mercosul", "mercosur", "celac", "latinoamerica", "latinoamericano", "colombia",
        "argentine", "mexique", "colombie", "bresil"},
        ("america latina", "latin america", "america do sul", "south america", "el salvador", "buenos aires",
         "amerique latine", "america central")),
    "terra": ("Campo e alimento (agricultura familiar, reforma agrária)", {
        "agricultor", "agricultores", "agricultora", "agricultoras", "pronaf", "mst", "assentamento",
        "assentamentos", "assentados", "incra", "agroecologia", "agroecologico", "agroecologica", "organicos",
        "agrotoxico", "agrotoxicos", "conab", "quilombola", "quilombolas", "grilagem", "grileiros", "contag",
        "camponeses", "campones", "latifundio", "agronegocio", "ruralistas", "ruralista", "sementes",
        "pequenos produtores", "feirantes", "agrario", "agraria"},
        ("agricultura familiar", "pequeno produtor", "pequenos produtores", "reforma agraria", "sem terra",
         "plano safra", "cesta basica", "preco dos alimentos", "seguranca alimentar", "trabalho escravo",
         "terra indigena", "terras indigenas", "conflito no campo", "desenvolvimento agrario", "fome")),
    # famosos declarando voto/apoio no 2º turno (pedido do João, 16/10/2026)
    "famosos": ("Famosos e a eleição (declaração de voto, apoio)", {
        "influenciador", "influenciadora", "cantor", "cantora", "atriz", "fisiculturista", "rapper", "funkeiro"},
        ("declara voto", "declarou voto", "declara apoio", "declarou apoio", "anuncia apoio", "anunciou apoio",
         "manifesta apoio", "faz o l", "fez o l", "vota em lula", "vota em flavio", "voto em lula", "voto em flavio")),
}


def temas_do_grupo(g: dict) -> list[str]:
    texto = " ".join([g["manchete"]] + [l["titulo"] for l in g.get("links", [])])
    t = unicodedata.normalize("NFKD", texto.lower())
    t = " " + re.sub(r"[^a-z0-9 ]", " ", "".join(c for c in t if not unicodedata.combining(c))) + " "
    t = re.sub(r"\s+", " ", t)
    pal = set(t.split())
    saida = []
    for k, (_, palavras, frases) in TEMAS.items():
        por_palavra = bool(pal & palavras)
        if k == "famosos":  # famoso só conta se a manchete também falar da eleição
            por_palavra = por_palavra and bool(pal & {"lula", "flavio", "bolsonaro", "voto", "eleicao", "turno"})
        if por_palavra or any(f" {f} " in t for f in frases):
            saida.append(k)
    return saida


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
        recentes = {i["veiculo"] for i in g["itens"] if (i["quando"] or "") >= CORTE_3H}
        diretos = [i["link"] for i in g["itens"] if i["link"] and "news.google." not in i["link"]]
        saida.append({
            "sig": chave(g["itens"][0]), "manchete": g["itens"][0]["titulo"], "secao": secao,
            "veiculos_3h": len(recentes), "link_direto": diretos[0] if diretos else None,
            "_tok": sorted(g["_tok"]),
            "veiculos": veiculos, "temperatura": len(veiculos),
            "primeira_vez": min(datas) if datas else None, "ultima_vez": max(datas) if datas else None,
            "detectado": min(i["_visto"] for i in g["itens"]),
            "resumo": next((i["resumo"] for i in g["itens"] if i["resumo"]), "")[:200],
            "links": [{"veiculo": i["veiculo"], "titulo": i["titulo"], "link": i["link"]} for i in g["itens"][:8]],
        })
    for g in saida:
        g["temas"] = temas_do_grupo(g)
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


CORTE_3H = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- pauta.md
# O arquivo curto que o boletim e a CBR leem PRIMEIRO (cabe inteiro numa leitura).
#   A. o que a BFC e a Luz postaram hoje, cruzado com o radar (cobertura obrigatória)
#   B. em alta: assuntos que ganharam veículos nas últimas 3 h, mesmo que tenham começado antes
#   C. novos nas últimas 3 h, com vagas garantidas para internacional, pesquisa e universidades
# Cada linha traz "na pauta desde": quando o assunto entrou numa dessas seções pela 1ª vez.

def _link(g: dict) -> str:
    return g.get("link_direto") or g["links"][0]["link"]


def _cruzar_parceiros(grupos: list[dict], nome_arq: str = "parceiros.json") -> list[dict]:
    arq = PASTA / nome_arq
    if not arq.exists():
        return []
    dados = json.loads(arq.read_text(encoding="utf-8"))
    inicio = datetime.now(BRT).replace(hour=0, minute=0, second=0, microsecond=0)
    saida = []
    for user, v in dados.get("perfis", {}).items():
        for p in v.get("posts", []):
            t = datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%S%z")
            if t < inicio:
                continue
            tok = normalizar(p.get("legenda", "")[:300])
            melhor, nota = None, 0.0
            for g in grupos[:4000]:
                # compara com cada manchete do grupo (não com o acumulado, que casa com tudo)
                for l in g["links"]:
                    tt = normalizar(l["titulo"])
                    inter = len(tok & tt)
                    if inter < 3 or not tt:
                        continue
                    r = inter / len(tt)
                    if r >= 0.4 and (r, g["temperatura"]) > (nota, melhor["temperatura"] if melhor else -1):
                        melhor, nota = g, r
            saida.append({"perfil": user, "quando": t, "link": p.get("link"), "velocidade": p.get("velocidade"),
                          "legenda": " ".join(p.get("legenda", "").split())[:160], "grupo": melhor})
    saida.sort(key=lambda x: -(x["velocidade"] or 0))
    return saida


def _pauta(grupos: list[dict], agora_dt: datetime) -> str:
    arq_estado = PASTA / "pauta_estado.json"
    try:
        estado = json.loads(arq_estado.read_text(encoding="utf-8"))
    except Exception:
        estado = {}
    agora = agora_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    hist = estado.setdefault("temperaturas", {})
    desde = estado.setdefault("na_pauta_desde", {})

    def delta(g):
        h = hist.get(g["sig"], [])
        antigo = [t for q, t in h if q <= (agora_dt - timedelta(hours=2, minutes=40)).strftime("%Y-%m-%dT%H:%M:%SZ")]
        base = antigo[-1] if antigo else (0 if g["detectado"] >= CORTE_3H else (h[0][1] if h else g["temperatura"]))
        return g["temperatura"] - base

    parceiros = _cruzar_parceiros(grupos)
    movimentos = _cruzar_parceiros(grupos, "movimentos.json")
    # regra do João (16/10/2026): 2 veículos já bastam para o assunto entrar em alta (era 5)
    em_alta = [g for g in grupos if g["temperatura"] >= 2 and (delta(g) >= 2 or g["veiculos_3h"] >= 2)]
    em_alta.sort(key=lambda g: (-g["veiculos_3h"], -g["temperatura"]))
    em_alta = em_alta[:60]
    novos = [g for g in grupos if g["detectado"] >= CORTE_3H]
    vagas = {"nacional": 40, "internacional": 15, "pesquisa": 12, "universidades": 12}
    novos_sel = []
    for sec, n in vagas.items():
        novos_sel += [g for g in novos if g["secao"] == sec][:n]
    # eixos novos: América Latina e Da Terra (assuntos das últimas 6 h, qualquer fonte, 2+ veículos primeiro)
    corte_tema = (agora_dt - timedelta(hours=6)).strftime("%Y-%m-%dT%H:%M:%SZ")
    por_tema = {}
    for k in TEMAS:
        lista = [g for g in grupos if k in g.get("temas", []) and (g["ultima_vez"] or "") >= corte_tema]
        lista.sort(key=lambda g: (-min(g["temperatura"], 2), -(g["veiculos_3h"]), -g["temperatura"]))
        por_tema[k] = lista[:15]

    for g in [p["grupo"] for p in parceiros + movimentos if p["grupo"]] + em_alta + novos_sel + [g for l in por_tema.values() for g in l]:
        desde.setdefault(g["sig"], agora)

    itens = []  # versão estruturada da pauta, lida pela triagem (bot/triagem.py)

    def reg(secao, g, parceiro=None):
        d = {"secao": secao, "sig": g["sig"] if g else None, "parceiro": parceiro}
        if g:
            d.update({"manchete": g["manchete"], "veiculos": len(g["veiculos"]), "veiculos_3h": g["veiculos_3h"],
                      "exemplos": g["veiculos"][:4], "publicado": g["primeira_vez"],
                      "na_pauta_desde": desde.get(g["sig"]), "temas": g.get("temas", []), "link": _link(g)})
        itens.append(d)

    def lin(g, extra=""):
        v = ", ".join(g["veiculos"][:4]) + (f" +{len(g['veiculos']) - 4}" if len(g["veiculos"]) > 4 else "")
        return (f"- [{g['temperatura']}|+{g['veiculos_3h']} em 3h] {g['manchete']} — {v} · "
                f"publicado {hora(g['primeira_vez'])} · na pauta desde {hora(desde.get(g['sig']))}{extra}"
                + "".join(f" · #{t}" for t in g.get("temas", [])) + f" · {_link(g)}")

    out = [f"# Pauta do radar — {hora(agora)}", "",
           "Leia INTEIRO. [N|+M em 3h] = N veículos no total, M nas últimas 3 h. \"na pauta desde\" = quando o",
           "assunto entrou nesta lista pela 1ª vez: tudo que entrou depois da rodada anterior é candidato,",
           "mesmo que a notícia tenha começado antes. Em alta = 2+ veículos. D = América Latina, Campo e Famosos.", "",
           f"## A. O que a BFC e a Luz postaram hoje ({len(parceiros)}) — cobertura obrigatória se confirmado", ""]
    for p in parceiros:
        cab = f"- @{p['perfil']} {p['quando'].astimezone(BRT).strftime('%Hh%M')} ({int(p['velocidade'] or 0)} interações/h) {p['link']}\n  \"{p['legenda']}\""
        out.append(cab)
        out.append("  " + (lin(p["grupo"]) if p["grupo"] else "- sem correspondência no radar: procure na busca da web"))
        reg("A", p["grupo"], {"perfil": p["perfil"], "quando": p["quando"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                              "legenda": p["legenda"], "link": p["link"]})
    if movimentos:
        out += ["", f"## A2. Movimentos sociais hoje ({len(movimentos)}) — MST, MTST, CUT, UNE, Apib... (pauta fora do jornal; confirme antes)", ""]
        for p in movimentos:
            out.append(f"- @{p['perfil']} {p['quando'].astimezone(BRT).strftime('%Hh%M')} ({int(p['velocidade'] or 0)} interações/h) {p['link']}\n  \"{p['legenda']}\"")
            out.append("  " + (lin(p["grupo"]) if p["grupo"] else "- sem correspondência no radar"))
            reg("A2", p["grupo"], {"perfil": p["perfil"], "quando": p["quando"].astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                   "legenda": p["legenda"], "link": p["link"]})
    out += ["", f"## B. Em alta agora ({len(em_alta)}) — ganharam veículos nas últimas 3 h", ""]
    out += [lin(g) for g in em_alta]
    for g in em_alta:
        reg("B", g)
    nomes = dict(SECOES)
    for sec in vagas:
        lista = [g for g in novos_sel if g["secao"] == sec]
        out += ["", f"## C. Novos nas últimas 3 h — {nomes[sec]} ({len(lista)} de {len([g for g in novos if g['secao'] == sec])})", ""]
        out += [lin(g) for g in lista]
        for g in lista:
            reg("C-" + sec, g)
    for k, lista in por_tema.items():
        out += ["", f"## D. {TEMAS[k][0]} — últimas 6 h ({len(lista)})", ""]
        out += [lin(g) for g in lista]
        for g in lista:
            reg("D-" + k, g)
    (PASTA / "pauta_itens.json").write_text(json.dumps({"quando": agora, "itens": itens}, ensure_ascii=False) + "\n",
                                            encoding="utf-8")

    # memória: temperatura por assunto (8 h) e entrada na pauta (30 h)
    lim_h = (agora_dt - timedelta(hours=8)).strftime("%Y-%m-%dT%H:%M:%SZ")
    vivos = {g["sig"] for g in grupos}
    for g in grupos[:4000]:
        hist.setdefault(g["sig"], []).append([agora, g["temperatura"]])
    estado["temperaturas"] = {k: [x for x in v if x[0] >= lim_h][-10:] for k, v in hist.items() if k in vivos}
    lim_d = (agora_dt - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    estado["na_pauta_desde"] = {k: v for k, v in desde.items() if v >= lim_d}
    arq_estado.write_text(json.dumps(estado, separators=(",", ":")) + "\n", encoding="utf-8")
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
        "grupos": [{k: v for k, v in g.items() if k != "_tok"} for g in grupos]},
        ensure_ascii=False, indent=0) + "\n", encoding="utf-8")

    corte = (agora_dt - timedelta(hours=NOVOS_HORAS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    novos = [g for g in grupos if g["detectado"] >= corte]
    (PASTA / "novos.md").write_text(markdown(
        f"Radar CBR — assuntos novos nas últimas {NOVOS_HORAS} h (gerado {hora(agora)}, {len(novos)} assuntos)",
        novos, True), encoding="utf-8")
    (PASTA / "top.md").write_text(markdown(
        f"Radar CBR — os {TOP} assuntos mais quentes das últimas 26 h (gerado {hora(agora)})",
        grupos[:TOP], False), encoding="utf-8")

    (PASTA / "pauta.md").write_text(_pauta(grupos, agora_dt), encoding="utf-8")
    for g in grupos:
        g.pop("_tok", None)

    total = len(tarefas)
    (PASTA / "saude_fontes.json").write_text(json.dumps({
        "quando": agora, "fontes": total, "ok": total - len(falhas), "falhas": falhas,
        "manchetes_por_fonte": dict(sorted(por_fonte.items(), key=lambda x: x[1]))},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"radar: {len(unicos)} manchetes, {len(grupos)} assuntos, {len(novos)} novos, "
          f"{len(falhas)}/{total} fontes com falha")


if __name__ == "__main__":
    main()
