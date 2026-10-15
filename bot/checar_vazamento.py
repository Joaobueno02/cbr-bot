"""Trava anti-vazamento: falha se algum arquivo alterado contiver o token ou algo parecido.

Uso: python bot/checar_vazamento.py <arquivo> [<arquivo> ...]
Roda no workflow antes de todo commit. Se achar algo, apaga nada e sai com erro:
o commit não acontece e o token não chega ao repositório público.
"""
import os
import re
import sys
from pathlib import Path

PADROES = [re.compile(r"EAA[A-Za-z0-9]{20,}"), re.compile(r"access_token", re.I)]


def main() -> int:
    token = os.environ.get("IG_TOKEN", "")
    achados = []
    for nome in sys.argv[1:]:
        p = Path(nome)
        if not p.is_file() or p.suffix.lower() in (".jpg", ".jpeg", ".png", ".woff2"):
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if token and token in txt:
            achados.append(f"{nome}: contém o IG_TOKEN")
        for pad in PADROES:
            if pad.search(txt):
                achados.append(f"{nome}: padrão suspeito {pad.pattern}")
    if achados:
        print("VAZAMENTO EVITADO — nada será commitado:")
        print("\n".join(achados))
        return 1
    print(f"ok: {len(sys.argv) - 1} arquivo(s) verificados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
