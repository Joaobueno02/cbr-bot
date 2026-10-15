"""Relatório semanal de desempenho (toda segunda de manhã).

Para cada post publicado nos últimos 7 dias (registro/posts.jsonl), busca as métricas no
Instagram e agrega por editoria, formato, faixa de horário, collab e bombástica. Calcula
também a variação de seguidores (registro/seguidores.jsonl).

Saída: registro/relatorios/AAAA-MM-DD.json. A rodada da CBR de segunda lê esse arquivo,
manda o resumo ao João e sugere ajustes (sem mudar o manual sozinha).

Requer a permissão instagram_manage_insights no token. Sem ela, grava o erro no relatório.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import REGISTRO, RAIZ, ErroAPI, chamar  # noqa: E402

METRICAS = ["reach", "views", "likes", "comments", "shares", "saved", "total_interactions"]
SAIDA = RAIZ / "registro" / "relatorios"
BRT = timezone(timedelta(hours=-3))


def metricas_do_post(media_id: str) -> dict:
    out, erros = {}, []
    for m in METRICAS:  # uma por vez: se uma métrica não existir para o formato, as outras seguem
        try:
            dados = chamar("GET", f"{media_id}/insights", metric=m).get("data", [])
            if dados:
                v = dados[0].get("values", [{}])[0].get("value", dados[0].get("total_value", {}).get("value"))
                out[m] = v
        except ErroAPI as e:
            erros.append(f"{m}: {e}")
    if erros and not out:
        out["_erro"] = erros[0]
    return out


def faixa(hora: int) -> str:
    if hora < 10:
        return "07-10h"
    if hora < 13:
        return "10-13h"
    if hora < 17:
        return "13-17h"
    if hora < 20:
        return "17-20h"
    return "20-23h"


def main() -> None:
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=7)
    posts = []
    if REGISTRO.exists():
        for linha in REGISTRO.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            p = json.loads(linha)
            q = datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if q >= inicio and p.get("media_id"):
                p["_q"] = q
                posts.append(p)

    linhas = []
    for p in posts:
        m = metricas_do_post(p["media_id"])
        linhas.append({
            "id": p["id"], "titulo": p.get("titulo"), "editoria": p.get("editoria"),
            "formato": p.get("formato") or "feed", "bombastica": bool(p.get("bombastica")),
            "collab": bool(p.get("collab")), "hora": p["_q"].astimezone(BRT).strftime("%a %H:%M"),
            "faixa": faixa(p["_q"].astimezone(BRT).hour), "permalink": p.get("permalink"), **m,
        })

    def agrega(chave: str) -> dict:
        grupos = defaultdict(list)
        for l in linhas:
            if "_erro" not in l:
                grupos[str(l[chave])].append(l)
        res = {}
        for k, ls in grupos.items():
            def media(campo):
                vals = [x.get(campo) for x in ls if isinstance(x.get(campo), (int, float))]
                return round(sum(vals) / len(vals), 1) if vals else None
            res[k] = {"posts": len(ls), "alcance_medio": media("reach"), "views_medio": media("views"),
                      "interacoes_medias": media("total_interactions"), "compart_medio": media("shares"),
                      "salvos_medio": media("saved")}
        return res

    seguidores = []
    arq_seg = RAIZ / "registro" / "seguidores.jsonl"
    if arq_seg.exists():
        for linha in arq_seg.read_text(encoding="utf-8").splitlines():
            if linha.strip():
                s = json.loads(linha)
                q = datetime.strptime(s["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if q >= inicio - timedelta(days=1):
                    seguidores.append(s["seguidores"])

    rel = {
        "periodo": [inicio.strftime("%Y-%m-%d"), agora.strftime("%Y-%m-%d")],
        "total_posts": len(linhas),
        "seguidores": {"inicio": seguidores[0] if seguidores else None, "fim": seguidores[-1] if seguidores else None},
        "por_editoria": agrega("editoria"), "por_formato": agrega("formato"), "por_faixa": agrega("faixa"),
        "collab_vs_sem": agrega("collab"), "bombastica_vs_comum": agrega("bombastica"),
        "top5_alcance": sorted([l for l in linhas if isinstance(l.get("reach"), (int, float))],
                               key=lambda l: -l["reach"])[:5],
        "posts": linhas,
    }
    erros = [l["_erro"] for l in linhas if "_erro" in l]
    if erros:
        rel["aviso"] = ("métricas indisponíveis em parte dos posts; se o erro fala em permissão, "
                        "o token precisa de instagram_manage_insights") + f" — ex.: {erros[0]}"
    SAIDA.mkdir(parents=True, exist_ok=True)
    (SAIDA / f"{agora.strftime('%Y-%m-%d')}.json").write_text(json.dumps(rel, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"relatório: {len(linhas)} posts, {len(erros)} sem métricas")


if __name__ == "__main__":
    main()
