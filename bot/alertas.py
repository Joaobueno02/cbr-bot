"""Alertas no celular do João (via ntfy), conferidos a cada 10 minutos pelo GitHub Actions.

1. Collab aceita: para cada post da CBR com convite pendente (registro/collabs_pendentes.json),
   consulta GET /{media-id}/collaborators. Assim que um convidado aceitar, manda o alerta com o
   link do post para o João compartilhar nos Stories pelo app ("Adicionar ao story").
   Convites com mais de 48 h sem aceite saem da lista.

2. Post forte dos parceiros: lê o feed da BFC e da Luz (Business Discovery). Um post vira alerta
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
    hoje = datetime.now(BRT)
    if not 7 <= hoje.hour <= 23:
        return
    dia = hoje.strftime("%Y-%m-%d")
    if estado.get("dia") != dia:
        estado["dia"] = dia
        estado["contagem"] = {}
    campos = "id,like_count,comments_count,media_product_type,permalink,timestamp,caption"
    for user in PARCEIROS:
        if estado["contagem"].get(user, 0) >= MAX_DIA:
            continue
        try:
            r = chamar("GET", CONFIG["ig_user_id"],
                       fields=f"business_discovery.username({user}){{media.limit(30){{{campos}}}}}")
        except ErroAPI as e:
            estado["log"].append({"quando": agora(), "tipo": "erro_parceiro", "perfil": user, "erro": str(e)})
            continue
        posts = []
        for m in r.get("business_discovery", {}).get("media", {}).get("data", []):
            t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
            horas = (datetime.now(timezone.utc) - t).total_seconds() / 3600
            if horas > 48:
                continue
            inter = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
            posts.append({**m, "horas": horas, "vel": inter / max(horas, 1)})
        if len(posts) < 4:
            continue
        vels = sorted(p["vel"] for p in posts)
        corte = vels[int(len(vels) * 0.75)]
        avisados = set(estado.setdefault("avisados_parceiros", []))
        # só posts publicados hoje a partir das 7h (Brasília); o que saiu antes fica de fora
        inicio_dia = hoje.replace(hour=7, minute=0, second=0, microsecond=0)
        candidatos = sorted([p for p in posts
                             if datetime.strptime(p["timestamp"], "%Y-%m-%dT%H:%M:%S%z") >= inicio_dia
                             and p["horas"] >= 1 and p["vel"] >= corte and p["id"] not in avisados],
                            key=lambda p: -p["vel"])
        for p in candidatos:
            if estado["contagem"].get(user, 0) >= MAX_DIA:
                break
            resumo = " ".join((p.get("caption") or "").split())[:110]
            ok = enviar(f"Post forte da @{user}",
                        f"{int(p['vel'])} interações/h ({p.get('like_count') or 0} curtidas em {p['horas']:.0f} h). {resumo}",
                        p.get("permalink"), ["fire"])
            if ok:
                estado["contagem"][user] = estado["contagem"].get(user, 0) + 1
                avisados.add(p["id"])
                estado["log"].append({"quando": agora(), "tipo": "parceiro", "perfil": user, "id": p["id"],
                                      "link": p.get("permalink")})
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
