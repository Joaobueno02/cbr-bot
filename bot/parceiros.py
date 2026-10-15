"""Lê o feed público da BFC e da Luz pela Business Discovery (só posts de feed e Reels;
stories de terceiros não são acessíveis pela API).

Grava radar/parceiros.json com os posts das últimas 48 h: legenda, curtidas, comentários,
tipo, link, imagem e uma "velocidade" (interações por hora desde a publicação).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, RAIZ, ErroAPI, agora, chamar  # noqa: E402

PARCEIROS = ["brasilforadacaverna", "luzmanifesto"]
CAMPOS = "id,caption,like_count,comments_count,media_type,media_product_type,permalink,timestamp,media_url,thumbnail_url"


def main() -> None:
    saida = {"quando": agora(), "perfis": {}}
    for user in PARCEIROS:
        try:
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
                posts.append({
                    "id": m["id"], "quando": m["timestamp"], "horas": round(horas, 1),
                    "tipo": m.get("media_product_type") or m.get("media_type"),
                    "curtidas": m.get("like_count"), "comentarios": m.get("comments_count"),
                    "velocidade": round(inter / horas, 1), "link": m.get("permalink"),
                    "imagem": m.get("media_url") if m.get("media_type") != "VIDEO" else m.get("thumbnail_url"),
                    "legenda": (m.get("caption") or "")[:600],
                })
            posts.sort(key=lambda p: -p["velocidade"])
            saida["perfis"][user] = {"seguidores": bd.get("followers_count"), "posts": posts}
        except ErroAPI as e:
            saida["perfis"][user] = {"erro": str(e)}
    destino = RAIZ / "radar" / "parceiros.json"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({u: (len(v.get("posts", [])) if "posts" in v else v.get("erro")) for u, v in saida["perfis"].items()})


if __name__ == "__main__":
    main()
