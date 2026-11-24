"""Checagem da rodada curta (regra do João, 26/10/2026, para gastar menos).

Roda no começo de toda rodada, ANTES de ler o MANUAL.md. Lê só arquivos pequenos do repositório
(radar/triagem.json, fila/*/post.json, pautas/acompanhamento.json) e diz se a rodada pode terminar cedo.

Uso: python bot/rodada_curta.py            (janela padrão: 65 min)
     python bot/rodada_curta.py --janela 125

Saída: a primeira linha é "VEREDITO: CURTA" ou "VEREDITO: COMPLETA"; depois os motivos e, em poucas
linhas, os itens que a rodada precisa olhar (candidatos novos, rebaixados/descartes quentes a conferir).
Candidato descartado hoje por uma rodada completa (campo "descartes" de registro/rodadas.jsonl, gravado pelo
bot/registrar_rodada.py --descarte) não conta como novo nem como "esquentou", a não ser que tenha ganhado
veículos desde o descarte (pelo menos GANHO_MINIMO e 10%). Ele aparece numa linha "já descartado hoje".
Na rodada curta grava uma linha em registro/rodadas.jsonl (bot/registrar_rodada.py); a rodada completa
chama o bot/registrar_rodada.py no fim, com os números dela.
"""
from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BRT = timezone(timedelta(hours=-3))
PENDENTES = {"renderizar", "renderizado", "erro_render", "erro_publicacao", "publicar"}
GANHO_MINIMO = 2      # veículos novos que reabrem um candidato descartado hoje
SEMELHANCA = 0.7      # parte das palavras em comum para dizer que é a mesma manchete


def descartes_de_hoje(local: datetime) -> list[dict]:
    """Manchetes descartadas hoje (Brasília) pelas rodadas completas, com os veículos na hora do descarte."""
    from registrar_rodada import normalizar
    hoje, saida = local.strftime("%Y-%m-%d"), []
    try:
        linhas = (RAIZ / "registro/rodadas.jsonl").read_text(encoding="utf-8").splitlines()
    except Exception:
        return saida
    for ln in linhas:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if not str(r.get("hora_brasilia", "")).startswith(hoje):
            continue
        for d in r.get("descartes", []) or []:
            saida.append({"palavras": set(normalizar(d.get("manchete", "")).split()),
                          "veiculos": d.get("veiculos")})
    return saida


