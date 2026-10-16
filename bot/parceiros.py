"""Lê o feed público da BFC e da Luz pela Business Discovery (só posts de feed e Reels;
stories de terceiros não são acessíveis pela API).

Grava radar/parceiros.json com os posts das últimas 48 h (desde 16/10/2026 quem chama a cada
20 min é o bot/alertas.py; este script roda sozinho só à mão): legenda, curtidas, comentários,
tipo, link, imagem e uma "velocidade" (interações por hora desde a publicação).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, RAIZ, ErroAPI, agora, chamar  # noqa: E402

PARCEIROS = ["brasilforadacaverna", "luzmanifesto"]
CAMPOS = "id,username,caption,like_count,comments_count,media_type,media_product_type,permalink,timestamp,media_url,thumbnail_url"


def coletar(user: str) -> dict:
    """Uma chamada à Business Discovery: seguidores + posts das últimas 48 h do perfil."""
    r = chamar("GET", CONFIG["ig_user_id"],
               fields=f"business_discovery.username({user}){{username,followers_count,media_count,media.limit(30){{{CAMPOS}}}}}")
    bd = r.get("business_discovery", {})
    posts = []
    for m in bd.get("media", {}).get("data", []):
        t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        horas = max(0.5, (datetime.now(timezone.utc) - t).total_seconds() / 3600)
        if horas > 48:
            continue
        inter = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        dono = m.get("username")
        mencoes = sorted(set(re.findall(r"@([A-Za-z0-9_.]{3,30})", m.get("caption") or "")) - {user})
        posts.append({
            "id": m["id"], "dono": dono,
            # collab confirmada: o post está no feed do parceiro mas pertence a outra página
            "collab_confirmada": bool(dono and dono.lower() != user),
            "mencoes": mencoes,
            "quando": m["timestamp"], "horas": round(horas, 1),
            "tipo": m.get("media_product_type") or m.get("media_type"),
            "curtidas": m.get("like_count"), "comentarios": m.get("comments_count"),
            "velocidade": round(inter / horas, 1), "link": m.get("permalink"),
            "imagem": m.get("media_url") if m.get("media_type") != "VIDEO" else m.get("thumbnail_url"),
            "legenda": (m.get("caption") or "")[:600],
        })
    posts.sort(key=lambda p: -p["velocidade"])
    return {"seguidores": bd.get("followers_count"), "posts": posts}


def gravar(perfis: dict) -> None:
    """Grava radar/parceiros.json. Perfil que falhou mantém os dados da leitura anterior."""
    destino = RAIZ / "radar" / "parceiros.json"
    destino.parent.mkdir(exist_ok=True)
    try:
        antigo = json.loads(destino.read_text(encoding="utf-8")).get("perfis", {})
    except Exception:
        antigo = {}
    for user, v in perfis.items():
        if "erro" in v and "posts" in antigo.get(user, {}):
            perfis[user] = {**antigo[user], "erro_ultima_leitura": v["erro"]}
    destino.write_text(json.dumps({"quando": agora(), "perfis": perfis}, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")


def coletar_movimentos() -> dict:
    """Perfis de movimentos sociais (config.json > movimentos), 3 vezes por dia (pedido do João,
    16/10/2026): pauta que não sai em jornal. Grava radar/movimentos.json. Perfil que não for
    conta comercial/criador ou tiver o @ errado aparece com "erro" (corrija o @ no config.json)."""
    perfis = {}
    for user in CONFIG.get("movimentos", []):
        try:
            perfis[user] = coletar(user)
        except ErroAPI as e:
            perfis[user] = {"erro": str(e)[:200]}
    destino = RAIZ / "radar" / "movimentos.json"
    destino.write_text(json.dumps({"quando": agora(), "perfis": perfis}, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
    return perfis


def main() -> None:
    perfis = {}
    for user in PARCEIROS:
        try:
            perfis[user] = coletar(user)
        except ErroAPI as e:
            perfis[user] = {"erro": str(e)}
    gravar(perfis)
    print({u: (len(v.get("posts", [])) if "posts" in v else v.get("erro")) for u, v in perfis.items()})


if __name__ == "__main__":
    main()
