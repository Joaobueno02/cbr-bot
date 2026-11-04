"""Comentários dos nossos posts (pedido do João, 04/11/2026; adaptado do instagram-skills, MIT).

No Instagram, a primeira hora decide o alcance e a conversa conta: comentário respondido puxa outros.
E numa página política, o comentário é por onde chega a acusação de erro ("isso é fake", "cadê a
fonte"), que o protocolo de crise do MANUAL (seção 11) precisa ver cedo.

Este módulo, chamado pelo bot/alertas.py (no máximo a cada 30 min), lê os comentários dos posts das
últimas 24 h e separa em:
- contestacao: diz que o post está errado, é fake ou pede fonte -> alerta no celular do João na hora;
- pergunta: dúvida de verdade sobre o assunto -> vai para a rodada e para o dossiê (pauta e resposta);
- hostil: ofensa ou provocação -> só conta, sem texto (não se discute nos comentários);
- outro: elogio, marcação, emoji -> só conta.

Grava radar/comentarios.json. O repositório é público: o arquivo guarda o id do comentário, a classe,
a hora e, só em contestação e pergunta, até 160 caracteres do texto, para a rodada conferir. Nunca
guarda o @ de quem comentou. Não responde nada: responder é ação pública e depende do João.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
POSTS = RAIZ / "registro" / "posts.jsonl"
SAIDA = RAIZ / "radar" / "comentarios.json"
JANELA_H = 24
MAX_POSTS = 14
INTERVALO_MIN = 30

CONTESTA = ["fake", "mentira", "mentiroso", "mentirosa", "falso", "falsa", "erra", "erro", "nao e verdade",
            "fonte?", "cade a fonte", "qual a fonte", "qual fonte", "sem fonte", "desinforma", "distorc",
            "fora de contexto", "corrige", "correcao", "nao foi isso", "nao disse isso", "manipula", "fake news",
            "inventaram", "inventou", "boato"]
HOSTIL = ["lixo", "esquerdopata", "comunista safado", "petralha", "vagabund", "idiota", "imbecil", "burro",
          "otario", "otaria", "vai pra cuba", "vai pra venezuela", "mamadeira", "bandido", "ladrao", "lula ladrao",
          "arrombad", "fdp", "porra", "caralho", "merda"]
PERGUNTA = re.compile(r"\?\s*$|^(como|quando|onde|quanto|quantos|quantas|qual|quais|quem|por que|porque|pq|"
                      r"e se|vale pra|vale para|tem direito|isso vale)\b")


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return " ".join("".join(c for c in t if not unicodedata.combining(c)).split())


def tem(t: str, termos: list[str]) -> bool:
    """termo casa no começo de palavra ("erro" pega "erro" e "errou", não "ferro" nem "terror")."""
    return any(re.search(r"(^|[^a-z0-9])" + re.escape(w), t) for w in termos)


def classificar(texto: str) -> str:
    t = norm(texto)
    if tem(t, HOSTIL):
        return "hostil"
    if tem(t, CONTESTA):
        return "contestacao"
    if PERGUNTA.search(t) and len(t) > 8:
        return "pergunta"
    return "outro"


def posts_recentes(agora: datetime) -> list[dict]:
    if not POSTS.exists():
        return []
    corte = (agora - timedelta(hours=JANELA_H)).strftime("%Y-%m-%dT%H:%M:%SZ")
    linhas = [json.loads(l) for l in POSTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [p for p in linhas if p.get("media_id") and (p.get("quando") or "") >= corte][-MAX_POSTS:]


def conferir(estado: dict, chamar, enviar, ig_user: str | None = None) -> None:
    agora = datetime.now(timezone.utc)
    ultima = estado.get("comentarios_ultima")
    if ultima and agora - datetime.strptime(ultima, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) \
            < timedelta(minutes=INTERVALO_MIN):
        return
    estado["comentarios_ultima"] = agora.strftime("%Y-%m-%dT%H:%M:%SZ")
    vistos = set(estado.get("comentarios_vistos", []))
    saida = {"quando": estado["comentarios_ultima"], "janela_h": JANELA_H, "posts": [], "erros": []}
    for p in posts_recentes(agora):
        try:
            dados = chamar("GET", f"{p['media_id']}/comments",
                           fields="id,text,timestamp,like_count,from", limit=50).get("data", [])
        except Exception as e:  # a leitura de comentários nunca derruba os alertas
            saida["erros"].append(f"{p.get('id')}: {type(e).__name__}")
            continue
        cont = {"contestacao": 0, "pergunta": 0, "hostil": 0, "outro": 0}
        itens = []
        for c in dados:
            autor = (c.get("from") or {}).get("id") or ""
            if ig_user and autor == ig_user:  # o primeiro comentário é do próprio bot
                continue
            classe = classificar(c.get("text", ""))
            cont[classe] += 1
            item = {"id": c.get("id"), "classe": classe, "quando": c.get("timestamp"),
                    "curtidas": c.get("like_count", 0)}
            if classe in ("contestacao", "pergunta"):
                item["texto"] = (c.get("text") or "")[:160]
            itens.append(item)
            if classe == "contestacao" and c.get("id") not in vistos:
                enviar("CBR: comentário contesta um post",
                       f"No post \"{(p.get('titulo') or '').replace('*', '')[:80]}\" alguém diz: "
                       f"\"{(c.get('text') or '')[:140]}\". Confira pelo protocolo de crise (manual, seção 11).",
                       p.get("permalink"), ["warning"])
            vistos.add(c.get("id"))
        if itens:
            saida["posts"].append({"id": p.get("id"), "permalink": p.get("permalink"), "contagem": cont,
                                   "comentarios": itens[:30]})
    estado["comentarios_vistos"] = list(vistos)[-500:]
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"comentários: {sum(len(x['comentarios']) for x in saida['posts'])} em {len(saida['posts'])} posts")
