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
    alertas.py avisa o João no celular (ntfy) para ele compartilhar nos Stories pelo app
  - o token vai só no cabeçalho Authorization; nada da resposta bruta é gravado
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = json.loads((RAIZ / "config.json").read_text(encoding="utf-8"))
ESTADO = RAIZ / "registro" / "estado.json"
REGISTRO = RAIZ / "registro" / "posts.jsonl"
PENDENTES = RAIZ / "registro" / "collabs_pendentes.json"
API = f"https://graph.facebook.com/{CONFIG['api']}"
# Anti-spam da Meta (4/2207051): a API responde erro mas quase sempre publica. Regra do João
# (15/10/2026): notícia sai na hora, sem pausas longas. O publicador faz o que ele fazia à mão:
# confere se saiu e, se não saiu, "tenta novamente" (até 2 vezes, com espera curta), sem nunca
# duplicar: confere o perfil e o status do container antes de cada nova tentativa.
TENTATIVAS_EXTRA = 2
ESPERA_TENTATIVA_S = [60, 150]
AVISOS = RAIZ / "registro" / "avisos_api.jsonl"
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
        trans = " (transitório)" if e.get("is_transient") else ""
        raise ErroAPI(limpar(f"{e.get('code')}/{e.get('error_subcode')}: {e.get('message')}{trans}"))
    return corpo


