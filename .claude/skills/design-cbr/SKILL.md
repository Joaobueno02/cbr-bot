---
name: design-cbr
description: >-
  A filosofia visual da CBR e a régua da revisão de design: o que faz uma arte ser da CBR e não um
  card de notícia genérico, os tokens (cor, tipo, layout) e as perguntas da revisão. Use em toda
  revisão de design (seção 6 do MANUAL) e antes de propor qualquer mudança visual.
---

# design-cbr

Escrita em 04/11/2026, a pedido do João, a partir das skills `frontend-design` e `canvas-design` da
Anthropic: as duas pedem uma filosofia visual curta, com nome, antes de desenhar, e que ela seja a
régua da revisão. **Esta skill não muda a arte.** O visual é travado (`visual_aprovado`); mudança de
`bot/arte.py`, `bot/render.py` ou `assets/` só por PR com antes e depois e aprovação do João.

## A filosofia: "Manchete de Fábrica"

A CBR fala com quem trabalha, e a arte vem do mesmo lugar que essa conversa sempre veio: o jornal de
sindicato, o boletim de porta de fábrica, o lambe-lambe colado no poste. Daí a serifa de manchete
(Fraunces) no título, o papel com grão por cima de tudo e o chapéu em caixa alta, que grita como a
manchete de banca. Não é estética de startup nem de portal: é impresso, direto, feito para ser lido de
pé, no ônibus, em dois segundos.

A foto é o fato e ocupa o alto da arte inteira; o texto assenta embaixo como a legenda de uma foto de
capa. Entre os dois, o degradê para o fundo da grade (preto nas editorias de poder, papel nas de bolso
e de serviço) é a dobra do jornal. Nada flutua solto: tudo encosta na margem esquerda, na mesma linha.

A ousadia mora num lugar só. Quando há chapéu, ele é a manchete e lidera; o destaque do título
acompanha, mais baixo. Quando não há chapéu, o destaque no número é o que fica na memória. Nunca os
dois gritando juntos.

Texto na arte é o mínimo para entender o fato: chapéu, título, uma frase de apoio de até 2 linhas. A
explicação mora na legenda. A linha de crédito, pequena, embaixo da barra, é a assinatura do jornal:
foto, fontes e data, porque "fato checado, fonte citada" é o diferencial declarado da página.

O acabamento tem de parecer feito à mão por quem conhece o ofício: nenhuma palavra sozinha na linha,
nenhum número partido, nada encostando na margem, a foto nítida e com o rosto inteiro. Arte "quase
certa" não sai.

## Tokens (o que está no `bot/arte.py`; não muda sem PR)

| Item | Valor |
|---|---|
| Grade preta (Política, Eleições, Gerais, América Latina) | fundo `#101010`, texto `#FFFFFF`, apoio `#C9C6C0` |
| Grade de papel (Economia, Educação, Saúde, da roça) | fundo `#ECEAE5` (roça `#F2EBDD`), texto `#101010`, apoio `#4E4B47` |
| Cor de cada editoria | Política e Gerais `#D0021B` · Eleições `#FED700` · Saúde `#087A6D` · América Latina `#FF5A1F` · Economia `#1646E0` · Educação `#56622C` · da roça `#4F7A1C` |
| Título | Fraunces, peso 640, até 60 px (encolhe até 44 para caber), entrelinha 1,05 |
| Chapéu | Fraunces, caixa alta, 60 a 66 px, na cor da editoria |
| Apoio | Archivo, 30 px, até 2 linhas |
| Crédito | Archivo 700, 14 px, caixa alta, uma linha embaixo da barra |
| Marca | lockup "EDITORIA + CBR" (Unbounded), CBR a 75% |
| Destaque | marca-texto inclinado na cor da editoria; mais leve (60%) quando há chapéu na grade preta |
| Papel | textura em todas as artes (sobreposição 35% na preta, multiplicação 16% na de papel) |

## A revisão de design: as perguntas

Além da lista da seção 6b do MANUAL, o revisor responde:

1. **Isto é CBR ou é um card de notícia qualquer?** Tape a marca: a arte ainda parece nossa (papel,
   serifa de manchete, chapéu, alinhamento)? Se parece a de qualquer portal, algo do post fugiu do padrão.
2. **Onde está a ousadia?** Um elemento lidera (o chapéu ou o destaque no número). Se dois disputam,
   aponte qual baixar (em geral, encurtar o destaque para só o número).
3. **O que dá para tirar?** (o conselho da Chanel, na `canvas-design`: antes de sair, tire um acessório.)
   Subtítulo que repete o título, destaque longo demais, chapéu de 3 palavras quando 2 bastam, um
   negrito a mais no apoio. Corte antes de acrescentar.
4. **Lê no tamanho do feed?** Reduza a arte para 360 px de largura e leia: chapéu e título têm de ser
   lidos; o apoio, de preferência.
5. **A foto conta o fato?** Rosto inteiro, olhar com espaço, sem logo de outro veículo, nítida.

## Clichês de design que não entram (da `frontend-design`, filtrados para a CBR)

- Rótulo que não informa nada acima do título (ex.: "FOTO: ..." em caixa alta no meio do bloco; desde
  04/11 o crédito fica só embaixo da barra).
- Mais de um destaque colorido no mesmo título.
- Emoji, seta ou ícone decorativo na arte.
- Moldura, sombra ou borda arredondada que a grade não usa.
- Texto centralizado (a CBR alinha à esquerda, como coluna de jornal).

O destaque de uma palavra na cor da editoria aparece na lista de clichês da `frontend-design`, mas
ali é sobre página web; na CBR ele é identidade aprovada pelo João e fica.
