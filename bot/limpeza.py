"""Limpeza diária da fila, para o repositório não crescer sem controle.

Só mexe em posts que já terminaram (publicado, simulado, descartado) e nunca apaga
post.json nem o registro. Regras por idade (contada a partir da publicação/render):
  > 2 dias  : miniaturas da sonda (candidatas/), fotos originais, HTML de trabalho
  > 7 dias  : reels.mp4 e story.jpg (o Story só sai nas primeiras 48 h)
  > 30 dias : as artes (arte-*.jpg)
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FINAIS = {"publicado", "simulado", "descartado"}
REGRAS = [
    (2, ["candidatas", "foto.jpg", "foto-*.jpg", "foto-recorte.png", "arte-*.html"]),
    (7, ["reels.mp4", "story.jpg"]),
    (30, ["arte-*.jpg"]),
]


def idade_dias(post: dict) -> float | None:
    for chave in ("publicacao", "render"):
        q = (post.get(chave) or {}).get("quando")
        if q:
            t = datetime.strptime(q, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - t).total_seconds() / 86400
    return None


def main() -> None:
    apagados = 0
    for arq in sorted((RAIZ / "fila").glob("*/post.json")):
        post = json.loads(arq.read_text(encoding="utf-8"))
        if post.get("status") not in FINAIS:
            continue
        idade = idade_dias(post)
        if idade is None:
            continue
        for dias, padroes in REGRAS:
            if idade < dias:
                continue
            for padrao in padroes:
                for alvo in arq.parent.glob(padrao):
                    if alvo.is_dir():
                        shutil.rmtree(alvo)
                    else:
                        alvo.unlink()
                    apagados += 1
    print(f"limpeza: {apagados} arquivo(s)/pasta(s) removidos")


if __name__ == "__main__":
    main()
