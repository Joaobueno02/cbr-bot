"""Segunda camada da triagem: o Gemini (API grátis do Google AI Studio) dá a nota editorial.

Chamado por bot/triagem.py, só sobre os candidatos que passaram nas regras (até 25 por vez).
Dá a cada um: editoria, I (impacto), V (viralizar), P (profundidade), formato, risco e motivo, com a
régua do MANUAL.md (seção 2). É SUGESTÃO: o Claude confirma, apura e revisa como sempre.

- Chave: secret GEMINI_API_KEY (aistudio.google.com, cota grátis, sem cartão). Sem chave, não faz nada.
- Modelo: variável GEMINI_MODEL, senão tenta os da lista MODELOS em ordem.
- Usa o endpoint compatível com OpenAI do Gemini. Memória por assunto (só paga de novo se o assunto
  dobrar de veículos) e teto diário próprio (TETO_DIA), abaixo da cota grátis.
- Erro ou cota estourada: devolve o erro e a triagem segue só com as regras. A chave nunca é gravada.
"""
from __future__ import annotations

import json
import os
import time

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
# 3.5-flash-lite respondeu no teste de 20/10/2026 (os outros falharam na conta nova); fica primeiro
MODELOS = [m for m in [os.environ.get("GEMINI_MODEL", "").strip(), "gemini-3.5-flash-lite", "gemini-3.8-flash",
                       "gemini-3.5-flash", "gemini-flash-latest"] if m]
LOTE = 25
TETO_DIA = 200
EDITORIAS = ["eleicoes", "politica", "economia", "educacao", "saude", "gerais", "america_latina", "roca", "fora"]

REGUA = """Você faz a triagem de pauta da CBR – Comuna Brasileira, página de notícias no Instagram com linha
socialista. Para cada assunto (manchete + quantos veículos deram), dê notas. Avalie só pela manchete:
não invente fatos.

Editorias: eleicoes (todo o processo eleitoral de 2026: TSE, pesquisas, debates, campanha, propaganda,
fake news eleitoral, famoso declarando voto), politica (Congresso, governo, STF, partidos, leis, operações
fora do processo eleitoral), economia (emprego, salário, preços, impostos, contas públicas), educacao
(universidades, escolas, ciência, MEC), saude (SUS, vacinas, hospitais), gerais (denúncias e casos que
envolvem figuras políticas fora da eleição; violência policial; meio ambiente; posts críticos),
america_latina (governos, eleições, protestos, repressão, EUA na região), roca (agricultura familiar,
reforma agrária, MST, agrotóxico, preço do alimento, fome, conflito no campo, trabalho escravo no campo).
"fora" = esporte, entretenimento, celebridade, crime comum sem ligação política, curiosidade, notícia de
outro continente sem efeito no Brasil, ou só de interesse do mercado.

Lente: pense em quem trabalha. Prioridade para direitos e condições de trabalho (salário, jornada, emprego,
aposentadoria), serviços públicos (SUS, educação pública, transporte, moradia), desigualdade e quem paga a
conta (impostos, juros, privilégios), vitórias de trabalhadores e movimentos sociais, contradições,
escândalos e ataques a direitos vindos da direita e da extrema-direita.

Notas de 0 a 3:
- I (impacto): afeta muita gente, bolso, direito, serviço público, ou o resultado da eleição.
- V (viralizar): conflito claro, número forte, contradição de político, vitória concreta de quem trabalha,
  algo que a pessoa quer mandar no grupo. Muitos veículos = assunto quente.
- P (profundidade): quanto rende para destrinchar (números, linha do tempo, quem é quem, o que muda pra
  você). 3 = 4+ blocos de informação; 2 = 3; 1 = 2; 0 = só o fato.
formato: "reels" se I=3 e V=3; "carrossel" se I+V>=5 e P>=2; senão "feed".
repetido: true se o mesmo fato está na lista de posts já publicados e não há fato novo.
risco: "" ou frase curta quando houver cuidado especial (acusação de crime sem fonte oficial; tragédia com
vítimas; menor de idade; boato; pesquisa eleitoral sem registro).
motivo: até 15 palavras, em português.
Responda só com JSON: {"avaliacoes": [{"id": 0, "editoria": "...", "I": 0, "V": 0, "P": 0,
"formato": "feed", "repetido": false, "risco": "", "motivo": "..."}]}, um item para cada id."""

CAMPOS = ("editoria", "I", "V", "P", "formato", "repetido", "risco", "motivo")


