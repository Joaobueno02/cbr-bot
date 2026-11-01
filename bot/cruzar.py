"""Checagem cruzada da notícia: acha a mesma notícia em outros veículos do radar.

Pedido do João (16/10/2026): achou uma notícia boa numa fonte? Procure a mesma notícia nas
outras fontes, compare as versões e escreva a nossa a partir do que elas têm em comum.

Uso:
  python bot/cruzar.py "palavras da notícia"            # busca por palavras no radar/atual.json
  python bot/cruzar.py "palavras" --minimo 4             # exige mais palavras em comum

Mostra os assuntos do radar que batem com as palavras, com TODOS os veículos e links de cada um,
marcando os que parecem independentes (veículo diferente, não é agregador nem republicação de
agência). Depois, abra pelo menos 2 versões independentes e preencha "apuracao" no post.json
(ver MANUAL, seção 3).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from radar import normalizar  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
AGREGADORES = ("msn", "yahoo", "terra", "bol", "uol notícias", "istoé dinheiro", "google")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("busca")
    ap.add_argument("--minimo", type=int, default=0, help="palavras em comum (padrão: metade da busca, no mínimo 2)")
    ap.add_argument("--max", type=int, default=6)
    a = ap.parse_args()
    alvo = normalizar(a.busca)
    if not alvo:
        sys.exit("busca vazia")
    minimo = a.minimo or max(2, (len(alvo) + 1) // 2)
    grupos = json.loads((RAIZ / "radar" / "atual.json").read_text(encoding="utf-8"))["grupos"]
    achados = []
    for g in grupos:
        melhor = 0
        for l in g.get("links", []) + [{"titulo": g["manchete"]}]:
            melhor = max(melhor, len(alvo & normalizar(l["titulo"])))
        if melhor >= minimo:
            achados.append((melhor, g))
    achados.sort(key=lambda x: (-x[0], -x[1]["temperatura"]))
    if not achados:
        print(f"nada no radar com {minimo}+ palavras de \"{a.busca}\". Procure na web (WebSearch) pelas mesmas palavras.")
        return
    for nota, g in achados[: a.max]:
        print(f"\n## [{g['temperatura']} veículos] {g['manchete']}  (bate {nota} palavras)")
        print("   veículos: " + ", ".join(g["veiculos"]))
        vistos = set()
        for l in g.get("links", []):
            v = l["veiculo"]
            marca = "  " if v in vistos or any(x in v.lower() for x in AGREGADORES) else "* "
            vistos.add(v)
            print(f"   {marca}{v}: {l['titulo']}\n      {l['link']}")
    print("\n* = candidato a versão independente. Abra pelo menos 2 e compare (MANUAL, seção 3).")


if __name__ == "__main__":
    main()
