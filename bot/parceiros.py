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


CANDIDATOS_MOVIMENTOS = {
    "MST": ["movimentosemterra", "mst_oficial", "mstoficial"],
    "MTST": ["mtst", "mtst_oficial", "mtstbrasil"],
    "CUT": ["cutbrasil", "cut_brasil", "cutnacional"],
    "UNE": ["uneoficial", "une_oficial", "unebrasil"],
    "Apib": ["apiboficial", "apib_oficial"],
    "Sleeping Giants": ["slpng_giants_pt"],
    "Greenpeace Brasil": ["greenpeacebrasil", "greenpeacebr"],
    "MAB": ["mabnacional", "mab_nacional"],
    "Levante Popular da Juventude": ["levantepopulardajuventude", "levantepopular"],
    "Contag": ["contagbrasil", "contag_oficial"],
}


def horarios() -> None:
    """Uma vez, à mão (manutencao.yml tarefa=movimentos): confirma os @ dos movimentos e mede
    em que horas (Brasília) cada perfil mais posta e quando os posts rendem mais.
    Grava radar/movimentos_horarios.json."""
    from collections import Counter, defaultdict
    from datetime import timedelta
    saida = {"quando": agora(), "perfis": {}}
    for nome, cands in CANDIDATOS_MOVIMENTOS.items():
        for user in cands:
            try:
                r = chamar("GET", CONFIG["ig_user_id"],
                           fields=f"business_discovery.username({user}){{username,followers_count,media_count,"
                                  f"media.limit(60){{timestamp,like_count,comments_count}}}}")
            except ErroAPI as e:
                saida["perfis"].setdefault(nome, {"testados": []})["testados"].append({"user": user, "erro": str(e)[:160]})
                continue
            bd = r.get("business_discovery", {})
            horas, inter = Counter(), defaultdict(list)
            datas = []
            for m in bd.get("media", {}).get("data", []):
                t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(timezone(timedelta(hours=-3)))
                datas.append(t)
                horas[t.hour] += 1
                inter[t.hour].append((m.get("like_count") or 0) + (m.get("comments_count") or 0))
            dias = max(1, (max(datas) - min(datas)).days) if datas else 1
            saida["perfis"][nome] = {
                "user": user, "seguidores": bd.get("followers_count"), "posts_analisados": len(datas),
                "periodo_dias": dias, "posts_por_dia": round(len(datas) / dias, 1),
                "posts_por_hora": {f"{h:02d}h": horas[h] for h in sorted(horas)},
                "mediana_interacoes_por_hora": {f"{h:02d}h": sorted(v)[len(v) // 2] for h, v in sorted(inter.items())},
                "testados": saida["perfis"].get(nome, {}).get("testados", []),
            }
            break
    destino = RAIZ / "radar" / "movimentos_horarios.json"
    destino.write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print({k: v.get("user", "não achado") for k, v in saida["perfis"].items()})


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
    if "--horarios" in sys.argv:
        horarios()
    else:
        main()
