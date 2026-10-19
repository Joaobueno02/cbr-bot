"""Triagem da pauta por IA (GPT pelo GitHub Models, de graça), para economizar o Claude.

Roda no radar.yml logo depois de bot/radar.py. Lê radar/pauta_itens.json (a pauta em JSON),
dá nota a cada assunto com a régua do MANUAL.md (seção 2: editoria, Impacto, Viralização,
Profundidade, "Não publique") e grava:

  radar/triagem.json         o que a rodada do Claude lê PRIMEIRO (curto): candidatos com nota
                             I + V >= 4, os itens obrigatórios (BFC/Luz/movimentos) e um resumo
                             dos descartes. Se não houver candidato, a rodada termina cedo.
  radar/triagem_estado.json  memória (assunto -> nota), para não pagar de novo pelo mesmo assunto

A triagem só PROPÕE. Apuração, texto, arte e as revisões continuam com o Claude e o manual.
Usa o GitHub Models (cota gratuita da conta do GitHub, sem cartão e sem chave nova): o próprio
GITHUB_TOKEN do Actions autentica, com "permissions: models: read" no workflow. Cota grátis dos
modelos "low" (gpt-4.1-mini, gpt-4o-mini): ~15 pedidos/min, ~150/dia, ~8 mil tokens de entrada por
pedido; por isso os lotes são pequenos e há um teto diário próprio (TETO_DIA). Estourou a cota ou deu
erro: grava "ok": false e a rodada usa a pauta.md como antes. O token nunca é gravado nem impresso.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

PASTA = Path("radar")
SAIDA = PASTA / "triagem.json"
ESTADO = PASTA / "triagem_estado.json"
POSTS = Path("registro/posts.jsonl")
URL = "https://models.github.ai/inference/chat/completions"
MODELOS = [m for m in [os.environ.get("TRIAGEM_MODELO", "").strip(), "openai/gpt-4.1-mini", "openai/gpt-4o-mini"] if m]
LOTE = 25       # cabe folgado no limite de ~8 mil tokens de entrada da cota grátis
TETO_DIA = 120  # pedidos por dia (UTC), abaixo dos ~150 da cota grátis
CORTE = 4  # I + V mínimo (manual, seção 2)

EDITORIAS = ["eleicoes", "politica", "economia", "educacao", "saude", "gerais", "america_latina", "roca", "fora"]

REGUA = """Você faz a triagem de pauta da CBR – Comuna Brasileira, página de notícias no Instagram com linha
socialista. Para cada assunto (manchete + quantos veículos deram), decida se vale post e dê notas.

Editorias: eleicoes (todo o processo eleitoral de 2026: TSE, pesquisas, debates, campanha, propaganda,
fake news eleitoral, famoso declarando voto), politica (Congresso, governo, STF, partidos, leis, operações
fora do processo eleitoral), economia (emprego, salário, preços, impostos, contas públicas), educacao
(universidades, escolas, ciência, MEC), saude (SUS, vacinas, hospitais), gerais (denúncias e casos que
envolvem figuras políticas fora da eleição; posts críticos), america_latina (governos, eleições, protestos,
repressão, EUA na região), roca (agricultura familiar, reforma agrária, MST, agrotóxico, preço do alimento,
fome, conflito no campo, trabalho escravo no campo). "fora" = esporte, celebridade, crime comum sem ligação
política, curiosidade, tragédia, ou qualquer coisa fora desses eixos.

Lente: pense em quem trabalha. Prioridade para direitos e condições de trabalho (salário, jornada, emprego,
aposentadoria), serviços públicos (SUS, educação pública, transporte, moradia), desigualdade e quem paga a
conta (impostos, juros, privilégios), vitórias de trabalhadores e movimentos sociais, contradições,
escândalos e ataques a direitos vindos da direita e da extrema-direita. O que só interessa ao mercado ou a
celebridade fica fora, a não ser que mexa no bolso de quem trabalha.

