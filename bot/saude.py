"""Checagem diária de saúde: o token ainda funciona? quanto da cota de publicação foi usada?

Grava registro/saude.json (o último estado) e acrescenta os seguidores do dia em
registro/seguidores.jsonl. A primeira rodada da CBR do dia lê saude.json e avisa o João
no celular se algo estiver errado.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, RAIZ, ErroAPI, agora, chamar  # noqa: E402

SAUDE = RAIZ / "registro" / "saude.json"
SEGUIDORES = RAIZ / "registro" / "seguidores.jsonl"


def main() -> None:
    ig = CONFIG["ig_user_id"]
    res = {"quando": agora(), "ok": False, "problemas": []}
    try:
        conta = chamar("GET", ig, fields="username,followers_count,media_count")
        res["seguidores"] = conta.get("followers_count")
        res["posts"] = conta.get("media_count")
        if conta.get("username") != "comunabrasileira_":
            res["problemas"].append(f"token aponta para outra conta: {conta.get('username')}")
        cota = chamar("GET", f"{ig}/content_publishing_limit", fields="quota_usage,config").get("data", [{}])[0]
        res["cota_usada"] = cota.get("quota_usage")
        res["cota_total"] = (cota.get("config") or {}).get("quota_total")
        if res["cota_usada"] is not None and res["cota_total"] and res["cota_usada"] >= 0.8 * res["cota_total"]:
            res["problemas"].append(f"cota de publicação quase no fim ({res['cota_usada']}/{res['cota_total']})")
    except ErroAPI as e:
        res["problemas"].append(f"token ou API com erro: {e}")
    except Exception as e:  # rede etc.
        res["problemas"].append(f"falha na checagem: {type(e).__name__}")
    if not CONFIG.get("publicacao_ativa"):
        res["problemas"].append("publicação está desligada em config.json")
    res["ok"] = not res["problemas"]
    SAUDE.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if res.get("seguidores") is not None:
        with SEGUIDORES.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"quando": res["quando"], "seguidores": res["seguidores"], "posts": res.get("posts")}) + "\n")
    print(json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
