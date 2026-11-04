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
# pedido de envio (o sinal que mais espalha) ou de salvar (post de prazo, direito, serviço); "marca quem" e
# "comenta" ficam de fora: pedir marcação é isca que o Instagram rebaixa (instagram-skills, MIT)
ENVIO = re.compile(r"\b(manda|mande|envia|envie|compartilh\w*|encaminh\w*|passa pra|passe pra|salva|salve|guarda)\b", re.I)
NUMERO = re.compile(r"\d")
DATA = re.compile(r"\b(\d{1,2}/\d{1,2}|\d{1,2} de (janeiro|fevereiro|marco|março|abril|maio|junho|julho|agosto|"
                  r"setembro|outubro|novembro|dezembro)|segunda|terca|terça|quarta|quinta|sexta|sabado|sábado|domingo|"
                  r"amanha|amanhã|hoje)\b", re.I)
STOP = set("a o os as de da do das dos e em no na nos nas um uma uns umas para pra por com que se ao aos sobre "
           "apos após diz e é ser foi vai mais menos seu sua seus suas ele ela eles elas isso esse essa este esta "
           "como ja já nao não sem ate até entre quem".split())

# "cara de IA" na legenda (adaptado da lista ai-tells do marketingskills, MIT, e da seção 8 do MANUAL)
IA_PROIBIDAS = ["ou seja", "em suma", "alem disso", "ademais", "nesse sentido", "vale ressaltar", "vale lembrar",
                "e importante destacar", "e importante ressaltar", "fundamental", "crucial", "significativo",
                "significativa", "no cenario atual", "cabe destacar", "nao e de hoje", "em meio a",
                # sinceridade encenada e clichê de rede (instagram-skills, scrub-rules, adaptado)
                "a verdade e que", "sejamos sinceros", "vamos combinar", "e sobre isso", "fica a reflexao",
                "e ta tudo bem", "simples assim", "pasmem", "acredite se quiser"]
IA_PADROES = [
    ("contraste encenado ('não é X, é Y')",
     re.compile(r"\bn[aã]o (e|é|foi|se trata de|era)\b[^.!?\n]{1,60}[,.;:]\s*(e|é|foi|era|mas)\b|\bn[aã]o s[oó]\b[^.!?\n]{1,60}\bmas (tamb[eé]m)?", re.I)),
    ("pergunta que o próprio texto responde ('O resultado? ...')",
     re.compile(r"(^|[.!\n]\s*)(o|a|os|as|e|e o|e a)\s+\w+(\s+\w+)?\?\s+\S", re.I)),
    ("revelação com dois-pontos ('O pior: ...')",
     re.compile(r"(^|[.!\n]\s*)(o|a)\s+(pior|melhor|detalhe|resumo|recado|segredo|problema|motivo|ponto)(\s+\w+)?:\s", re.I)),
    ("isca de engajamento ('Concorda?', 'Leia de novo')",
     re.compile(r"\b(concorda|faz sentido|leia de novo|leia outra vez|pensa nisso|reflita|comenta a[ií])\b\s*[?!.]"
                r"|\b(marca|marque) (quem|um amigo|uma amiga|\d)|\bo que voc[eê]s acham\b|\bcomente (sim|eu|aqui)\b", re.I)),
]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def conferir_legenda(legenda: str, hashtags: list | None = None) -> tuple[list[str], list[str]]:
    """Avisos e sugestões só da legenda: marcas de texto de IA, travessão, emoji, ritmo e hashtags."""
    avisos, sugestoes = [], []
    corpo = "\n".join(l for l in (legenda or "").splitlines() if not l.strip().lower().startswith(("fontes", "fonte:")))
    sa = sem_acento(corpo)
    achadas = sorted({w for w in IA_PROIBIDAS if re.search(rf"\b{w}\b", sa)})
    if achadas:
        avisos.append(f"expressões proibidas pela seção 8 do manual: {', '.join(achadas)}")
    for nome, rx in IA_PADROES:
        m = rx.search(corpo)
        if m:
            avisos.append(f"{nome}: \"{m.group(0).strip()[:60]}\"; diga a coisa direto, com o fato")
    trav = corpo.count("—") + corpo.count(" – ")
    if trav > 1:
        avisos.append(f"{trav} travessões na legenda: troque por ponto ou vírgula (no máximo 1)")
    emojis = EMOJI.findall(corpo)
    if len(emojis) > 2:
        avisos.append(f"{len(emojis)} emojis na legenda (manual: no máximo 1 ou 2)")
    linhas = [l.strip() for l in corpo.splitlines() if l.strip()]
    if sum(1 for l in linhas if EMOJI.match(l)) >= 3:
        avisos.append("emoji abrindo várias linhas, como marcador de lista: escreva em parágrafo")
    if len(linhas) >= 6 and sum(1 for l in linhas if len(l) < 60 and l.count(".") <= 1) / len(linhas) > 0.7:
        sugestoes.append("quase toda linha é uma frase curta solta: junte em parágrafos onde uma pessoa pausaria")
    if hashtags is not None:
        if len(hashtags) != 5:
            avisos.append(f"{len(hashtags)} hashtags (o manual pede exatamente 5: 3 do assunto, 1 da editoria, #ComunaBrasileira)")
        elif hashtags[-1] != "#ComunaBrasileira":
            sugestoes.append("a última hashtag deveria ser #ComunaBrasileira")
        if re.search(r"(^|\s)#\w", corpo):
            avisos.append("hashtag escrita dentro da legenda: elas vão só no campo hashtags")
    return avisos, sugestoes


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