Notas de 0 a 3:
- I (impacto): afeta muita gente, bolso, direito, serviço público, ou o resultado da eleição.
- V (viralizar): conflito claro, número forte, contradição de político, vitória concreta de quem trabalha,
  algo que a pessoa quer mandar no grupo. Mais veículos = sinal de assunto quente.
- P (profundidade): quanto rende para destrinchar em partes (números, linha do tempo, quem é quem,
  o que muda pra você). 3 = 4+ blocos de informação própria; 2 = 3; 1 = 2; 0 = só o fato.
Formato: "reels" se I=3 e V=3 (ou domina o noticiário do dia); "carrossel" se I+V>=5 e P>=2; senão "feed".

Marque "repetido": true se o mesmo fato já está na lista de posts já publicados (mesmo com outra manchete)
e não há fato novo relevante.

"risco": vazio, ou uma frase curta quando houver cuidado especial: acusação de crime (precisa de fonte
oficial ou reportagem com documento, e da negativa), tragédia com vítimas, menor de idade, boato/rede social
como única base, pesquisa eleitoral (precisa de instituto, data, margem e registro). Tragédia em andamento
com vítimas, crime violento e menor identificável: I e V = 0 e editoria "fora".

"motivo": até 15 palavras, em português, dizendo por que sim ou por que não.
Não invente fatos: avalie só pela manchete. Responda só com o JSON pedido."""

ESQUEMA = {
    "name": "triagem",
    "strict": True,
    "schema": {
        "type": "object", "additionalProperties": False, "required": ["avaliacoes"],
        "properties": {"avaliacoes": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["id", "editoria", "I", "V", "P", "formato", "repetido", "risco", "motivo"],
            "properties": {
                "id": {"type": "integer"},
                "editoria": {"type": "string", "enum": EDITORIAS},
                "I": {"type": "integer"}, "V": {"type": "integer"}, "P": {"type": "integer"},
                "formato": {"type": "string", "enum": ["feed", "carrossel", "reels"]},
                "repetido": {"type": "boolean"},
                "risco": {"type": "string"},
                "motivo": {"type": "string"}}}}}},
}


PEDIDOS = [0]
FORMATO_SIMPLES = """

