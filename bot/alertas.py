"""Alertas no celular do João (via ntfy), conferidos a cada 10 minutos pelo GitHub Actions.

1. Collab aceita: para cada post da CBR com convite pendente (registro/collabs_pendentes.json),
   consulta GET /{media-id}/collaborators. Assim que um convidado aceitar, manda o alerta com o
   link do post para o João compartilhar nos Stories pelo app ("Adicionar ao story").
   Convites com mais de 48 h sem aceite saem da lista.

2. Post forte dos parceiros: a cada 20 min lê o feed da BFC e da Luz (Business Discovery), grava
   radar/parceiros.json (monitor da BFC usado pela pauta) e Um post vira alerta
   quando foi publicado no mesmo dia a partir das 7h, tem pelo menos 1 h de vida e engajamento
   por hora no quartil de cima dos posts do próprio perfil nas últimas 48 h (régua de comparação). Máximo de 5 alertas por perfil por dia, só das 7h às 23h.

O tópico do ntfy fica no secret NTFY_TOPIC (o repositório é público). Sem ele, nada é enviado.
Estado em registro/alertas.json.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, PENDENTES, RAIZ, ErroAPI, agora, chamar  # noqa: E402
from parceiros import coletar, coletar_movimentos, gravar  # noqa: E402

ESTADO = RAIZ / "registro" / "alertas.json"
BRT = timezone(timedelta(hours=-3))
PARCEIROS = ["brasilforadacaverna", "luzmanifesto"]
MAX_DIA = 5
JANELA_COLLAB = timedelta(hours=48)


def enviar(titulo: str, mensagem: str, link: str | None, tags: list[str]) -> bool:
    topico = os.environ.get("NTFY_TOPIC", "").strip()
    if not topico:
        print("NTFY_TOPIC ausente; alerta não enviado:", titulo)
        return False
    if link:
        mensagem = f"{mensagem}\n\n{link}"
    corpo = {"topic": topico, "title": titulo, "message": mensagem, "tags": tags, "priority": 4}
    if link:
        corpo["click"] = link
        corpo["actions"] = [{"action": "view", "label": "Abrir post", "url": link}]
    try:
        r = requests.post("https://ntfy.sh/", json=corpo, timeout=20)
        return r.ok
    except Exception:
        return False


def collabs(estado: dict) -> None:
    if not PENDENTES.exists():
        return
    pend = json.loads(PENDENTES.read_text(encoding="utf-8"))
    restantes = []
    for item in pend:
        desde = datetime.strptime(item["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - desde > JANELA_COLLAB:
            estado["log"].append({"quando": agora(), "tipo": "collab_expirou", "id": item["id"]})
            continue
        try:
            colabs = chamar("GET", f"{item['media_id']}/collaborators").get("data", [])
        except ErroAPI as e:
            item["ultimo_erro"] = str(e)
            restantes.append(item)
            continue
        aceitos = [c.get("username") for c in colabs if str(c.get("invite_status", "")).lower() == "accepted"]
        ja = set(item.get("avisados", []))
        novos = [a for a in aceitos if a not in ja]
        if novos:
            quem = ", ".join(f"@{a}" for a in novos)
            ok = enviar("Collab aceita: põe nos Stories",
                        f"{quem} aceitou o post \"{(item.get('titulo') or '')[:90]}\". Toque para abrir e use \"Adicionar ao story\".",
                        item.get("permalink"), ["handshake"])
            if ok:
                item["avisados"] = sorted(ja | set(novos))
                estado["log"].append({"quando": agora(), "tipo": "collab_aceita", "id": item["id"], "aceitos": novos})
        # continua na lista até todos aceitarem ou expirar, para avisar aceites tardios
        if set(item.get("avisados", [])) < set(c.lstrip("@") for c in item.get("convidados", [])):
            restantes.append(item)
    PENDENTES.write_text(json.dumps(restantes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parceiros(estado: dict) -> None:
    """Monitor da BFC e da Luz (pedido do João, 16/10/2026): a cada 20 min lê o feed dos dois,
    grava radar/parceiros.json (a pauta e as rodadas leem dali) e manda alerta de post forte.
    Uma chamada por perfil; o radar das :50 não chama mais a API (mesmo gasto, dado mais novo)."""
    hoje = datetime.now(BRT)
    if not 7 <= hoje.hour <= 23:
        return
    # movimentos sociais: 3 vezes por dia, 30 min depois dos picos de postagem medidos em 16/10/2026
    # (radar/movimentos_horarios.json: ondas às 9-12h, 15-18h e 21h); horários em config.json
    agora_hm = [(int(x[:2]), int(x[3:])) for x in CONFIG.get("movimentos_horarios", ["12:30", "18:30", "21:30"])]
    na_janela = any(hoje.hour == h and m <= hoje.minute < m + 10 for h, m in agora_hm)
    if na_janela or "--movimentos" in sys.argv:
        try:
            coletar_movimentos()
        except Exception as e:
            estado["log"].append({"quando": agora(), "tipo": "erro_movimentos", "erro": str(e)[:200]})
    if hoje.minute % 20 >= 10 and "--parceiros" not in sys.argv:
        return
    dia = hoje.strftime("%Y-%m-%d")
    if estado.get("dia") != dia:
        estado["dia"] = dia
        estado["contagem"] = {}
    perfis = {}
    for user in PARCEIROS:
        try:
            perfis[user] = coletar(user)
        except ErroAPI as e:
            perfis[user] = {"erro": str(e)}
            estado["log"].append({"quando": agora(), "tipo": "erro_parceiro", "perfil": user, "erro": str(e)})
    gravar(perfis)
    for user, dados in perfis.items():
        if "posts" not in dados or estado["contagem"].get(user, 0) >= MAX_DIA:
            continue
        posts = dados["posts"]
        if len(posts) < 4:
            continue
        vels = sorted(p["velocidade"] for p in posts)
        corte = vels[int(len(vels) * 0.75)]
        avisados = set(estado.setdefault("avisados_parceiros", []))
        # só posts publicados hoje a partir das 7h (Brasília); o que saiu antes fica de fora
        inicio_dia = hoje.replace(hour=7, minute=0, second=0, microsecond=0)
        candidatos = sorted([p for p in posts
                             if datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%S%z") >= inicio_dia
                             and p["horas"] >= 1 and p["velocidade"] >= corte and p["id"] not in avisados],
                            key=lambda p: -p["velocidade"])
        for p in candidatos:
            if estado["contagem"].get(user, 0) >= MAX_DIA:
                break
            resumo = " ".join((p.get("legenda") or "").split())[:110]
            ok = enviar(f"Post forte da @{user}",
                        f"{int(p['velocidade'])} interações/h ({p.get('curtidas') or 0} curtidas em {p['horas']:.0f} h). {resumo}",
                        p.get("link"), ["fire"])
            if ok:
                estado["contagem"][user] = estado["contagem"].get(user, 0) + 1
                avisados.add(p["id"])
                estado["log"].append({"quando": agora(), "tipo": "parceiro", "perfil": user, "id": p["id"],
                                      "link": p.get("link")})
        estado["avisados_parceiros"] = sorted(avisados)[-300:]


def main() -> None:
    if "--teste" in sys.argv:
        ok = enviar("CBR: teste de alerta", "Se você está lendo isto, os avisos de collab aceita e de posts fortes da BFC/Luz vão chegar aqui.",
                    "https://www.instagram.com/comunabrasileira_/", ["white_check_mark"])
        print("teste enviado" if ok else "falha no envio do teste")
        sys.exit(0 if ok else 1)
    if not CONFIG.get("publicacao_ativa"):
        print("publicação desligada; sem alertas")
        return
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    estado.setdefault("log", [])
    collabs(estado)
    parceiros(estado)
    estado["log"] = estado["log"][-200:]
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("alertas ok")


if __name__ == "__main__":
    main()
