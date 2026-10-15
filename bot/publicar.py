"""Publica no Instagram os posts da fila com status "publicar".

Regras:
  - só publica se config.json tiver "publicacao_ativa": true; senão marca "simulado"
    e registra o que teria acontecido (inclusive a decisão de collab)
  - exige revisão aprovada (post["revisao"]["aprovado"] == true) e arte renderizada
  - collab (regras do João, 15/10/2026):
      bombástica + instituição  -> instituição + @brasilforadacaverna
      bombástica                -> perfis padrão (BFC + Luz)
      instituição               -> só a instituição
      N-ésimo post, N % 3 == 0  -> perfis padrão
  - bombástica sai como Reels com música da biblioteca do Instagram (Audio API)
  - posts com collab entram em registro/collabs_pendentes.json; quando o convite é aceito,
    stories.py posta a versão vertical nos Stories
  - o token vai só no cabeçalho Authorization; nada da resposta bruta é gravado
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
ESTADO = RAIZ / "registro" / "estado.json"
REGISTRO = RAIZ / "registro" / "posts.jsonl"
PENDENTES = RAIZ / "registro" / "collabs_pendentes.json"
API = f"https://graph.facebook.com/{CONFIG['api']}"
PADRAO_TOKEN = re.compile(r"EAA[A-Za-z0-9]{20,}")


class ErroAPI(Exception):
    pass


def agora() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def limpar(txt: str) -> str:
    """Remove qualquer coisa com cara de token de mensagens de erro."""
    token = os.environ.get("IG_TOKEN", "")
    if token:
        txt = txt.replace(token, "[token]")
    return PADRAO_TOKEN.sub("[token]", txt)


def chamar(metodo: str, caminho: str, **params) -> dict:
    token = os.environ["IG_TOKEN"]
    r = requests.request(metodo, f"{API}/{caminho}", headers={"Authorization": f"Bearer {token}"},
                         data=params if metodo == "POST" else None,
                         params=params if metodo == "GET" else None, timeout=60)
    try:
        corpo = r.json()
    except ValueError:
        raise ErroAPI(limpar(f"HTTP {r.status_code}: resposta não-JSON"))
    if "error" in corpo:
        e = corpo["error"]
        raise ErroAPI(limpar(f"{e.get('code')}/{e.get('error_subcode')}: {e.get('message')}"))
    return corpo


def esperar_container(cid: str, limite: int = 120) -> None:
    fim = time.time() + limite
    while time.time() < fim:
        st = chamar("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise ErroAPI(f"container {st}")
        time.sleep(4)
    raise ErroAPI("container não ficou pronto a tempo")


def legenda_final(post: dict) -> str:
    tags = post.get("hashtags", [])
    if len(tags) != 5:
        raise ValueError(f"precisa de exatamente 5 hashtags, veio {len(tags)}")
    tags = [t if t.startswith("#") else f"#{t}" for t in tags]
    texto = post["legenda"].rstrip() + "\n\n" + " ".join(tags)
    if len(texto) > 2200:
        raise ValueError(f"legenda com {len(texto)} caracteres; o limite é 2200")
    return texto


def decidir_collab(post: dict, numero: int) -> list[str]:
    inst = (post.get("instituicao_ig") or post.get("universidade_ig") or "").lstrip("@").strip()
    bfc = CONFIG["collab_padrao"][0]
    if post.get("bombastica"):
        return [inst, bfc] if inst else list(CONFIG["collab_padrao"])
    if inst:
        return [inst]
    if numero % CONFIG["collab_a_cada"] == 0:
        return list(CONFIG["collab_padrao"])
    return []


def escolher_musica(busca: str | None) -> dict | None:
    """Busca na biblioteca do Instagram (Audio API). Sem termo, pega as músicas em alta."""
    params = {"audio_type": "music", "user_id": CONFIG["ig_user_id"]}
    if busca:
        params["search_query"] = busca
    dados = chamar("GET", "ig_audio", **params).get("data", [])
    if not dados and busca:
        dados = chamar("GET", "ig_audio", audio_type="music", user_id=CONFIG["ig_user_id"]).get("data", [])
    if not dados:
        return None
    m = dados[0]
    return {"audio_id": m.get("audio_id"), "titulo": m.get("title"), "artista": m.get("display_artist")}


def url_arte(pasta: str, arquivo: str) -> str:
    return f"{CONFIG['repo_raw']}/fila/{pasta}/{arquivo}"


def criar_e_publicar(post: dict, pasta: str, legenda: str, collab: list[str]) -> dict:
    ig = CONFIG["ig_user_id"]
    artes = [a["arquivo"] for a in post["render"]["artes"]]
    extra = {"collaborators": json.dumps(collab)} if collab else {}
    musica = None
    if post.get("bombastica") and post.get("render", {}).get("reels"):
        params = dict(media_type="REELS", video_url=url_arte(pasta, post["render"]["reels"]["video"]),
                      cover_url=url_arte(pasta, post["render"]["reels"]["capa"]),
                      share_to_feed="true", caption=legenda, **extra)
        try:
            musica = escolher_musica(post.get("musica_busca"))
        except ErroAPI:
            musica = None
        if musica and musica.get("audio_id"):
            params["audio_configuration"] = json.dumps({"audio_id": musica["audio_id"], "audio_volume": 100, "video_volume": 0})
        cid = chamar("POST", f"{ig}/media", **params)["id"]
        esperar_container(cid, limite=600)
        mid = chamar("POST", f"{ig}/media_publish", creation_id=cid)["id"]
        link = chamar("GET", mid, fields="permalink").get("permalink")
        return {"media_id": mid, "permalink": link, "musica": musica}
    if len(artes) == 1:
        cid = chamar("POST", f"{ig}/media", image_url=url_arte(pasta, artes[0]), caption=legenda, **extra)["id"]
    else:
        filhos = []
        for a in artes:
            f = chamar("POST", f"{ig}/media", image_url=url_arte(pasta, a), is_carousel_item="true")["id"]
            esperar_container(f)
            filhos.append(f)
        cid = chamar("POST", f"{ig}/media", media_type="CAROUSEL", children=",".join(filhos), caption=legenda, **extra)["id"]
    esperar_container(cid)
    mid = chamar("POST", f"{ig}/media_publish", creation_id=cid)["id"]
    link = chamar("GET", mid, fields="permalink").get("permalink")
    return {"media_id": mid, "permalink": link}


def processar(arq: Path, estado: dict) -> None:
    post = json.loads(arq.read_text(encoding="utf-8"))
    pasta = arq.parent.name
    res = {"quando": agora()}
    try:
        if post.get("status") != "publicar":
            return
        if not post.get("revisao", {}).get("aprovado"):
            raise ValueError("revisão independente não aprovou este post")
        if not post.get("render", {}).get("artes"):
            raise ValueError("post sem arte renderizada")
        legenda = legenda_final(post)

        numero = estado["publicados"] + 1
        collab = decidir_collab(post, numero)
        res["numero"] = numero
        res["collab"] = collab
        res["formato"] = "reels" if post.get("bombastica") else ("carrossel" if len(post["render"]["artes"]) > 1 else "feed")

        if not CONFIG.get("publicacao_ativa"):
            post["status"] = "simulado"
            res["obs"] = "publicação desligada em config.json; nada foi enviado ao Instagram"
        else:
            try:
                res.update(criar_e_publicar(post, pasta, legenda, collab))
            except ErroAPI as e:
                if collab and "collab" in str(e).lower():  # cobre "collaborator(s)"
                    res["collab_erro"] = str(e)
                    res["collab"] = []
                    res.update(criar_e_publicar(post, pasta, legenda, []))
                else:
                    raise
            post["status"] = "publicado"
            estado["publicados"] = numero
            if res.get("collab") and post.get("render", {}).get("story"):
                pend = json.loads(PENDENTES.read_text(encoding="utf-8")) if PENDENTES.exists() else []
                pend.append({"id": pasta, "media_id": res["media_id"], "quando": res["quando"],
                             "convidados": res["collab"], "story": post["render"]["story"]})
                PENDENTES.write_text(json.dumps(pend, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            with REGISTRO.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "id": pasta, "quando": res["quando"], "numero": numero, "editoria": post.get("editoria"),
                    "titulo": post.get("titulo") or post.get("slides", [{}])[0].get("titulo"),
                    "permalink": res.get("permalink"), "media_id": res.get("media_id"),
                    "collab": res.get("collab"), "formato": res.get("formato"),
                    "bombastica": bool(post.get("bombastica")), "musica": res.get("musica"),
                    "fontes": post.get("fontes", []),
                    "corrige": post.get("corrige"),
                }, ensure_ascii=False) + "\n")
    except Exception as e:
        post["status"] = "erro_publicacao"
        res["erro"] = limpar(f"{type(e).__name__}: {e}")
    post["publicacao"] = res
    arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{pasta}: {post['status']} {res.get('permalink') or res.get('erro') or res.get('obs','')}")


def main() -> None:
    estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    alvos = sorted((RAIZ / "fila").glob("*/post.json"))
    for arq in alvos:
        processar(arq, estado)
    ESTADO.write_text(json.dumps(estado, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