def ja_descartado(c: dict, descartes: list[dict]) -> bool:
    """True se a manchete foi descartada hoje e não ganhou veículos que justifiquem reabrir."""
    from registrar_rodada import normalizar
    p = set(normalizar(c.get("manchete", "")).split())
    if not p:
        return False
    for d in descartes:
        q = d["palavras"]
        if not q or len(p & q) / max(len(p), len(q)) < SEMELHANCA:
            continue
        antes, agora = d.get("veiculos"), c.get("veiculos")
        if antes is None or agora is None:
            return True
        if agora - antes < max(GANHO_MINIMO, antes * 0.10):
            return True
    return False


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def ler(caminho: Path):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--janela", type=int, default=65, help="minutos desde a rodada anterior")
    args = ap.parse_args()

    agora = datetime.now(timezone.utc)
    corte = iso(agora - timedelta(minutes=args.janela))
    local = agora.astimezone(BRT)
    motivos: list[str] = []
    olhar: list[str] = []

    # 1. tarefas fixas do horário
    if local.hour == 18:
        motivos.append("rodada das 18h: preparar o calendário de amanhã")
    if local.hour == 23:
        motivos.append("rodada das 23h: dossiê do dia")
    if local.weekday() == 0 and local.hour == 8:
        motivos.append("segunda, 1ª rodada depois das 7h40: resumo do relatório semanal")

    # 1b. saúde do token (registro/saude.json, checagem das 6h40)
    sd = ler(RAIZ / "registro/saude.json")
    if not sd:
        motivos.append("registro/saude.json ausente: avise o João")
    else:
        if not sd.get("ok"):
            motivos.append(f"saúde com problema: {sd.get('problemas')} (avise o João, 1x por dia; não publique)")
        q = sd.get("quando") or "2000-01-01T00:00:00Z"
        if q < iso(agora - timedelta(hours=26)):
            motivos.append("saude.json com mais de 26 h: dispare manutencao.yml (tarefa=saude)")

    # 2. fila
    for f in sorted(glob.glob(str(RAIZ / "fila/*/post.json"))):
        p = ler(Path(f)) or {}
        st, pid = p.get("status"), Path(f).parent.name
        if st in PENDENTES:
            motivos.append(f"fila: {pid} está em '{st}'")
        elif st == "agendado" and (p.get("publicar_apos") or "9999") <= iso(agora):
            motivos.append(f"fila: {pid} agendado com horário vencido")

    # 3. pauta de acompanhamento
    ac = ler(RAIZ / "pautas/acompanhamento.json")
    itens = ac if isinstance(ac, list) else (ac or {}).get("itens", (ac or {}).get("eventos", []))
    for e in itens or []:
        if e.get("status") == "aguardando" and (e.get("quando") or "9999") <= iso(agora):
            motivos.append(f"acompanhamento vencido: {str(e.get('evento'))[:90]}")

    # 4. triagem
    t = ler(RAIZ / "radar/triagem.json")
    if not t:
        motivos.append("triagem ausente ou ilegível: caminho antigo do manual")
    else:
        idade = (agora - datetime.strptime(t["quando"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc))
        if not t.get("ok"):
            motivos.append(f"triagem com erro ({t.get('erro')}): caminho antigo do manual")
        if idade > timedelta(minutes=70):
            motivos.append(f"triagem velha ({int(idade.total_seconds() // 60)} min): dispare o radar e rode de novo")
        ia = t.get("ia") or {}
        if isinstance(ia, dict) and ia.get("ok") is False:
            olhar.append(f"Gemini fora do ar ({ia.get('erro')}): dê você a nota aos candidatos")
        descartes = descartes_de_hoje(local)
        repetidos: list[dict] = []

        def filtrar(lista: list[dict]) -> list[dict]:
            fica = []
            for c in lista:
                if ja_descartado(c, descartes):
                    if c not in repetidos:
                        repetidos.append(c)
                else:
                    fica.append(c)
            return fica

        novos = filtrar([c for c in t.get("candidatos", []) if (c.get("na_pauta_desde") or "") >= corte])
        obrig = filtrar([c for c in t.get("obrigatorios", []) if (c.get("na_pauta_desde") or "") >= corte])
        quentes = filtrar([c for c in t.get("candidatos", []) + t.get("obrigatorios", []) if c.get("esquentou")])
        if novos:
            motivos.append(f"{len(novos)} candidato(s) novo(s) na triagem")
        if obrig:
            motivos.append(f"{len(obrig)} obrigatório(s) novo(s) (BFC/Luz/movimentos)")
        if quentes:
            motivos.append(f"{len(quentes)} assunto(s) esquentou(aram)")
        for c in novos + obrig + quentes:
            ia_c = c.get("ia") or {}
            nota = f"I{ia_c.get('I')} V{ia_c.get('V')} P{ia_c.get('P')}" if ia_c else "sem nota"
            par = (c.get("parceiro") or {}).get("perfil", "")
            olhar.append(f"- {(c.get('manchete') or '')[:110]} | {c.get('veiculos')} veíc. ({c.get('veiculos_3h')} em 3 h)"
                         f" | {nota}{' | ' + par if par else ''}")
        for c in repetidos:
            olhar.append(f"- já descartado hoje (sem veículos novos; ignore): {(c.get('manchete') or '')[:110]}"
                         f" | {c.get('veiculos')} veíc.")
        # resgates possíveis: o Gemini ou a regra tiraram algo com muitos veículos nas últimas 3 h
        resg = filtrar([c for c in t.get("rebaixados", [])
                        if (c.get("na_pauta_desde") or "") >= corte and c.get("veiculos_3h", 0) >= 3
                        and not (c.get("ia") or {}).get("repetido")])
        # descartes da regra não têm data de entrada: aparecem para conferir, mas não impedem a rodada curta
        desc = [c for c in t.get("descartados_mais_quentes", [])
                if c.get("veiculos_3h", 0) >= 5 and "internacional" not in str(c.get("motivo", ""))
                and "crime" not in str(c.get("motivo", ""))]
        for c in desc:
            olhar.append(f"- descarte quente (só olhe a manchete; já publicado ou velho = ignore): "
                         f"{(c.get('manchete') or '')[:110]} | {c.get('veiculos_3h')} em 3 h")
        if resg:
            motivos.append(f"{len(resg)} rebaixado(s)/descarte(s) quente(s) a conferir")
            for c in resg:
                olhar.append(f"- conferir: {(c.get('manchete') or '')[:110]} | {c.get('veiculos_3h')} em 3 h"
                             f" | {c.get('motivo') or (c.get('ia') or {}).get('motivo', '')}"[:200])

    if not motivos:  # rodada curta: grava a linha sozinha (registro de rodadas, 04/11/2026)
        from registrar_rodada import registrar
        ia = (t or {}).get("ia") if t else None
        registrar("curta", ia_ok=ia.get("ok") if isinstance(ia, dict) else None,
                  obs="triagem sem candidatos novos")
    print("VEREDITO: " + ("COMPLETA" if motivos else "CURTA"))
    print(f"agora {local:%d/%m %Hh%M} (Brasília) · janela desde {corte}")
    for m in motivos:
        print("* " + m)
    for o in olhar[:25]:
        print(o)
    if not motivos:
        print("Triagem sem candidatos novos e sem pendências: encerre a rodada sem ler o manual nem buscar na web.")


if __name__ == "__main__":
    main()
