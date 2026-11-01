"""Triagem da pauta por regras (sem IA, sem custo), para economizar o Claude.

Roda no radar.yml logo depois de bot/radar.py. Lê radar/pauta_itens.json (a pauta em JSON) e faz
o filtro grosso que o Claude fazia lendo a pauta.md inteira (~25 mil tokens por rodada):

  - descarta o que está fora dos eixos (esporte, entretenimento, crime comum, tragédia, curiosidade);
  - adivinha a editoria por palavras-chave (eleicoes, politica, economia, saude, educacao,
    america_latina, roca, gerais);
  - dá uma nota de CALOR (quantos veículos, quantos nas últimas 3 h) e de LENTE (palavras da linha
    da página: trabalho, salário, SUS, fome, direita, investigação...);
  - tira o que já publicamos (registro/posts.jsonl) e junta manchetes do mesmo assunto.

Depois das regras, o Gemini (bot/triagem_ia.py, API grátis) dá a nota editorial I/V/P a cada candidato.
Para os 3 melhores, já separa os veículos independentes do radar (pré-apuração, sem IA).

Grava radar/triagem.json (curto): `candidatos` (até 20, ordenados), `obrigatorios` (posts da BFC,
Luz e movimentos de hoje), `descartados_mais_quentes` (para o Claude conferir se a regra errou) e
`novos_3h` (quantos candidatos entraram na pauta nas últimas 3 h). A nota editorial final (impacto,
viralização, profundidade, formato) continua com o Claude, só sobre esses itens.
Regras ajustáveis no topo do arquivo; o dossiê das 23h aponta os erros da triagem para ajustar.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

PASTA = Path("radar")
SAIDA = PASTA / "triagem.json"
ESTADO = PASTA / "triagem_estado.json"
POSTS = Path("registro/posts.jsonl")
NOTA_MINIMA = 4  # calor + lente + editoria (+1 se a BFC/Luz/movimento deu)
MAX_CANDIDATOS = 20


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return " " + re.sub(r"[^a-z0-9%$ ]+", " ", "".join(c for c in t if not unicodedata.combining(c))) + " "


def tem(txt: str, termos) -> list[str]:
    """termos com espaço nas pontas casam palavra inteira; sem espaço, casam prefixo de palavra."""
    achados = []
    for t in termos:
        t = t.strip()
        if (f" {t} " in txt) if not t.endswith("*") else (f" {t[:-1]}" in txt):
            achados.append(t.rstrip("*"))
    return achados


# ----------------------------------------------------------------- regras (ajustáveis)
FORA = {
    "esporte": ["futebol", "flamengo", "palmeiras", "corinthians", "sao paulo fc", "vasco", "botafogo", "gremio",
                "brasileirao", "campeonato", "champions", "libertadores", "copa do mundo", "tecnico do*", "atacante",
                "zagueiro", "goleiro", "gol", "gols", "ufc", "luta*", "tenis", "ranking mundial", "challenger",
                "formula 1", "f1", "nba", "manchester", "barca", "psg", "real madrid", "cristiano ronaldo", "neymar",
                "messi", "selecao brasileira", "jogador", "jogadora", "olimpiad*", "afcon", "maratona"],
    "entretenimento": ["bbb", "a fazenda", "reality", "novela", "netflix", "streaming", "victoria s secret", "desfil*",
                       "simpsons", "filme", "serie", "album", "turne", "famosa", "famoso", "influenciadora fitness",
                       "horoscopo", "signo*", "receita de", "loteria", "mega sena", "lotofacil", "quina"],
    "crime ou tragedia": ["assassin*", "homicidio", "mata ", "matar", "matou", "morto", "mortos", "morre", "morreu",
                          "morte", "muerte", "dies", "dead", "killed", "estupr*", "agride", "agrediu", "agressao",
                          "esfaque*", "tiroteio", "baleado", "acidente", "afoga*", "desaparecid*", "sequestr*",
                          "atacada", "atacado", "incendio em base", "naufrag*", "capsized", "missing"],
    "curiosidade": ["dinossaur*", "ornitorrinco", "recorde mundial", "repulsa", "creatina", "paozinho", "patrimonio cultural",
                    "astronom*", "curiosidade"],
}
# nome de político ou termo eleitoral salva a manchete da lista FORA (ex.: deputado detido, morte de candidato)
SALVA_FORA = ["lula", "flavio", "bolsonaro", "deputado", "deputada", "senador", "senadora", "ministro", "ministra",
              "candidato", "candidata", "prefeito", "governador", "pl ", "stf", "policia federal", "pf ", "vorcaro",
              "master", "tse", "policia*", "policial", "operacao", "chacina", "indigena*", "quilombola*",
              "trabalhador*", "ice", "sem terra", "mst", "repressa*", "militar*", "milicia*"]

EDITORIAS = {
    "eleicoes": ["eleica*", "eleitora*", "segundo turno", "2o turno", "debate", "tse", "candidat*", "campanha",
                 "datafolha", "quaest", "atlasintel", "atlas intel", "ipec", "paranna", "voto", "votos", "eleitor*",
                 "urna*", "propaganda eleitoral", "declara apoio", "declarou apoio", "anuncia apoio", "apoio a lula",
                 "apoio a flavio", "election", "vote", "pesquisa eleitoral", "ato de flavio", "ato de lula", "plano de governo"],
    "politica": ["stf", "supremo", "camara", "senado", "congresso", "pec", "projeto de lei", "ministro", "ministra",
                 "planalto", "governo federal", "policia federal", "pf", "cpi", "inquerito", "deputad*", "senador*",
                 "tcu", "cgu", "ministerio publico", "governador", "prefeito", "orcamento", "decreto", "lei ",
                 "investigad*", "indiciad*", "operacao", "lavagem", "corrupca*", "vorcaro", "master"],
    "economia": ["salario*", "salario minimo", "inflacao", "ipca", "juros", "selic", "imposto*", "isencao", "emprego*",
                 "desemprego", "demissa*", "demite", "trabalhador*", "greve", "preco*", "gasolina", "diesel", "conta de luz",
                 "bolsa familia", "inss", "aposentad*", "previdencia", "6x1", "jornada", "fgts", "cesta basica", "aluguel",
                 "banco central", "divida", "fiscal", "tarifa*", "pib", "renda", "bilionari*", "taxacao", "congelar"],
    "saude": ["sus", "saude", "anvisa", "vacina*", "hospita*", "dengue", "hiv", "cancer", "medicamento*", "remedio*",
              "farmacia popular", "mais medicos", "plano de saude", "ans", "fiocruz", "butantan", "epidemia", "surto"],
    "educacao": ["universidade*", "enem", "mec", "escola*", "professor*", "capes", "cnpq", "fundeb", "merenda",
                 "licenciatura", "estudante*", "ensino", "instituto federal", "ciencia", "pesquisador*", "bolsas de",
                 "unifesp", "usp", "unicamp", "unesp", "ufrj", "ufmg", "ufscar", "creche*"],
    "roca": ["agricultura familiar", "reforma agraria", "mst", "assentament*", "agrotoxic*", "agroecolog*", "plano safra",
             "safra", "fome", "cesta basica", "preco dos alimentos", "alimento*", "granja", "incra", "quilombo*",
             "terra indigena", "trabalho escravo", "grilage*", "agronegocio", "ruralista*", "pronaf", "conab"],
    "gerais": ["incendio*", "queimada*", "desmatamento", "seca", "enchente*", "clima", "ambienta*", "meio ambiente",
               "racismo", "feminicidio", "violencia policial", "chacina", "milicia*", "fake news", "desinformacao"],
    "america_latina": ["cuba", "cuban*", "castro", "mexic*", "venezuel*", "maduro", "argentin*", "milei", "colombi*",
                       "petro", "chile*", "kast", "boric", "bolivia*", "peru", "perua*", "equador", "ecuador", "haiti",
                       "uruguai", "paraguai", "nicaragua", "honduras", "guatemala", "el salvador", "bukele", "sheinbaum"],
}
# outros países: sem citar o Brasil nem a América Latina, fica de fora
OUTROS_PAISES = ["israel", "eua", "estados unidos", "russia", "ucrania", "china", "gaza", "cisjordania", "canada",
                 "portugal", "franca", "alemanha", "reino unido", "japao", "india", "ira", "iran", "quenia", "arabia",
                 "qatar", "houthi*", "netanyahu", "zelensky", "putin", "europa", "otan", "noruega", "siria", "libano"]
# assunto estrangeiro só entra se for América Latina (tema do radar) ou citar o Brasil
BRASIL = ["brasil", "brazil", "brasileir*", "lula", "bolsonaro", "flavio", "sao paulo", "rio de janeiro", "brasilia",
          "amazonia", "amazon"]
ESTRANGEIRO = [" the ", " of ", " and ", " to ", " el ", " la ", " los ", " las ", " del ", " y ", " una "]

LENTE = ["trabalhador*", "salario*", "greve", "direito*", "6x1", "jornada", "aposentad*", "inss", "bolsa familia", "sus",
         "fome", "cesta basica", "moradia", "despejo*", "privatiza*", "bilionari*", "super ricos", "isencao", "taxacao",
         "corte*", "congel*", "demissa*", "desemprego", "bolsonar*", "flavio", "extrema direita", "golpe*", "pl ",
         "investigad*", "inquerito", "lavagem", "corrupca*", "detido", "preso", "mst", "mtst", "indigena*", "quilombola*",
         "desmatamento", "incendio*", "queimada*", "ice", "trump", "milei", "imperialis*", "repressa*", "protesto*",
         "racismo", "feminicidio", "violencia policial", "chacina", "agrotoxic*", "vorcaro", "master", "propina",
         "orcamento", "educacao publica", "universidade publica", "piso", "precariza*", "uber", "aplicativo*",
         "lucro*", "banco*", "juros", "aluguel", "tarifa zero", "passe livre", "transporte publico", "merenda",
         "fundeb", "auxilio*", "incentivo", "bolsas", "piso salarial", "vagas", "cotas", "reajuste", "dispara",
         "mais caro", "mais cara", "encarece", "rombo", "isencao", "conta de luz", "saneamento", "favela*",
         "periferia*", "violencia policial", "operacao policial", "letalidade"]

STOP = set("a o os as de da do das dos e em no na nos nas um uma para por com que se ao aos sobre apos diz "
           "the of and to in on for la el los las del y en".split())


def tokens(t: str) -> set[str]:
    return {(w[:-1] if len(w) > 4 and w.endswith("s") else w) for w in norm(t).split() if len(w) > 2 and w not in STOP}


def parecido(a: set[str], b: set[str], corte: float = 0.5) -> bool:
    return bool(a and b) and len(a & b) / min(len(a), len(b)) >= corte


def ja_publicados() -> list[tuple[str, set[str]]]:
    if not POSTS.exists():
        return []
    linhas = [json.loads(l) for l in POSTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [(p.get("id", ""), tokens(p.get("titulo", "").replace("*", ""))) for p in linhas[-60:]]


def avaliar(it: dict, publicados) -> dict:
    texto = it.get("manchete") or ""
    par = it.get("parceiro")
    if par:
        texto += " " + (par.get("legenda") or "")
    t = norm(texto)
    temas = it.get("temas") or []
    v, v3 = it.get("veiculos", 0) or 0, it.get("veiculos_3h", 0) or 0

    salva = tem(t, SALVA_FORA)
    for motivo, termos in FORA.items():
        achou = tem(t, termos)
        if achou and not salva:
            return {"ok": False, "motivo": f"fora: {motivo} ({achou[0]})"}

    eds = {ed: len(tem(t, termos)) for ed, termos in EDITORIAS.items()}
    if "america_latina" in temas:
        eds["america_latina"] = max(3, eds["america_latina"])
    if "terra" in temas:
        eds["roca"] = eds.get("roca", 0) + 2
    if "famosos" in temas:
        eds["eleicoes"] = eds.get("eleicoes", 0) + 2
    editoria = max(eds, key=lambda k: eds[k]) if max(eds.values()) > 0 else None
    estrangeiro = (sum(1 for w in ESTRANGEIRO if w in t) >= 2 or str(it.get("secao", "")).startswith("C-internacional")
                   or bool(tem(t, OUTROS_PAISES)))
    if estrangeiro and not eds["america_latina"] and not tem(t, BRASIL):
        return {"ok": False, "motivo": "fora: internacional sem Brasil nem América Latina"}
    if not editoria:
        if par:
            editoria = "gerais"
        else:
            return {"ok": False, "motivo": "sem editoria"}
    if editoria == "politica" and eds.get("eleicoes", 0) >= 1 and tem(t, ["lula", "flavio", "candidat*", "turno"]):
        editoria = "eleicoes"

    calor = 0 if v < 2 else 1 if v < 5 else 2 if v < 15 else 3
    if v3 >= 3:
        calor = min(3, calor + 1)
    lente_hits = tem(t, LENTE)
    lente = min(3, len(lente_hits))
    nota = calor + lente + min(2, eds[editoria] if editoria in eds else 0) + (1 if par else 0)

    tok = tokens(it.get("manchete") or texto)
    for pid, ptok in publicados:
        if parecido(tok, ptok, 0.6):
            return {"ok": False, "motivo": f"repetido ({pid})", "editoria": editoria, "nota": nota}
    if nota < (NOTA_MINIMA - 1 if lente_hits else NOTA_MINIMA) and not par:
        return {"ok": False, "motivo": f"fraco (calor {calor}, lente {lente})", "editoria": editoria, "nota": nota}
    return {"ok": True, "editoria": editoria, "nota": nota, "calor": calor, "lente": lente_hits[:4]}


def main() -> int:
    agora = datetime.now(timezone.utc)
    iso = agora.strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        pauta = json.loads((PASTA / "pauta_itens.json").read_text(encoding="utf-8"))
    except Exception as e:
        SAIDA.write_text(json.dumps({"quando": iso, "ok": False, "erro": f"sem pauta_itens.json ({e})"},
                                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return 0
    publicados = ja_publicados()
    try:
        estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        estado = {}
    vistos = estado.setdefault("vistos", {})  # assunto -> [quando entrou, veículos naquele momento]

    # junta o mesmo assunto que aparece em várias seções
    por_chave: dict[str, dict] = {}
    for it in pauta["itens"]:
        k = it.get("sig") or ("p:" + ((it.get("parceiro") or {}).get("link") or ""))
        if k in por_chave:
            por_chave[k]["secoes"].append(it["secao"])
            if it.get("parceiro") and not por_chave[k].get("parceiro"):
                por_chave[k]["parceiro"] = it["parceiro"]
        else:
            por_chave[k] = dict(it, secoes=[it["secao"]])

    candidatos, descartes, obrigatorios = [], [], []
    for it in por_chave.values():
        r = avaliar(it, publicados)
        base = {"manchete": it.get("manchete"), "secoes": it["secoes"], "veiculos": it.get("veiculos", 0),
                "veiculos_3h": it.get("veiculos_3h", 0), "na_pauta_desde": it.get("na_pauta_desde"),
                "link": it.get("link"), "editoria": r.get("editoria"), "nota": r.get("nota")}
        if it.get("parceiro"):
            p = it["parceiro"]
            obrigatorios.append(dict(base, parceiro={k: p.get(k) for k in ("perfil", "quando", "legenda", "link")},
                                     triagem=("candidato" if r["ok"] else r["motivo"])))
        chave = it.get("sig") or base["link"] or base["manchete"]
        v0 = vistos.setdefault(chave, [iso, base["veiculos"]])[1]
        base["esquentou"] = base["veiculos"] >= max(v0 + 3, 2 * v0)
        if r["ok"]:
            candidatos.append(dict(base, chave=chave, sig=it.get("sig"), parceiro=it.get("parceiro"),
                                   lente=r["lente"], _tok=tokens(it.get("manchete") or "")))
        else:
            descartes.append(dict(base, motivo=r["motivo"]))

    # junta manchetes do mesmo assunto entre os candidatos (ex.: 3 versões da mesma notícia)
    candidatos.sort(key=lambda c: (-c["nota"], -c["veiculos_3h"], -c["veiculos"]))
    unicos = []
    for c in candidatos:
        irmao = next((u for u in unicos if parecido(c["_tok"], u["_tok"], 0.5)), None)
        if irmao:
            irmao["outras_manchetes"] = irmao.get("outras_manchetes", 0) + 1
        else:
            unicos.append(c)
    for c in unicos:
        c.pop("_tok", None)

    # 2ª camada: nota editorial do Gemini (grátis); sem chave ou com erro, fica só a regra
    import triagem_ia
    titulos = [f"{pid}" for pid, _ in publicados]
    try:
        titulos = [json.loads(l).get("titulo", "").replace("*", "")
                   for l in POSTS.read_text(encoding="utf-8").splitlines()[-40:] if l.strip()]
    except Exception:
        pass
    info_ia = triagem_ia.avaliar(unicos, titulos, estado, iso)

    def ordem(c):
        ia = c.get("ia")
        fora = ia and (ia["editoria"] == "fora" or ia["repetido"])
        return (bool(fora), -(ia["soma"] if ia else c["nota"] - 1), -(ia["P"] if ia else 0), -c["veiculos_3h"],
                -c["veiculos"])
    unicos.sort(key=ordem)
    rebaixados = [c for c in unicos if c.get("ia") and (c["ia"]["editoria"] == "fora" or c["ia"]["repetido"]
                                                         or c["ia"]["soma"] < 4)]
    unicos = [c for c in unicos if c not in rebaixados]

    # pré-apuração (sem IA): veículos independentes do radar para os 3 melhores
    pre = []
    try:
        grupos = {g["sig"]: g for g in json.loads((PASTA / "atual.json").read_text(encoding="utf-8"))["grupos"]}
        agreg = ("msn", "yahoo", "terra", "bol", "uol notícias", "istoé dinheiro", "google")
        for c in unicos[:3]:
            g = grupos.get(c.get("sig"))
            if not g:
                continue
            versoes, ja = [], set()
            for l in g.get("links", []):
                v = l["veiculo"]
                if v in ja or any(x in v.lower() for x in agreg):
                    continue
                ja.add(v)
                versoes.append({"veiculo": v, "titulo": l["titulo"], "link": l["link"]})
            pre.append({"manchete": c["manchete"], "veiculos_independentes": versoes[:10]})
    except Exception:
        pass
    (PASTA / "pre_apuracao.json").write_text(json.dumps({"quando": iso, "assuntos": pre}, ensure_ascii=False,
                                                        indent=1) + "\n", encoding="utf-8")
    for c in unicos + rebaixados:
        for k in ("chave", "sig", "parceiro"):
            c.pop(k, None)

    corte3h = (agora - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
    quentes = sorted([d for d in descartes if not d["motivo"].startswith("fraco")], key=lambda d: -d["veiculos"])
    resultado = {
        "quando": iso, "pauta_quando": pauta.get("quando"), "ok": True, "erro": None,
        "metodo": "regras + gemini" if info_ia["ok"] else "regras", "ia": info_ia,
        "regra": "1) Regras (sem IA) tiram o que está fora dos eixos e o repetido; 2) o Gemini dá a nota I/V/P em "
                 "`ia` (sugestão, avalia só a manchete); 3) a nota final é do Claude. `rebaixados` = o Gemini achou "
                 "fraco/fora/repetido; `descartados_mais_quentes` = a regra tirou. Os dois erram: confira. "
                 "`esquentou` = ganhou muitos veículos desde que entrou. Obrigatórios = BFC/Luz/movimentos de hoje. "
                 "Pré-apuração dos 3 primeiros em radar/pre_apuracao.json.",
        "total_assuntos": len(por_chave),
        "novos_3h": sum(1 for c in unicos[:MAX_CANDIDATOS] if (c.get("na_pauta_desde") or "") >= corte3h),
        "esquentaram": sum(1 for c in unicos[:MAX_CANDIDATOS] if c.get("esquentou")),
        "candidatos": unicos[:MAX_CANDIDATOS],
        "rebaixados": [{k: c.get(k) for k in ("manchete", "veiculos", "veiculos_3h", "na_pauta_desde", "esquentou", "ia")}
                       for c in rebaixados[:10]],
        "obrigatorios": obrigatorios,
        "descartados_mais_quentes": [{k: d[k] for k in ("manchete", "veiculos", "veiculos_3h", "motivo")}
                                     for d in quentes[:10]],
    }
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    lim = (agora - timedelta(hours=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    estado["vistos"] = {k: v for k, v in vistos.items() if v[0] >= lim}
    estado["ia"] = {k: v for k, v in estado.get("ia", {}).items() if v.get("quando", "") >= lim}
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"triagem: {len(por_chave)} assuntos, {len(unicos)} candidatos ({resultado['novos_3h']} novos em 3 h), "
          f"{len(obrigatorios)} obrigatórios; IA: {info_ia['ok']} {info_ia.get('erro') or ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
