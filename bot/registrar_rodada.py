"""Registro de rodadas (item 4 da fila do AGENTS.md; pedido do João, 04/11/2026).

Grava uma linha por rodada em registro/rodadas.jsonl, para o dossiê das 23h contar rodadas curtas,
descartes antes e depois do render, sites bloqueados e se o Gemini estava no ar.

Uso (fim da rodada completa):
  python bot/registrar_rodada.py --tipo completa --candidatos 7 --publicados 1 \
      --descartados-antes 5 --descartados-depois 0 --sites "folha.uol.com.br,brasil247.com" --ia-ok true \
      --obs "teto diário atingido" \
      --descarte "Anvisa aprova novo medicamento para câncer de mama" --descarte "Flávio acusa Moraes..."
--descarte (repetível; desde 24/11/2026, tarefa 0 do AGENTS.md) grava a manchete exatamente como veio da triagem,
com o número de veículos que ela tinha no radar/triagem.json na hora do descarte. O bot/rodada_curta.py usa isso para
não contar de novo, no mesmo dia, o candidato já descartado, a não ser que ele tenha ganhado veículos desde então.
A rodada curta é gravada sozinha pelo bot/rodada_curta.py.
Sem dependências fora da biblioteca padrão.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "registro" / "rodadas.jsonl"
BRT = timezone(timedelta(hours=-3))


def normalizar(texto: str) -> str:
    """Minúsculas, sem acento e sem pontuação: para comparar manchetes."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", t).split())


def veiculos_na_triagem(manchete: str) -> int | None:
    """Quantos veículos a manchete tem agora no radar/triagem.json (candidatos, obrigatórios, rebaixados)."""
    try:
        t = json.loads((RAIZ / "radar" / "triagem.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    alvo = normalizar(manchete)
    for chave in ("candidatos", "obrigatorios", "rebaixados", "descartados_mais_quentes"):
        for c in t.get(chave, []) or []:
            if normalizar(c.get("manchete", "")) == alvo:
                return c.get("veiculos")
    return None


def registrar(tipo: str, candidatos: int = 0, publicados: int = 0, descartados_antes: int = 0,
              descartados_depois: int = 0, sites_bloqueados: list[str] | None = None,
              ia_ok: bool | None = None, obs: str = "", descartes: list[str] | None = None) -> dict:
    agora = datetime.now(timezone.utc)
    linha = {
        "quando": agora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hora_brasilia": agora.astimezone(BRT).strftime("%Y-%m-%d %H:%M"),
        "tipo": tipo,
        "candidatos": candidatos,
        "publicados": publicados,
        "descartados_antes_render": descartados_antes,
        "descartados_depois_render": descartados_depois,
        "sites_bloqueados": sites_bloqueados or [],
        "ia_ok": ia_ok,
        "obs": obs[:300],
    }
    if descartes:
        linha["descartes"] = [{"manchete": m[:200], "veiculos": veiculos_na_triagem(m)} for m in descartes if m.strip()]
    ARQ.parent.mkdir(exist_ok=True)
    with ARQ.open("a", encoding="utf-8") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha


def _bool(v: str) -> bool | None:
    v = (v or "").strip().lower()
    return True if v in ("true", "1", "sim") else False if v in ("false", "0", "nao", "não") else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", choices=["curta", "completa"], required=True)
    ap.add_argument("--candidatos", type=int, default=0)
    ap.add_argument("--publicados", type=int, default=0)
    ap.add_argument("--descartados-antes", type=int, default=0)
    ap.add_argument("--descartados-depois", type=int, default=0)
    ap.add_argument("--sites", default="", help="domínios que bloquearam ou pediram aprovação, separados por vírgula")
    ap.add_argument("--ia-ok", default="")
    ap.add_argument("--obs", default="")
    ap.add_argument("--descarte", action="append", default=[],
                    help="manchete descartada nesta rodada, como veio da triagem (repita para cada uma)")
    a = ap.parse_args()
    linha = registrar(a.tipo, a.candidatos, a.publicados, a.descartados_antes, a.descartados_depois,
                      [s.strip() for s in a.sites.split(",") if s.strip()], _bool(a.ia_ok), a.obs, a.descarte)
    print("registrado:", json.dumps(linha, ensure_ascii=False))


if __name__ == "__main__":
    main()
