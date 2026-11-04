---
name: carrossel-cbr
description: >-
  Escolher a estrutura e escrever os slides de um carrossel da CBR (notícia, explicação, direito,
  contradição), com as regras que evitam palavra órfã e slide que não se sustenta sozinho. Use
  depois de aprovar a pauta como carrossel e antes do primeiro render.
---

# carrossel-cbr

Adaptado das cinco estruturas de carrossel do `social` (marketingskills, MIT) para notícia, em
português, para quem trabalha. Vale junto com o MANUAL.md (seção 2, "Formato") e com a skill
`titulo-cbr` (a capa é um título). **Nunca muda fato, número ou atribuição apurados.**

## Antes de começar: é mesmo carrossel?

Os carrosséis custaram caro e renderam pouco. Em 02/11, três foram feitos, dois caíram por palavra
órfã depois de 3 ou 4 renders, e o que saiu teve 4 de alcance (os Reels do dia fizeram média de 61).
Carrossel só quando a notícia **precisa** de partes: P ≥ 2 e I + V ≥ 5 (manual). Se o valor está no
choque do fato, é Reels.

## Duas regras que valem para todas as estruturas

1. **O slide 1 compete sozinho no feed.** Ele entrega o fato principal (quem, o quê, quanto), como
   manda a regra de 29/10. Nunca esconda a notícia para forçar o deslize.
2. **Cada slide sobrevive sozinho.** Se dois slides dizem a mesma coisa, junte os dois. Um
   carrossel enxuto de 5 vale mais que um inchado de 8.

## Escolha a estrutura antes de escrever

| A notícia é... | Estrutura | Por que a pessoa desliza |
|---|---|---|
| uma lista de mudanças, pontos ou números | **A. Entenda em N pontos** | o número da capa é uma promessa que dá para conferir |
| um dado forte que tem documento por trás | **B. O número e a prova** | a capa afirma, o último slide mostra a prova |
| um direito com prazo e caminho | **C. Seu direito passo a passo** | ver o caminho inteiro antes faz terminar |
| um político ou empresa dizendo uma coisa e fazendo outra | **D. Discurso x prática** | cada slide aumenta a contradição, e o slide do "outro lado" a torna justa |

### A. Entenda em N pontos (4 a 7 slides)

| Slide | Função | Tipo no post.json |
|---|---|---|
| 1, capa | o fato e o número exato de pontos: "Fim da 6x1: *4 coisas* que mudam no seu contracheque" | `capa` |
| 2 a N | um ponto por slide, com o dado que o sustenta | `texto` ou `lista` |
| último escrito | o que fazer ou o que vem depois (data, votação, prazo) | `texto` |

O número da capa é o número real de pontos. Nunca encha para chegar a um número maior.

### B. O número e a prova (4 a 6 slides)

| Slide | Função | Tipo |
|---|---|---|
| 1, capa | o número em destaque: "*84,2 milhões* de brasileiros com contas atrasadas" | `capa` |
| 2 | quem é afetado e por quê, em uma frase | `texto` |
| 3 a N−1 | o número comparado: antes e depois, por região, por renda (barras quando houver série) | `barras` ou `lista` |
| último escrito | **a prova**: de onde vem o dado (órgão, pesquisa, decisão), com data | `texto`, com `fonte` |

O último slide fecha o que a capa abriu. É aqui que a fonte primária aparece por extenso, o que
também protege a página de acusação de inventar número.

### C. Seu direito passo a passo (5 a 7 slides)

| Slide | Função | Tipo |
|---|---|---|
| 1, capa | o direito e o prazo: "Patrão tem até *30 de novembro* para pagar a 1ª parcela do 13º" | `capa` |
| 2 | **o mapa antes dos passos**: "3 passos, até 30/11" (quem tem direito, como conferir, o que fazer se não pagar) | `lista` |
| 3 a N | um passo por slide, com o órgão ou o canal de verdade (app, telefone, sindicato) | `texto` |

Ver o caminho inteiro no slide 2 é o que faz a pessoa ir até o fim. Só entra passo confirmado em
fonte oficial (órgão, lei, nota do ministério).

### D. Discurso x prática (4 a 6 slides)

| Slide | Função | Tipo |
|---|---|---|
| 1, capa | a contradição em uma frase: o que disse e o que fez, com data | `capa` |
| 2 a N−2 | os fatos, um por slide, cada um com fonte: o voto, o gasto, a fala | `texto` ou `barras` |
| N−1, o outro lado | **o que eles dizem**: a resposta, a negativa ou a justificativa (seção 3 do manual) | `texto` |
| último escrito | o que isso muda para quem trabalha | `texto` |

O slide do outro lado não é opcional. Ele torna a crítica justa, se adianta ao comentário hostil e
cumpre a regra de que toda acusação traz a negativa do acusado. Deboche só com o político e só na
legenda (seção 8).

## Regras de texto dos slides (o `conferir_titulo.py` confere)

- Capa: as regras do `titulo-cbr` (8 a 14 palavras, destaque no número).
- Slides internos: **título com até 10 palavras.** Título longo é o que mais gera palavra órfã, a
  causa dos descartes de 02/11.
- 4 a 8 slides escritos. **Não escreva slide de fechamento** ("siga", "salve", "mande"): o render
  acrescenta sozinho o último slide, com as fontes.
- Número com unidade junto ("42 horas", "R$ 1.412"), para não quebrar entre linhas.
- O campo `fonte` em todo slide que traz número.

Antes do push:
```bash
python bot/conferir_titulo.py fila/<id>/post.json
```
Corrija os `x`. Cada render a menos é crédito economizado.

## O que esta skill não faz

Não decide se a pauta sai, não apura e não substitui as duas revisões. Se a estrutura pedir um dado
que a apuração não tem (o passo 3, o número da região), corte o slide: nunca invente.
