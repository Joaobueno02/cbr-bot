"""Posta nos Stories os posts cuja collab foi aceita.

Lê registro/collabs_pendentes.json. Para cada post publicado com convite de collab nas
últimas 48 h, consulta GET /{media-id}/collaborators. Assim que algum convidado estiver
"Accepted", publica a versão vertical (story.jpg) nos Stories uma única vez e tira da lista.
Convites com mais de 48 h sem aceite saem da lista sem story.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import (CONFIG, PENDENTES, REGISTRO, ErroAPI, agora, chamar,  # noqa: E402
                      esperar_container, url_arte)

JANELA = timedelta(hours=48)


def main() -> None:
    if not CONFIG.get("publicacao_ativa") or not PENDENTES.exists():
        print("nada a fazer")
        return
    pend = json.loads(PENDENTES.read_text(encoding="utf-8"))
    restantes, log = [], []
    ig = CONFIG["ig_user_id"]
    for item in pend:
        desde = datetime.strptime(item["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - desde > JANELA:
            log.append({"id": item["id"], "resultado": "expirou sem aceite"})
            continue
        try:
            colabs = chamar("GET", f"{item['media_id']}/collaborators").get("data", [])
            aceitos = [c.get("username") for c in colabs if str(c.get("invite_status", "")).lower() == "accepted"]
            if not aceitos:
                restantes.append(item)
                continue
            cid = chamar("POST", f"{ig}/media", media_type="STORIES", image_url=url_arte(item["id"], item["story"]))["id"]
            esperar_container(cid)
            sid = chamar("POST", f"{ig}/media_publish", creation_id=cid)["id"]
            log.append({"id": item["id"], "resultado": "story publicado", "story_id": sid, "aceitos": aceitos})
        except ErroAPI as e:
            item["ultimo_erro"] = str(e)
            restantes.append(item)
    PENDENTES.write_text(json.dumps(restantes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if log:
        with REGISTRO.parent.joinpath("stories.jsonl").open("a", encoding="utf-8") as f:
            for l in log:
                f.write(json.dumps({"quando": agora(), **l}, ensure_ascii=False) + "\n")
    print(json.dumps(log, ensure_ascii=False))


if __name__ == "__main__":
    main()
