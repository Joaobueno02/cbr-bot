"""Conferência do texto do post: título, chapéu, subtítulo e legenda como UM conjunto (04/11/2026).

Adaptado da ideia do yt-package (youtube-agent-skill, MIT): título e capa são uma unidade, e a
falha mais comum é as duas partes dizerem a mesma coisa. Na CBR o "par" é o que a pessoa vê antes
de decidir parar: chapéu + título da arte + primeira linha da legenda (a que aparece antes do
"mais", ~125 caracteres). Regras de 29/10 (texto feito para ser enviado) e de 04/11 (ângulo de
mobilização) também entram.

É um piso de qualidade, não uma previsão de alcance: nos posts de 03/11, os de 3 e de 725 de alcance
tiraram nota parecida. Nada aqui é grave: são avisos e sugestões para decidir ANTES do render (economiza render) e que o
conferir_design.py também grava em design_auto. Sem dependências fora da biblioteca padrão.

Uso:
  python bot/conferir_titulo.py fila/<id>/post.json
  python bot/conferir_titulo.py --titulo "Botijão de gás fica *R$ 0,91* mais caro em fevereiro" --chapeu "NO BOLSO"
  python bot/conferir_titulo.py titulos.txt         # um título por linha: ranqueia as opções
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

VISIVEL_LEGENDA = 125  # o Instagram corta a legenda no "mais" por volta daqui
VAGAS = ["chocante", "inacreditavel", "absurdo", "absurda", "bomba", "bombastico", "polemica", "surpreendente",
         "impressionante", "incrivel", "inedito", "historico", "historica", "urgente", "entenda", "saiba",
         "veja", "confira", "importante", "grave", "serio"]
INSTITUICOES = ["governo", "ministerio", "senado", "camara", "stf", "stj", "tse", "tcu", "comissao", "conselho",
                "tribunal", "prefeitura", "secretaria", "estados", "orgao", "agencia", "assembleia", "congresso"]
ENVIO = re.compile(r"\b(manda|mande|envia|envie|compartilh\w*|encaminh\w*|passa pra|passe pra|marca quem|marque)\b", re.I)
NUMERO = re.compile(r"\d")
DATA = re.compile(r"\b(\d{1,2}/\d{1,2}|\d{1,2} de (janeiro|fevereiro|marco|março|abril|maio|junho|julho|agosto|"
                  r"setembro|outubro|novembro|dezembro)|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo|"
                  r"amanha|amanhã|hoje)\b", re.I)
STOP = set("a o os as de da do das dos e em no na nos nas um uma uns umas para pra por com que se ao aos sobre "
           "apos após diz e é ser foi vai mais menos seu sua seus suas ele ela eles elas isso esse essa este esta "
           "como ja já nao não sem ate até entre quem".split())

# fórmulas de título da CBR (ver .claude/skills/titulo-cbr/SKILL.md); a classificação é sobre as
# palavras do título, não uma explicação de por que o post rendeu
FORMULAS = [
    ("prazo", re.compile(r"\b(ate|até|prazo|ultimo dia|último dia|termina|vence|a partir de|comeca|começa)\b", re.I)),
    ("povo x eles", re.compile(r"\d+\s?%.*\b(querem|quer|apoiam|defendem|favoravel|favoráveis|contra)\b|\b(trava|segura|engaveta|barra)\b", re.I)),
    ("bolso", re.compile(r"(r\$\s?\d|\d+\s?%|\bsalario|\bsalário|\bpreco|\bpreço|\bconta de|\bmais car[oa]|\baluguel|\b13º|\bfgts|\binss)", re.I)),
    ("quem paga a conta", re.compile(r"\b(demite|demitid\w*|corta|cortam|perde\w*|fecha|fecham|despej\w*|sem salario|sem salário)\b", re.I)),
    ("contradicao", re.compile(r"\b(mas|enquanto|depois de|apesar|mesmo após|mesmo apos|denuncia o brasil|pede ao stf|pede de volta)\b", re.I)),
    ("ironia ou frase", re.compile(r"[“\"].+[”\"]|\bironiza\b|\bdebocha\b", re.I)),
    ("desmentido", re.compile(r"\b(desmente|falso|fake|boato|mentira|nega)\b", re.I)),
    ("placar", re.compile(r"\b\d+\s?a\s?\d+\b", re.I)),
    ("vitoria de quem trabalha", re.compile(r"\b(conquista|vence|aprova|garante|cai para|reajuste|aumento|volta a)\b", re.I)),
    ("pergunta", re.compile(r"\?\s*$")),
]


def sem_acento(t: str) -> str:
    t = unicodedata.normalize("NFKD", t or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def limpo(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[*=|]", " ", t or "")).strip()


def palavras(t: str) -> list[str]:
    return re.findall(r"[a-z0-9$%º]+", sem_acento(limpo(t)))


def conteudo(t: str) -> set[str]:
    return {w for w in palavras(t) if len(w) > 2 and w not in STOP}


def sobreposicao(a: str, b: str) -> float:
    ca, cb = conteudo(a), conteudo(b)
    return len(ca & cb) / len(ca) if ca and cb else 0.0


def primeira_linha(legenda: str) -> str:
    for l in (legenda or "").splitlines():
        if l.strip():
            return l.strip()
    return ""


def formula(titulo: str) -> str | None:
    t = limpo(titulo)
    for nome, rx in FORMULAS:
        if rx.search(t):
            return nome
    return None


def conferir_texto(titulo: str, chapeu: str = "", subtitulo: str = "", legenda: str = "") -> dict:
    avisos, sugestoes, bons = [], [], []
    t = limpo(titulo)
    ws = t.split()
    n = len(ws)
    if n and not 8 <= n <= 14:
        avisos.append(f"título com {n} palavras (regra de 29/10: 8 a 14)")
    destaques = re.findall(r"\*([^*]+)\*", titulo or "")
    if not destaques:
        avisos.append("título sem destaque *...* (todo título tem um)")
    elif NUMERO.search(t) and not any(NUMERO.search(d) for d in destaques):
        sugestoes.append("o título tem número, mas o destaque não está nele: ponha o *número* em destaque")
    if not (NUMERO.search(t) or DATA.search(t) or any(w[:1].isupper() for w in ws[1:])):
        sugestoes.append("sem número, nome ou data: um dado concreto vence qualquer adjetivo")
    vagas = [w for w in palavras(t) if w in VAGAS]
    if vagas:
        avisos.append(f"palavra vaga no título ({', '.join(sorted(set(vagas)))}): troque pelo fato ou pelo número")
    caixa = [w for w in ws if len(w) > 2 and w.isupper() and not NUMERO.search(w)]
    if len(caixa) > 2:
        avisos.append(f"{len(caixa)} palavras em caixa alta no título (lê como spam a partir de 3)")
    if ws and sem_acento(ws[0]) in INSTITUICOES:
        sugestoes.append(f"abre pela instituição ('{ws[0]}'): teste abrir por quem é afetado ou pelo que muda no bolso")
    # o conjunto: cada parte acrescenta algo
    if chapeu:
        rep = conteudo(chapeu) & conteudo(titulo)
        if rep:
            avisos.append(f"chapéu repete o título ({', '.join(sorted(rep))}): o chapéu é o enquadramento, não a mesma palavra")
    if subtitulo and sobreposicao(titulo, subtitulo) >= 0.6:
        avisos.append("subtítulo repete o título: use-o para o dado que sustenta e a resposta do outro lado")
    if legenda:
        l1 = primeira_linha(legenda)
        if sobreposicao(titulo, l1) >= 0.6:
            avisos.append("a 1ª linha da legenda repete o título: ela é o que aparece antes do 'mais'; traga o fato seguinte")
        if len(l1) > VISIVEL_LEGENDA:
            sugestoes.append(f"1ª linha da legenda com {len(l1)} caracteres: o Instagram corta em ~{VISIVEL_LEGENDA}; "
                             "ponha o essencial antes disso")
        linhas = [l.strip() for l in legenda.splitlines() if l.strip()]
        corpo = [l for l in linhas if not l.lower().startswith(("fontes", "fonte:", "foto"))]
        if corpo and not any(ENVIO.search(l) for l in corpo[-2:]):
            avisos.append("legenda sem pedido de envio no fim (regra de 29/10: 'Manda pra quem...', variando a frase)")
    f = formula(titulo)
    if f:
        bons.append(f"fórmula: {f}")
    pontos = 100 - 15 * len(avisos) - 5 * len(sugestoes)
    return {"pontos": max(pontos, 0), "formula": f, "avisos": avisos, "sugestoes": sugestoes, "bons": bons}


def conferir_post(post: dict) -> dict:
    if post.get("formato") == "carrossel":
        capa = next((s for s in post.get("slides", []) if s.get("tipo") == "capa"), (post.get("slides") or [{}])[0])
        return conferir_texto(capa.get("titulo", ""), capa.get("chamada", ""), capa.get("texto", ""),
                              post.get("legenda", ""))
    return conferir_texto(post.get("titulo", ""), post.get("chapeu", ""), post.get("subtitulo", ""),
                          post.get("legenda", ""))


def mostrar(rotulo: str, r: dict) -> None:
    print(f"\n  {rotulo}\n    pontos {r['pontos']}  ·  fórmula: {r['formula'] or '-'}")
    for a in r["avisos"]:
        print(f"    x  {a}")
    for s in r["sugestoes"]:
        print(f"    ?  {s}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("arquivo", nargs="?", help="post.json ou .txt com um título por linha")
    ap.add_argument("--titulo")
    ap.add_argument("--chapeu", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.titulo:
        r = conferir_texto(a.titulo, a.chapeu)
        print(json.dumps(r, ensure_ascii=False)) if a.json else mostrar(a.titulo, r)
        return 0
    if not a.arquivo:
        ap.print_help()
        return 1
    p = Path(a.arquivo)
    if p.suffix == ".json":
        r = conferir_post(json.loads(p.read_text(encoding="utf-8")))
        print(json.dumps(r, ensure_ascii=False)) if a.json else mostrar(p.parent.name, r)
        return 0
    opcoes = [(l.strip(), conferir_texto(l.strip())) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    opcoes.sort(key=lambda x: -x[1]["pontos"])
    for t, r in opcoes:
        mostrar(t, r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