def conferir_texto(titulo: str, chapeu: str = "", subtitulo: str = "", legenda: str = "",
                   hashtags: list | None = None) -> dict:
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
    if subtitulo and len(limpo(subtitulo)) > 110:
        sugestoes.append(f"subtítulo com {len(limpo(subtitulo))} caracteres: em 30 px cabem ~105 em 2 linhas; "
                         "deixe o dado principal e leve o resto para a legenda")
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
            avisos.append("legenda sem pedido de envio no fim (regra de 29/10: 'Manda pra quem...'; em post de prazo ou "
                          "direito, 'Salva pra não perder o prazo' também vale)")
        la, ls = conferir_legenda(legenda, hashtags)
        avisos += la
        sugestoes += ls
    f = formula(titulo)
    if f:
        bons.append(f"fórmula: {f}")
    pontos = 100 - 15 * len(avisos) - 5 * len(sugestoes)
    return {"pontos": max(pontos, 0), "formula": f, "avisos": avisos, "sugestoes": sugestoes, "bons": bons}


def conferir_post(post: dict) -> dict:
    if post.get("formato") == "carrossel":
        capa = next((s for s in post.get("slides", []) if s.get("tipo") == "capa"), (post.get("slides") or [{}])[0])
        r = conferir_texto(capa.get("titulo", ""), capa.get("chamada", ""), capa.get("texto", ""),
                           post.get("legenda", ""), post.get("hashtags"))
        r["avisos"] += conferir_slides(post.get("slides", []))
        return r
    return conferir_texto(post.get("titulo", ""), post.get("chapeu", ""), post.get("subtitulo", ""),
                          post.get("legenda", ""), post.get("hashtags"))


def conferir_slides(slides: list[dict]) -> list[str]:
    """Carrossel (skill carrossel-cbr): cada slide sobrevive sozinho, sem fechamento escrito à mão."""
    avisos = []
    if not 4 <= len(slides) <= 8:
        avisos.append(f"carrossel com {len(slides)} slides (manual: 4 a 8, sem contar o fechamento automático)")
    titulos = [limpo(x.get("titulo", "")) for x in slides]
    for i, t in enumerate(titulos[1:], start=2):
        if len(t.split()) > 10:
            avisos.append(f"slide {i}: título com {len(t.split())} palavras (até 10; título longo é o que mais gera órfã)")
        if re.search(r"\b(siga|salve|compartilhe|mande pra quem)\b", sem_acento(t)):
            avisos.append(f"slide {i}: parece slide de fechamento; o render já acrescenta o último slide sozinho")
    for i in range(1, len(titulos)):
        for j in range(i):
            if titulos[i] and titulos[j] and sobreposicao(titulos[i], titulos[j]) >= 0.7:
                avisos.append(f"slide {i + 1} repete o título do slide {j + 1}: junte os dois ou corte um")
    return avisos


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
