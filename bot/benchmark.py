"""Coleta diária para o dossiê de melhorias (roda às 22h45, antes da última rodada).

1. Páginas de referência (Business Discovery): posts das últimas 24 h de cada perfil em
   bot/referencias_paginas.json, com engajamento, formato, horário, tamanho da legenda,
   hashtags e menções. Salva miniaturas (480 px) dos posts que mais renderam em
   radar/benchmark/img/ para o robô analisar o design (apagadas no dia seguinte).
2. A CBR: posts publicados hoje e suas métricas (alcance, interações, compartilhamentos,
   salvos), seguidores atuais.

Saída: radar/benchmark.json
"""
from __future__ import annotations

import io
import json
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median

import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, REGISTRO, RAIZ, ErroAPI, agora, chamar  # noqa: E402

BRT = timezone(timedelta(hours=-3))
PERFIS = json.loads((RAIZ / "bot" / "referencias_paginas.json").read_text(encoding="utf-8"))["perfis"]
CAMPOS = "id,caption,like_count,comments_count,media_type,media_product_type,permalink,timestamp,media_url,thumbnail_url"
PASTA_IMG = RAIZ / "radar" / "benchmark" / "img"
METRICAS_CBR = ["reach", "views", "total_interactions", "shares", "saved", "likes", "comments"]


def perfil(user: str) -> dict:
    # pagina até cobrir 24 h (a API devolve no máximo ~40 por página)
    midias, cursor, seguidores = [], None, 0
    for _ in range(5):
        pag = f".after({cursor})" if cursor else ""
        r = chamar("GET", CONFIG["ig_user_id"],
                   fields=f"business_discovery.username({user}){{followers_count,media{pag}.limit(40){{{CAMPOS}}}}}")
        bd = r.get("business_discovery", {})
        seguidores = bd.get("followers_count") or seguidores
        lote = bd.get("media", {}).get("data", [])
        midias += lote
        cursor = bd.get("media", {}).get("paging", {}).get("cursors", {}).get("after")
        if not lote or not cursor:
            break
        ultimo = datetime.strptime(lote[-1]["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        if (datetime.now(timezone.utc) - ultimo).total_seconds() > 24 * 3600:
            break
    posts = []
    for m in midias:
        t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z")
        horas = (datetime.now(timezone.utc) - t).total_seconds() / 3600
        if horas > 24:
            continue
        leg = m.get("caption") or ""
        ocultas = m.get("like_count") is None   # perfil escondeu as curtidas
        inter = (m.get("like_count") or 0) + (m.get("comments_count") or 0)
        posts.append({
            "id": m["id"], "link": m.get("permalink"), "curtidas_ocultas": ocultas,
            "quando": t.astimezone(BRT).strftime("%d/%m %H:%M"), "_ts": t.timestamp(),
            "formato": m.get("media_product_type") or m.get("media_type"),
            "tipo_midia": m.get("media_type"),
            "curtidas": m.get("like_count"), "comentarios": m.get("comments_count"),
            "interacoes": inter, "por_mil_seguidores": round(1000 * inter / seguidores, 2) if seguidores else None,
            "legenda_caracteres": len(leg), "legenda_linhas": leg.count("\n") + 1 if leg else 0,
            "hashtags": re.findall(r"#\w+", leg)[:15], "emojis": len(re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", leg)),
            "inicio_legenda": " ".join(leg.split())[:600],
            "fim_legenda": " ".join(leg.split())[-250:] if len(leg) > 850 else "",
            "_img": m.get("media_url") if m.get("media_type") != "VIDEO" else m.get("thumbnail_url"),
        })
    posts.sort(key=lambda p: -p["interacoes"])
    resumo = {}
    validos = [p for p in posts if not p["curtidas_ocultas"]]
    if validos:
        por_formato = {}
        for p in validos:
            por_formato.setdefault(p["formato"], []).append(p["interacoes"])
        resumo = {
            "posts_24h": len(posts), "com_curtidas_ocultas": len(posts) - len(validos),
            "mediana_interacoes": median(p["interacoes"] for p in validos),
            "por_formato": {k: {"posts": len(v), "mediana": median(v)} for k, v in por_formato.items()},
            "mediana_legenda_caracteres": median(p["legenda_caracteres"] for p in posts),
            "horarios": [p["quando"] for p in sorted(posts, key=lambda p: p["_ts"])],
        }
    for p in posts:
        p.pop("_ts", None)
    return {"seguidores": seguidores, "resumo": resumo, "posts": posts}


def salvar_miniatura(url: str, destino: Path) -> bool:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        im.thumbnail((480, 600))
        im.save(destino, "JPEG", quality=78)
        return True
    except Exception:
        return False


def cbr_hoje() -> dict:
    inicio = datetime.now(BRT).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    posts = []
    if REGISTRO.exists():
        for linha in REGISTRO.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            p = json.loads(linha)
            q = datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if q >= inicio and p.get("media_id"):
                met = {}
                for m in METRICAS_CBR:
                    try:
                        d = chamar("GET", f"{p['media_id']}/insights", metric=m).get("data", [])
                        if d:
                            met[m] = d[0].get("values", [{}])[0].get("value", d[0].get("total_value", {}).get("value"))
                    except ErroAPI:
                        pass
                posts.append({"id": p["id"], "titulo": p.get("titulo"), "editoria": p.get("editoria"),
                              "formato": p.get("formato"), "collab": p.get("collab"),
                              "hora": q.astimezone(BRT).strftime("%H:%M"), "link": p.get("permalink"), **met})
    try:
        seg = chamar("GET", CONFIG["ig_user_id"], fields="followers_count").get("followers_count")
    except ErroAPI:
        seg = None
    return {"seguidores": seg, "posts": posts}


def main() -> None:
    if PASTA_IMG.exists():
        shutil.rmtree(PASTA_IMG)
    PASTA_IMG.mkdir(parents=True)
    saida = {"quando": agora(), "perfis": {}, "falhas": {}}
    for user in PERFIS:
        try:
            dados = perfil(user)
        except ErroAPI as e:
            saida["falhas"][user] = str(e)
            continue
        # miniaturas dos 3 posts de maior engajamento de cada perfil (6 da BFC, a referência principal)
        n = 6 if user == "brasilforadacaverna" else 3
        for i, p in enumerate(dados["posts"]):
            url = p.pop("_img", None)
            if i < n and url:
                nome = f"{user}-{i + 1}.jpg"
                if salvar_miniatura(url, PASTA_IMG / nome):
                    p["miniatura"] = f"radar/benchmark/img/{nome}"
        saida["perfis"][user] = dados
    saida["cbr"] = cbr_hoje()
    (RAIZ / "radar" / "benchmark.json").write_text(json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"benchmark: {len(saida['perfis'])} perfis, falhas: {list(saida['falhas'])}")


if __name__ == "__main__":
    main()
