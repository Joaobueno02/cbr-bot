"""Números das collabs para o dossiê (pedido do João, 20/10/2026).

Roda com a coleta do dossiê (manutencao.yml, 22h45). Para cada post dos últimos 14 dias com convite
de collab (registro/posts.jsonl), pergunta à API quem aceitou (GET /{media-id}/collaborators) e junta:

  - por página convidada: convites, aceites, taxa de aceite, último convite;
  - por post com collab aceita: seguidores da CBR no dia anterior e no dia seguinte
    (registro/seguidores.jsonl, uma medida por dia: é sinal, não prova).

Grava radar/collabs.json. Só leitura na API; não muda nada no Instagram.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import RAIZ, ErroAPI, agora, chamar  # noqa: E402

POSTS = RAIZ / "registro" / "posts.jsonl"
SEGUIDORES = RAIZ / "registro" / "seguidores.jsonl"
SAIDA = RAIZ / "radar" / "collabs.json"
DIAS = 14


def _jsonl(arq: Path) -> list[dict]:
    if not arq.exists():
        return []
    return [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines() if l.strip()]


def seguidores_em(medidas: list[dict], quando: datetime, depois: bool) -> int | None:
    """Medida mais próxima antes (depois=False) ou depois (depois=True) do momento."""
    cand = []
    for m in medidas:
        t = datetime.strptime(m["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if (t >= quando) == depois:
            cand.append((abs((t - quando).total_seconds()), m.get("seguidores")))
    return min(cand)[1] if cand else None


def main() -> None:
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS)
    medidas = _jsonl(SEGUIDORES)
    paginas: dict[str, dict] = {}
    posts_saida = []
    for p in _jsonl(POSTS):
        if not p.get("collab") or not p.get("media_id"):
            continue
        quando = datetime.strptime(p["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if quando < limite:
            continue
        try:
            dados = chamar("GET", f"{p['media_id']}/collaborators").get("data", [])
            status = {c.get("username"): str(c.get("invite_status", "")).lower() for c in dados}
            erro = None
        except ErroAPI as e:
            status, erro = {}, str(e)[:120]
        aceitos = [u for u in p["collab"] if status.get(u) == "accepted"]
        for u in p["collab"]:
            g = paginas.setdefault(u, {"convites": 0, "aceites": 0, "ultimo_convite": None})
            g["convites"] += 1
            g["aceites"] += u in aceitos
            g["ultimo_convite"] = max(g["ultimo_convite"] or "", p["quando"])
        antes, depois = seguidores_em(medidas, quando, False), seguidores_em(medidas, quando, True)
        posts_saida.append({"id": p["id"], "quando": p["quando"], "formato": p.get("formato"),
                            "editoria": p.get("editoria"), "permalink": p.get("permalink"),
                            "convidados": p["collab"], "aceitos": aceitos, "erro": erro,
                            "seguidores_antes": antes, "seguidores_depois": depois,
                            "ganho": (depois - antes) if antes is not None and depois is not None else None})
    for g in paginas.values():
        g["taxa_aceite"] = round(g["aceites"] / g["convites"], 2) if g["convites"] else None
    SAIDA.write_text(json.dumps({
        "quando": agora(), "janela_dias": DIAS,
        "obs": "ganho = seguidores da medida seguinte menos a anterior (uma medida por dia): sinal, não prova",
        "paginas": dict(sorted(paginas.items(), key=lambda kv: (-kv[1]["aceites"], -kv[1]["convites"]))),
        "posts": posts_saida,
    }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"collabs: {len(posts_saida)} posts com convite, {len(paginas)} páginas")


if __name__ == "__main__":
    main()