def esperar_container(cid: str, limite: int = 180) -> None:
    fim = time.time() + limite
    time.sleep(8)  # o container quase nunca fica pronto antes disso; evita martelar a API
    while time.time() < fim:
        st = chamar("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise ErroAPI(f"container {st}")
        time.sleep(7)
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


ARQUIVOS_VISUAIS = ["bot/arte.py", "bot/render.py"]


def impressao_visual() -> str:
    """sha256 do gerador de arte + renderizador + fontes + textura. Muda se qualquer um mudar."""
    import hashlib
    h = hashlib.sha256()
    arquivos = [RAIZ / a for a in ARQUIVOS_VISUAIS] + sorted((RAIZ / "assets").rglob("*"))
    for a in arquivos:
        if a.is_file():
            h.update(a.relative_to(RAIZ).as_posix().encode())
            h.update(a.read_bytes())
    return h.hexdigest()[:16]


def avisar_celular(titulo: str, mensagem: str) -> None:
    topico = os.environ.get("NTFY_TOPIC", "").strip()
    if topico:
        try:
            requests.post("https://ntfy.sh/", json={"topic": topico, "title": titulo, "message": mensagem,
                                                    "tags": ["warning"], "priority": 5}, timeout=20)
        except Exception:
            pass


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


def recentes(n: int = 5) -> list[dict]:
    return chamar("GET", f"{CONFIG['ig_user_id']}/media", fields="id,caption,timestamp,permalink", limit=n).get("data", [])


def ja_no_perfil(legenda: str) -> dict | None:
    """Antes de publicar: o mesmo texto já está entre os últimos posts? (evita duplicata)"""
    alvo = " ".join(legenda.split())[:80]
    for m in recentes(8):
        if " ".join((m.get("caption") or "").split())[:80] == alvo:
            return {"media_id": m["id"], "permalink": m.get("permalink"),
                    "aviso_api": "o post já estava no perfil antes desta tentativa; nada foi reenviado"}
    return None


def ja_saiu(legenda: str, desde: float) -> dict | None:
    """Procura no perfil um post com a mesma legenda publicado depois de `desde` (epoch).
    A API às vezes devolve erro (ex.: 4/2207051) e publica assim mesmo."""
    alvo = " ".join(legenda.split())[:80]
    for _ in range(3):
        time.sleep(15)
        for m in recentes(5):
            t = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").timestamp()
            if t >= desde - 60 and " ".join((m.get("caption") or "").split())[:80] == alvo:
                return {"media_id": m["id"], "permalink": m.get("permalink")}
    return None


def publicar_container(cid: str, legenda: str) -> dict:
    import random
    time.sleep(random.uniform(20, 45))  # não publicar no mesmo segundo em que o container fica pronto
    inicio = time.time()
    erros = []
    for tentativa in range(1 + TENTATIVAS_EXTRA):
        try:
            mid = chamar("POST", f"{CONFIG['ig_user_id']}/media_publish", creation_id=cid)["id"]
            link = chamar("GET", mid, fields="permalink").get("permalink")
            res = {"media_id": mid, "permalink": link}
            if erros:
                res["aviso_api"] = f"publicado na {tentativa + 1}ª tentativa (antes: {'; '.join(erros)})"
            return res
        except ErroAPI as e:
            erros.append(str(e))
            achado = ja_saiu(legenda, inicio)
            if achado:
                achado["aviso_api"] = f"a API devolveu erro ({e}), mas o post saiu; conferido no perfil"
                return achado
            if tentativa >= TENTATIVAS_EXTRA:
                raise
            # "tentar novamente": espera curta e, antes, confirma que o container não foi usado
            time.sleep(ESPERA_TENTATIVA_S[tentativa])
            try:
                st = chamar("GET", cid, fields="status_code").get("status_code")
            except ErroAPI:
                st = None
            achado = ja_saiu(legenda, inicio)
            if achado:
                achado["aviso_api"] = f"a API devolveu erro ({e}), mas o post saiu; conferido no perfil"
                return achado
            if st == "PUBLISHED":
                raise ErroAPI(f"container já publicado mas o post não apareceu no perfil ({e}); conferir à mão")
            if st in ("ERROR", "EXPIRED"):
                raise
    raise ErroAPI("; ".join(erros))


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
        return {**publicar_container(cid, legenda), "musica": musica}
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
    return publicar_container(cid, legenda)


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

        # intervalo mínimo entre publicações (a Meta marcou como possível spam publicar em sequência)
        ultimo = estado.get("ultima_publicacao")
        if ultimo and CONFIG.get("publicacao_ativa"):
            t_ult = datetime.strptime(ultimo, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            minimo = timedelta(minutes=CONFIG.get("intervalo_minimo_min", 45))
            liberado = t_ult + minimo
            # depois de um aviso 2207051 (Meta desconfiou de spam, mas publicou), espaça mais o próximo
            if datetime.now(timezone.utc) < liberado:
                quando = liberado.strftime("%Y-%m-%dT%H:%M:%SZ")
                post["status"] = "agendado"
                post["publicar_apos"] = quando
                res["obs"] = f"intervalo mínimo entre posts: reagendado para {quando}"
                post["publicacao"] = res
                arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                print(f"{pasta}: agendado {quando} (intervalo mínimo)")
                return
        # teto diário (dia de Brasília)
        hoje_brt = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%d")
        if estado.get("dia") != hoje_brt:
            estado["dia"], estado["hoje"] = hoje_brt, 0
        teto = CONFIG.get("max_posts_dia", 8)
        if CONFIG.get("publicacao_ativa") and estado.get("hoje", 0) >= teto:
            quando = (datetime.strptime(hoje_brt, "%Y-%m-%d") + timedelta(days=1, hours=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
            post["status"] = "agendado"
            post["publicar_apos"] = quando
            res["obs"] = f"teto de {teto} posts/dia atingido: reagendado para {quando}"
            post["publicacao"] = res
            arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{pasta}: agendado {quando} (teto diário)")
            return
        numero = estado["publicados"] + 1
        collab = decidir_collab(post, numero)
        res["numero"] = numero
        res["collab"] = collab
        res["formato"] = "reels" if post.get("bombastica") else ("carrossel" if len(post["render"]["artes"]) > 1 else "feed")

        if not CONFIG.get("publicacao_ativa"):
            post["status"] = "simulado"
            res["obs"] = "publicação desligada em config.json; nada foi enviado ao Instagram"
        else:
            achado = ja_no_perfil(legenda)
            try:
                res.update(achado or criar_e_publicar(post, pasta, legenda, collab))
            except ErroAPI as e:
                if collab and "collab" in str(e).lower():  # cobre "collaborator(s)"
                    res["collab_erro"] = str(e)
                    res["collab"] = []
                    res.update(criar_e_publicar(post, pasta, legenda, []))
                else:
                    raise
            post["status"] = "publicado"
            estado["publicados"] = numero
            estado["ultima_publicacao"] = agora()
            estado["hoje"] = estado.get("hoje", 0) + 1
            if "2207051" in str(res.get("aviso_api", "")):
                with AVISOS.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"quando": agora(), "id": pasta, "publicado": True,
                                        "aviso": res["aviso_api"][:200]}, ensure_ascii=False) + "\n")
            if res.get("collab"):
                pend = json.loads(PENDENTES.read_text(encoding="utf-8")) if PENDENTES.exists() else []
                pend.append({"id": pasta, "media_id": res["media_id"], "quando": res["quando"],
                             "convidados": res["collab"], "permalink": res.get("permalink"),
                             "titulo": post.get("titulo") or (post.get("slides") or [{}])[0].get("titulo")})
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
        if "2207051" in res["erro"]:
            with AVISOS.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"quando": agora(), "id": pasta, "publicado": False,
                                    "aviso": res["erro"][:200]}, ensure_ascii=False) + "\n")
    post["publicacao"] = res
    arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{pasta}: {post['status']} {res.get('permalink') or res.get('erro') or res.get('obs','')}")


def main() -> None:
    aprovada, atual = CONFIG.get("visual_aprovado"), impressao_visual()
    if CONFIG.get("publicacao_ativa") and aprovada and aprovada != atual:
        msg = (f"O código visual mudou sem aprovação (esperado {aprovada}, atual {atual}). "
               "Nada foi publicado. Fale com o Claude para revisar e reaprovar o visual.")
        print("TRAVA VISUAL:", msg)
        avisar_celular("CBR: publicação travada", msg)
        for arq in sorted((RAIZ / "fila").glob("*/post.json")):
            post = json.loads(arq.read_text(encoding="utf-8"))
            if post.get("status") == "publicar":
                post["status"] = "erro_publicacao"
                post["publicacao"] = {"quando": agora(), "erro": msg}
                arq.write_text(json.dumps(post, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    estado = json.loads(ESTADO.read_text(encoding="utf-8"))
    alvos = sorted((RAIZ / "fila").glob("*/post.json"))
    for arq in alvos:
        processar(arq, estado)
    ESTADO.write_text(json.dumps(estado, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
