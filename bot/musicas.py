"""Sonda a biblioteca de músicas do Instagram para escolher a música padrão de cada editoria
(pedido do João, 27/10/2026). Para cada editoria de config.json > musicas, busca pelo termo
("busca") e por termos extras ("alternativas"), e grava em radar/musicas.json as 8 primeiras de cada
busca (título, artista, audio_id, duração) ou o erro da API. O Claude escolhe a faixa e grava o
audio_id em config.json (com o OK do João); o publicador passa a usar sempre a mesma por editoria.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, RAIZ, ErroAPI, agora, buscar_musicas  # noqa: E402

SAIDA = RAIZ / "radar" / "musicas.json"


def resumo(m: dict) -> dict:
    return {"titulo": m.get("title"), "artista": m.get("display_artist"), "audio_id": m.get("audio_id"),
            "duracao_ms": m.get("duration_in_ms") or m.get("duration")}


def main() -> None:
    res = {"quando": agora(), "buscas": {}}
    termos = {"(em alta)": None}
    for ed, d in (CONFIG.get("musicas") or {}).items():
        for t in [d.get("busca")] + list(d.get("alternativas") or []):
            if t:
                termos.setdefault(t, t)
    for rotulo, termo in termos.items():
        try:
            dados = buscar_musicas(termo)
            res["buscas"][rotulo] = {"ok": True, "n": len(dados), "musicas": [resumo(m) for m in dados[:8]]}
        except ErroAPI as e:
            res["buscas"][rotulo] = {"ok": False, "erro": str(e)[:300]}
    res["ok"] = any(b.get("n") for b in res["buscas"].values())
    SAIDA.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: (v.get("n") if v.get("ok") else v.get("erro")) for k, v in res["buscas"].items()},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