def _chamar(itens: list[dict], publicados: list[str], chave: str) -> tuple[list[dict], str, int, str]:
    linhas = []
    for i, it in enumerate(itens):
        txt = it.get("manchete") or ""
        par = it.get("parceiro")
        if par:
            txt = f"post de @{par.get('perfil')}: \"{par.get('legenda', '')}\"" + (f" | radar: {txt}" if txt else "")
        linhas.append(f"{i}. [{it.get('veiculos', 0)} veículos, +{it.get('veiculos_3h', 0)} em 3h] {txt}")
    usuario = ("Posts já publicados pela CBR:\n" + "\n".join(publicados or ["(nenhum)"]) +
               "\n\nAssuntos (avalie TODOS, usando o número como id):\n" + "\n".join(linhas))
    erro, pedidos = "", 0
    for modelo in MODELOS:
        corpo = {"model": modelo, "temperature": 0.2, "response_format": {"type": "json_object"},
                 "messages": [{"role": "system", "content": REGUA}, {"role": "user", "content": usuario}]}
        for _ in range(2):
            try:
                r = requests.post(URL, headers={"Authorization": f"Bearer {chave}"}, json=corpo, timeout=120)
                pedidos += 1
            except requests.RequestException as e:
                erro = f"{modelo}: {type(e).__name__}"
                time.sleep(5)
                continue
            if r.status_code == 200:
                try:
                    txt = (r.json()["choices"][0]["message"]["content"] or "").strip()
                    if txt.startswith("```"):
                        txt = txt.strip("`").removeprefix("json").strip()
                    return json.loads(txt)["avaliacoes"], modelo, pedidos, erro
                except Exception as e:
                    erro = f"{modelo}: resposta ilegível ({type(e).__name__})"
                    break
            try:  # só a mensagem curta do erro, nunca cabeçalhos nem a chave
                j = r.json()
                j = j[0] if isinstance(j, list) and j else j
                msg = str(j.get("error", {}).get("message", ""))[:140]
            except Exception:
                msg = ""
            erro = (erro + " | " if erro else "") + f"{modelo}: HTTP {r.status_code} {msg[:60]}".strip()
            if r.status_code in (500, 502, 503):
                time.sleep(8)
                continue
            break  # 404 (modelo não existe), 429 (cota): tenta o próximo modelo
    raise RuntimeError(erro or "sem resposta")


def avaliar(candidatos: list[dict], publicados: list[str], estado: dict, agora_iso: str) -> dict:
    """Preenche a nota da IA em cada candidato (in place). Devolve um resumo para o triagem.json."""
    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    memoria = estado.setdefault("ia", {})
    cota = estado.setdefault("cota", {})
    dia = agora_iso[:10]
    if cota.get("dia") != dia:
        cota.clear()
        cota.update(dia=dia, pedidos=0)
    info = {"ia": "gemini", "ok": bool(chave), "erro": None if chave else "sem GEMINI_API_KEY (só regras)",
            "modelo": None, "avaliados_agora": 0}
    pendentes = []
    for c in candidatos[:LOTE]:
        m = memoria.get(c["chave"])
        if m and c.get("veiculos", 0) < max(3, 2 * m.get("veiculos", 0)):
            continue
        pendentes.append(c)
    if pendentes and chave:
        if cota["pedidos"] >= TETO_DIA:
            info.update(ok=False, erro="teto diário da cota grátis (só regras até amanhã)")
        else:
            try:
                avals, modelo, n, falhas = _chamar(pendentes, publicados, chave)
                cota["pedidos"] += n
                info.update(modelo=modelo, avaliados_agora=len(pendentes), falhas_antes=falhas or None)
                for a in avals:
                    i = a.get("id")
                    if not isinstance(i, int) or not 0 <= i < len(pendentes):
                        continue
                    nota = {k: a.get(k) for k in CAMPOS}
                    for k in ("I", "V", "P"):
                        try:
                            nota[k] = max(0, min(3, int(nota[k])))
                        except (TypeError, ValueError):
                            nota[k] = 0
                    if nota["editoria"] not in EDITORIAS:
                        nota["editoria"] = None
                    nota["formato"] = nota["formato"] if nota["formato"] in ("feed", "carrossel", "reels") else "feed"
                    nota["repetido"] = bool(nota["repetido"])
                    nota.update(veiculos=pendentes[i].get("veiculos", 0), quando=agora_iso)
                    memoria[pendentes[i]["chave"]] = nota
            except Exception as e:
                cota["pedidos"] += 2
                info.update(ok=False, erro=f"Gemini: {e}"[:200])
    for c in candidatos:
        m = memoria.get(c["chave"])
        if m:
            c["ia"] = {k: m[k] for k in CAMPOS}
            c["ia"]["soma"] = m["I"] + m["V"]
    info["pedidos_hoje"] = cota["pedidos"]
    return info