Formato da resposta: {"avaliacoes": [{"id": 0, "editoria": "...", "I": 0, "V": 0, "P": 0,
"formato": "feed|carrossel|reels", "repetido": false, "risco": "", "motivo": "..."}]}"""


def agora_iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def chave_item(it: dict) -> str:
    if it.get("sig"):
        return it["sig"]
    return "p:" + (it.get("parceiro") or {}).get("link", "") or it.get("manchete", "")


def ja_publicados() -> list[str]:
    if not POSTS.exists():
        return []
    linhas = [json.loads(l) for l in POSTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [f"{p.get('quando', '')[:10]} {p.get('titulo', '').replace('*', '')}" for p in linhas[-40:]]


def chamar(itens: list[dict], publicados: list[str], chave: str) -> tuple[list[dict], str]:
    linhas = []
    for i, it in enumerate(itens):
        par = it.get("parceiro")
        txt = it.get("manchete") or ""
        if par:
            txt = f"post de @{par['perfil']}: \"{par.get('legenda', '')}\"" + (f" | radar: {txt}" if txt else "")
        linhas.append(f"{i}. [{it.get('veiculos', 0)} veículos, +{it.get('veiculos_3h', 0)} em 3h] {txt}")
    usuario = ("Posts já publicados pela CBR (para marcar repetido):\n" + "\n".join(publicados or ["(nenhum)"]) +
               "\n\nAssuntos para avaliar (avalie TODOS, usando o número como id):\n" + "\n".join(linhas))
    erro = ""
    for modelo in MODELOS:
        corpo = {"model": modelo, "messages": [{"role": "system", "content": REGUA}, {"role": "user", "content": usuario}],
                 "response_format": {"type": "json_schema", "json_schema": ESQUEMA}, "temperature": 0.2}
        for tentativa in range(2):
            try:
                r = requests.post(URL, headers={"Authorization": f"Bearer {chave}", "Accept": "application/json",
                                                "X-GitHub-Api-Version": "2022-11-28"}, json=corpo, timeout=180)
                PEDIDOS[0] += 1
            except requests.RequestException as e:
                erro = f"{modelo}: {type(e).__name__}"
                time.sleep(5)
                continue
            if r.status_code == 200:
                try:
                    conteudo = (r.json()["choices"][0]["message"]["content"] or "").strip()
                    if conteudo.startswith("```"):
                        conteudo = conteudo.strip("`").removeprefix("json").strip()
                    return json.loads(conteudo)["avaliacoes"], modelo
                except Exception as e:
                    # diagnóstico curto (sem cabeçalhos, sem token): tipo e começo do corpo
                    erro = (f"{modelo}: resposta 200 ilegível ({type(e).__name__}; "
                            f"{r.headers.get('content-type', '?')}; {r.text[:120]!r})")
                    break
            # nunca grava a resposta bruta: só o código e a mensagem curta do erro
            try:
                msg = r.json().get("error", {}).get("message", "")[:160]
            except Exception:
                msg = ""
            erro = f"{modelo}: HTTP {r.status_code} {msg}"
            if r.status_code == 400 and corpo["response_format"]["type"] == "json_schema":
                # modelo sem suporte a json_schema: pede JSON simples (o esquema já está descrito na régua)
                corpo["response_format"] = {"type": "json_object"}
                corpo["messages"][0]["content"] = REGUA + FORMATO_SIMPLES
                continue
            if r.status_code == 429:
                break  # cota grátis estourada: não insiste (tenta o outro modelo, que tem cota própria)
            if r.status_code in (500, 502, 503):
                time.sleep(10)
                continue
            break
    raise RuntimeError(erro or "sem resposta")


def main() -> int:
    agora = datetime.now(timezone.utc)
    try:
        pauta = json.loads((PASTA / "pauta_itens.json").read_text(encoding="utf-8"))
    except Exception as e:
        SAIDA.write_text(json.dumps({"quando": agora_iso(agora), "ok": False, "erro": f"sem pauta_itens.json ({e})"},
                                    ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        return 0
    try:
        estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    except Exception:
        estado = {}

    # junta o mesmo assunto que aparece em várias seções
    por_chave: dict[str, dict] = {}
    for it in pauta["itens"]:
        k = chave_item(it)
        if k in por_chave:
            por_chave[k]["secoes"].append(it["secao"])
            if it.get("parceiro") and not por_chave[k].get("parceiro"):
                por_chave[k]["parceiro"] = it["parceiro"]
        else:
            por_chave[k] = dict(it, secoes=[it["secao"]], chave=k)
    itens = list(por_chave.values())

    # só paga pelo que é novo ou que esquentou muito desde a última nota
    pendentes = []
    for it in itens:
        antigo = estado.get(it["chave"])
        if not antigo or it.get("veiculos", 0) >= max(3, 2 * antigo.get("veiculos", 0)):
            pendentes.append(it)

    chave = os.environ.get("GITHUB_TOKEN", "").strip()
    hoje = agora.strftime("%Y-%m-%d")
    cota = estado.pop("_cota", {})
    usados = cota.get("pedidos", 0) if cota.get("dia") == hoje else 0
    cortados = 0
    if usados + -(-len(pendentes) // LOTE) > TETO_DIA:
        cabe = max(0, (TETO_DIA - usados) * LOTE)
        cortados, pendentes = len(pendentes) - cabe, pendentes[:cabe]
    resultado = {"quando": agora_iso(agora), "pauta_quando": pauta.get("quando"), "ok": True, "erro": None,
                 "modelo": None, "avaliados_agora": len(pendentes), "em_cache": len(itens) - len(pendentes)}
    if cortados:
        resultado.update(ok=False, erro=f"teto diário da cota grátis: {cortados} assuntos ficaram sem nota; "
                                        "leia radar/pauta.md como antes")
    if pendentes and not chave:
        resultado.update(ok=False, avaliados_agora=0, erro="sem GITHUB_TOKEN: leia radar/pauta.md como antes")
    elif pendentes:
        publicados = ja_publicados()
        try:
            for i in range(0, len(pendentes), LOTE):
                lote = pendentes[i:i + LOTE]
                avals, modelo = chamar(lote, publicados, chave)
                resultado["modelo"] = modelo
                for a in avals:
                    if 0 <= a["id"] < len(lote):
                        it = lote[a["id"]]
                        nota = {k: a[k] for k in ("editoria", "I", "V", "P", "formato", "repetido", "risco", "motivo")}
                        for k in ("I", "V", "P"):
                            nota[k] = max(0, min(3, int(nota[k])))
                        nota.update(veiculos=it.get("veiculos", 0), quando=agora_iso(agora))
                        estado[it["chave"]] = nota
        except Exception as e:
            resultado.update(ok=False, erro=f"API: {e}"[:220])

    # monta a saída curta com o que tem nota (novas + memória)
    candidatos, obrigatorios, descartes, sem_nota = [], [], [], 0
    for it in itens:
        n = estado.get(it["chave"])
        base = {"manchete": it.get("manchete"), "secoes": it["secoes"], "veiculos": it.get("veiculos", 0),
                "veiculos_3h": it.get("veiculos_3h", 0), "na_pauta_desde": it.get("na_pauta_desde"),
                "publicado": it.get("publicado"), "link": it.get("link"), "sig": it.get("sig")}
        if it.get("parceiro"):
            base["parceiro"] = it["parceiro"]
        if not n:
            sem_nota += 1
            if it.get("parceiro"):
                obrigatorios.append(base)
            continue
        base.update({k: n[k] for k in ("editoria", "I", "V", "P", "formato", "repetido", "risco", "motivo")})
        base["soma"] = n["I"] + n["V"]
        if it.get("parceiro"):
            obrigatorios.append(base)
        if base["soma"] >= CORTE and n["editoria"] != "fora" and not n["repetido"]:
            candidatos.append(base)
        else:
            descartes.append(base)
    candidatos.sort(key=lambda c: (-c["soma"], -c["P"], -c["veiculos_3h"], -c["veiculos"]))
    descartes.sort(key=lambda c: -c["veiculos"])
    resultado.update({
        "regra": "Candidatos = I+V >= 4, dentro das editorias e não repetidos. É sugestão: a apuração e as "
                 "revisões do manual continuam obrigatórias. Obrigatórios = posts da BFC/Luz/movimentos de hoje.",
        "total_assuntos": len(itens), "sem_nota": sem_nota,
        "candidatos": candidatos[:15],
        "obrigatorios": obrigatorios,
        "descartados_mais_quentes": [{"manchete": d["manchete"], "veiculos": d["veiculos"], "editoria": d["editoria"],
                                      "I": d["I"], "V": d["V"], "repetido": d["repetido"], "motivo": d["motivo"]}
                                     for d in descartes[:15]],
    })
    resultado["pedidos_hoje"] = usados + PEDIDOS[0]
    SAIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # memória de 30 h
    lim = agora_iso(agora - timedelta(hours=30))
    estado = {k: v for k, v in estado.items() if v.get("quando", "") >= lim}
    estado["_cota"] = {"dia": hoje, "pedidos": usados + PEDIDOS[0]}
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"triagem: {len(itens)} assuntos, {len(pendentes)} avaliados agora, {len(candidatos)} candidatos, "
          f"ok={resultado['ok']}" + (f" ({resultado['erro']})" if resultado["erro"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
