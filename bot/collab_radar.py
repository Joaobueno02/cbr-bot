"""Radar de collab: acha páginas progressistas abertas a parceria (pedido do João, 16/10/2026).

O movimento de "esquerda ajuda esquerda": páginas como a BFC e a Luz postam chamadas do tipo
"chama a gente na collab", "divulgue sua página progressista aqui", #esquerdasegueesquerda.
Este script, 2 vezes por dia (alertas.yml, 11h40 e 19h40):

1. Lê as legendas que já temos (radar/parceiros.json, radar/movimentos.json) e, numa chamada
   por perfil, os posts recentes das páginas progressistas conhecidas (lista em
   radar/collab_paginas.json), procurando CHAMADAS de collab/divulgação.
2. Tenta a busca por hashtag da API (#esquerdasegueesquerda etc.). Se a conta não tiver
   permissão para busca de hashtag, registra e segue sem ela.
3. Descobre páginas novas: quem aparece marcado (@) nos posts de "sigam páginas de esquerda" e
   quem fez collab com a BFC/Luz/movimentos; mede seguidores (até 8 perfis novos por rodada).
4. Grava radar/collab_oportunidades.json e manda alerta no celular do João (ntfy) para cada
   chamada nova de collab (até 4 por dia), com o link: é ele quem comenta/manda direct.

A API não deixa comentar no post dos outros nem mandar direct: o contato é sempre do João.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publicar import CONFIG, RAIZ, ErroAPI, agora, chamar  # noqa: E402

BRT = timezone(timedelta(hours=-3))
SAIDA = RAIZ / "radar" / "collab_oportunidades.json"
PAGINAS = RAIZ / "radar" / "collab_paginas.json"
HASHTAGS = ["esquerdasegueesquerda", "esquerdaunida", "paginasdeesquerda"]
CHAMADA = re.compile(
    r"(chama(r)? (a gente |nós |nos |)?(na|no|pra|para) (a )?colla?b|bora (de |fazer )?colla?b|aceita(mos)? colla?b|"
    r"colla?b(s)? (aberta|aberto)|fa(z|ça|zer) colla?b|"
    r"divulgu?e (a )?sua p[aá]gina|sigam p[aá]ginas (de esquerda|progressistas)|p[aá]ginas? progressistas? (aqui|nos coment)|"
    r"deix[ae] (o )?seu @|comenta (o )?seu @|marque? (uma|sua) p[aá]gina|esquerda (segue|ajuda) esquerda|"
    r"#esquerdasegueesquerda|engajamento (da|de) esquerda)", re.I)
MAX_ALERTAS_DIA = 4
MAX_NOVOS = 8
IGNORAR = {"comunabrasileira_"}


def _legendas_locais() -> list[dict]:
    posts = []
    for nome in ("parceiros.json", "movimentos.json"):
        arq = RAIZ / "radar" / nome
        if not arq.exists():
            continue
        for user, v in json.loads(arq.read_text(encoding="utf-8")).get("perfis", {}).items():
            for p in v.get("posts", []):
                posts.append({"perfil": user, "link": p.get("link"), "quando": p.get("quando"),
                              "legenda": p.get("legenda") or "", "dono": p.get("dono"),
                              "mencoes": p.get("mencoes", [])})
    return posts


def _posts_pagina(user: str) -> tuple[int | None, list[dict]]:
    r = chamar("GET", CONFIG["ig_user_id"],
               fields=f"business_discovery.username({user}){{followers_count,media.limit(15){{caption,permalink,timestamp,username}}}}")
    bd = r.get("business_discovery", {})
    posts = [{"perfil": user, "link": m.get("permalink"), "quando": m.get("timestamp"), "legenda": m.get("caption") or "",
              "dono": m.get("username"), "mencoes": sorted(set(re.findall(r"@([A-Za-z0-9_.]{3,30})", m.get("caption") or "")))}
             for m in bd.get("media", {}).get("data", [])]
    return bd.get("followers_count"), posts


def _hashtags(log: list) -> list[dict]:
    posts = []
    for tag in HASHTAGS:
        try:
            h = chamar("GET", "ig_hashtag_search", user_id=CONFIG["ig_user_id"], q=tag).get("data", [])
            if not h:
                continue
            r = chamar("GET", f"{h[0]['id']}/recent_media", user_id=CONFIG["ig_user_id"],
                       fields="caption,permalink,timestamp", limit=30).get("data", [])
            posts += [{"perfil": f"#{tag}", "link": m.get("permalink"), "quando": m.get("timestamp"),
                       "legenda": m.get("caption") or "", "dono": None,
                       "mencoes": sorted(set(re.findall(r"@([A-Za-z0-9_.]{3,30})", m.get("caption") or "")))} for m in r]
        except ErroAPI as e:
            log.append(f"hashtag #{tag}: {str(e)[:120]}")
            break  # sem permissão de busca por hashtag: não insiste nas outras
    return posts


def _recente(quando: str | None, horas: int = 48) -> bool:
    if not quando:
        return False
    try:
        t = datetime.strptime(quando[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return False
    return datetime.now(timezone.utc) - t < timedelta(hours=horas)


def rodar(enviar=None) -> dict:
    log: list[str] = []
    estado = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    paginas = json.loads(PAGINAS.read_text(encoding="utf-8")) if PAGINAS.exists() else {"paginas": {}}
    conhecidas = paginas.setdefault("paginas", {})
    for u in json.loads((RAIZ / "bot" / "referencias_paginas.json").read_text(encoding="utf-8"))["perfis"]:
        conhecidas.setdefault(u, {"origem": "referência", "seguidores": None})

    posts = _legendas_locais()
    # páginas progressistas conhecidas (fora as grandes de imprensa): as 10 lidas há mais tempo
    grandes = {"metropoles", "uolnoticias", "folhadespaulo", "cnnbrasil", "poder360", "brasilforadacaverna", "luzmanifesto"}
    fila = sorted((u for u in conhecidas if u not in grandes and u not in IGNORAR),
                  key=lambda u: conhecidas[u].get("lida") or "")[:10]
    for u in fila:
        try:
            seg, ps = _posts_pagina(u)
            conhecidas[u].update(seguidores=seg, lida=agora())
            posts += ps
        except ErroAPI as e:
            conhecidas[u].update(lida=agora(), erro=str(e)[:120])
    posts += _hashtags(log)

    # chamadas de collab das últimas 48 h
    vistas = set(estado.get("avisadas", []))
    chamadas = []
    for p in posts:
        if not _recente(p["quando"]) or not CHAMADA.search(p["legenda"]):
            continue
        trecho = " ".join(p["legenda"].split())
        m = CHAMADA.search(trecho)
        ini = max(0, m.start() - 80)
        chamadas.append({"perfil": p["perfil"], "link": p["link"], "quando": p["quando"],
                         "trecho": trecho[ini:ini + 220]})
    # páginas novas: marcadas nas chamadas e donos de collab com os parceiros
    candidatas = set()
    for p in posts:
        if CHAMADA.search(p["legenda"]) or (p.get("dono") and p["dono"] != p["perfil"]):
            candidatas |= set(p.get("mencoes", []))
            if p.get("dono") and p["dono"] != p["perfil"] and not str(p["perfil"]).startswith("#"):
                candidatas.add(p["dono"])
                conhecidas.setdefault(p["dono"], {"origem": f"fez collab com @{p['perfil']}", "seguidores": None})
    novas = [u for u in sorted(candidatas) if u not in conhecidas and u not in IGNORAR][:MAX_NOVOS]
    for u in novas:
        try:
            seg, _ = _posts_pagina(u)
            conhecidas[u] = {"origem": "marcada em chamada/collab de página de esquerda", "seguidores": seg, "lida": agora()}
        except ErroAPI as e:
            conhecidas[u] = {"origem": "marcada", "seguidores": None, "erro": str(e)[:120], "lida": agora()}

    # alertas no celular
    hoje = datetime.now(BRT).strftime("%Y-%m-%d")
    if estado.get("dia") != hoje:
        estado["dia"], estado["alertas_hoje"] = hoje, 0
    for c in sorted(chamadas, key=lambda c: c["quando"] or "", reverse=True):
        if c["link"] in vistas or estado["alertas_hoje"] >= MAX_ALERTAS_DIA or not enviar:
            continue
        ok = enviar("Collab: página chamando parceria",
                    f"@{c['perfil'].lstrip('@')}: \"{c['trecho'][:150]}\". Comente com o @ da CBR ou mande direct.",
                    c["link"], ["handshake"])
        if ok:
            vistas.add(c["link"])
            estado["alertas_hoje"] += 1

    estado.update(quando=agora(), chamadas=chamadas[:40], avisadas=sorted(vistas)[-300:], log=log,
                  paginas_progressistas=sorted(
                      ({"user": u, **{k: v for k, v in d.items() if k != "lida"}} for u, d in conhecidas.items()),
                      key=lambda x: -(x.get("seguidores") or 0))[:80])
    SAIDA.write_text(json.dumps(estado, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PAGINAS.write_text(json.dumps(paginas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"collab: {len(chamadas)} chamadas, {len(novas)} páginas novas, {len(conhecidas)} conhecidas; {log}")
    return estado


if __name__ == "__main__":
    rodar()
