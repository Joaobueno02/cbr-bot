"""Trava anti-vazamento: falha se algum arquivo alterado contiver o token ou algo parecido.

Uso: python bot/checar_vazamento.py <arquivo> [<arquivo> ...]
Roda no workflow antes de todo commit. Se achar algo, apaga nada e sai com erro:
o commit não acontece e o token não chega ao repositório público.
"""
import os
import re
import sys
from pathlib import Path

PADROES = [re.compile(r"EAA[A-Za-z0-9]{20,}"), re.compile(r"access_token", re.I),
           re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}")]  # chave da OpenAI (triagem, 19/10/2026)
PARECIDOS = (0, 2)  # padrões "parecidos com chave" que links longos podem casar por acaso
# arquivos do radar de manchetes: gerados por bot/radar.py, que nunca toca no token. Os links do
# Google Notícias são códigos longos que às vezes contêm "EAA..." por acaso, então ali só vale a
# checagem do token exato e de "access_token".
SO_TOKEN_EXATO = {"radar/atual.json", "radar/novos.md", "radar/top.md", "radar/vistos.json",
                  "radar/saude_fontes.json", "radar/pauta_itens.json", "radar/triagem.json",
                  "radar/triagem_estado.json"}


def main() -> int:
    token = os.environ.get("IG_TOKEN", "")
    chave_ia = os.environ.get("OPENAI_API_KEY", "")
    achados = []
    for nome in sys.argv[1:]:
        p = Path(nome)
        if not p.is_file() or p.suffix.lower() in (".jpg", ".jpeg", ".png", ".woff2"):
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if token and token in txt:
            achados.append(f"{nome}: contém o IG_TOKEN")
        if chave_ia and chave_ia in txt:
            achados.append(f"{nome}: contém a OPENAI_API_KEY")
        for pad in PADROES:
            if nome in SO_TOKEN_EXATO and PADROES.index(pad) in PARECIDOS:
                continue
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
