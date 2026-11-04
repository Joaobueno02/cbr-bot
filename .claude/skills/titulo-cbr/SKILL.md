---
name: titulo-cbr
description: >-
  Escrever e conferir título, chapéu, subtítulo e a 1ª linha da legenda de um post da CBR como um
  conjunto, com as fórmulas de título que funcionam na página. Use depois de aprovar a pauta e antes
  do primeiro render, em todo post único, Reels ou capa de carrossel.
---

# titulo-cbr

Adaptado do `yt-package` e das 21 fórmulas do `yt-script` (youtube-agent-skill, MIT), com partes do `marketing-psychology` (marketingskills, MIT), para notícia
no Instagram, em português, para quem trabalha. Vale junto com o MANUAL.md e com a regra de 29/10
("Texto feito para ser enviado"). **Nunca muda fato, número ou atribuição apurados**: a fórmula
escolhe o enquadramento, a apuração escolhe o conteúdo.

## O conjunto

O que a pessoa vê antes de decidir parar é um conjunto só: **chapéu + título da arte + 1ª linha da
legenda** (a que aparece antes do "mais", por volta de 125 caracteres). Cada parte acrescenta algo:

- **chapéu**: o enquadramento, em 1 a 3 palavras ("NO BOLSO", "DESMENTIDO", "PRAZO"). Não repete
  palavra do título.
- **título**: o fato, de 8 a 14 palavras, com um destaque `*...*`, de preferência no número.
- **subtítulo**: o dado que sustenta o título e a resposta do outro lado. Não repete o título.
- **1ª linha da legenda**: o fato seguinte (quem, quanto, quando), não o título de novo. O essencial
  cabe nos primeiros 125 caracteres.
- **fim da legenda**: o pedido de envio ligado ao assunto, variando a frase.

## Antes do título: o objetivo do post

O Instagram distribui pelo que a pessoa faz depois de ver, e os pesos não são iguais: **envio por DM**
pesa mais, depois **salvar**, depois comentário; a curtida pesa pouco (instagram-skills, MIT, a partir
das falas públicas do Instagram). Escolha **um** objetivo antes de escrever:

- **envio**: contradição, frase de efeito, detalhe ridículo, povo x eles, desmentido. A pergunta é:
  "a pessoa pensaria em alguém específico para mandar isto?" O fim da legenda pede o envio.
- **salvar**: prazo, direito, passo a passo, entenda. A pergunta é: "a pessoa vai voltar aqui depois?"
  O fim da legenda pede para salvar ("Salva pra não perder o prazo de 30/11").

Nunca peça marcação ("marque quem..."), "comente SIM" ou "o que vocês acham?": o Instagram rebaixa
isca de engajamento. A pergunta do primeiro comentário (`comentario`) continua valendo, porque pede
experiência, não clique.

## Escreva cinco, fique com um

1. Escreva **5 títulos** para a pauta aprovada, cada um com uma fórmula diferente (lista abaixo).
2. Rode todos de uma vez, antes de escrever o post.json:
   ```bash
   printf '%s\n' "título 1" "título 2" "título 3" "título 4" "título 5" > /tmp/titulos.txt
   python bot/conferir_titulo.py /tmp/titulos.txt
   ```
3. Fique com o que tem menos avisos **e** com o dado mais concreto de bolso ou de direito. Se dois
   empatarem, prefira o que a pessoa mandaria no grupo.
4. Escreva o post.json e confira o conjunto inteiro antes do push:
   ```bash
   python bot/conferir_titulo.py fila/<id>/post.json
   ```
   Corrija os `x` (avisos) e pese os `?` (sugestões). O mesmo comando confere a legenda: expressões
   proibidas da seção 8, "não é X, é Y", pergunta que o próprio texto responde, "O pior: ...", isca
   ("Concorda?", "marque quem", "o que vocês acham?"), clichês ("a verdade é que", "é sobre isso"),
   travessões, emojis demais e as 5 hashtags. O render grava o mesmo resultado em
   `design_auto.texto`.

A nota é um **piso de qualidade, não uma previsão de alcance**: em 03/11, posts de 3 e de 725 de
alcance tiraram nota parecida. Nota baixa é motivo para olhar de novo; nota alta não promete nada.

## As fórmulas da CBR

Os exemplos são títulos que já publicamos. Os números de alcance e envio são do dia do post: sinal,
não regra.

| Fórmula | Forma | Exemplo nosso |
|---|---|---|
| **Bolso** | o valor que muda na vida de quem trabalha, em destaque | "Botijão de gás fica *R$ 0,91* mais caro em fevereiro com alta do ICMS" (modelo aprovado pelo João) |
| **Prazo** | a data-limite de um direito ou de uma cobrança | "Patrão tem até *30 de novembro* para pagar a 1ª parcela do seu 13º" |
| **Contradição** | o personagem fazendo o oposto do que prega | "Banqueiro do Master, preso desde março, denuncia o Brasil por violar *seus direitos humanos*" (100 de alcance, 5 envios, 02/11) |
| **Pedido do poderoso** | quem tem poder pedindo algo que expõe a situação | "Flávio pede ao STF os *passaportes de volta* e a saída de Moraes do inquérito" (725, o maior de 03/11) |
| **Ironia ou frase** | a frase de efeito de alguém, entre aspas ou como ironia | "Padre de Aparecida ironiza quem tem *jatinho à disposição* para fugir" (4 envios, 01/11) |
| **Detalhe ridículo** | o número pequeno que desmonta o personagem | "Condenada e solta na Itália, Zambelli pede *R$ 50* a apoiadores" (4 envios, o maior de 03/11) |
| **Quem paga a conta** | quem perde, contado em gente | "Gerdau demite *280 metalúrgicos* em Divinópolis com o fim do aço, diz sindicato" |
| **Povo x eles** | a maioria quer, alguém segura (regra de 04/11) | forma: "*X%* querem [medida]; [quem] segura" (ainda não publicamos; o número tem de vir de pesquisa apurada, com instituto, data e margem) |
| **Vitória de quem trabalha** | o direito conquistado, com o número | "Jornada máxima cai para *42 horas* em 16 de dezembro, com duas folgas" |
| **Desmentido** | o boato e o fato, quem desmente | "Lula garante que *nenhum programa social* vai acabar e desmente boato da extrema direita" |
| **Placar** | a votação em número | "Senado aprova PEC da Segurança por *73 a 0* e separa maioridade penal" (4 de alcance: placar sozinho não basta; diga o que muda para quem) |
| **Pergunta** | só quando a resposta está no slide ou na 1ª linha | use pouco: pergunta sem resposta vira isca |

## O número na escala da pessoa

Adaptado do `marketing-psychology` (marketingskills, MIT), só com o que é honesto para notícia.
Número grande demais não pesa para ninguém; o mesmo número na escala de quem lê pesa.

- **Divida pela pessoa ou pelo tempo**: "R$ 1,4 trilhão em juros" vira quanto isso dá por brasileiro
  ou por dia, **com a conta feita a partir de dado oficial** (IBGE para população, por exemplo) e
  explicada na legenda ("dividindo pela população do IBGE, dá...").
- **Compare com o que a pessoa conhece**: em salários mínimos, cestas básicas (DIEESE), botijões,
  meses de aluguel. Só com a fonte da referência na legenda.
- **Diga o que a pessoa perde**, quando é isso que o fato diz: "Gerdau demite 280" pesa mais que
  "Gerdau reorganiza a produção". É o mesmo fato, contado por quem paga a conta.
- **Antes e depois**: o valor de hoje e o de antes, com as duas datas.

Limites: a conta tem de estar certa e a fonte, citada; arredonde para baixo; nada de comparação que
mude o sentido do fato; nada de urgência falsa ("corre!", "últimas horas") sem prazo real. Se a
conta não fecha com dado oficial, não use.

## Regras do título (o `conferir_titulo.py` confere)

- 8 a 14 palavras, verbo ativo, e um destaque `*...*`. Se houver número, o destaque vai nele.
- Número, nome ou data vencem qualquer adjetivo. Palavras vagas ("chocante", "absurdo", "bomba",
  "polêmica", "entenda", "veja") saem.
- No máximo 2 palavras em caixa alta no título (o chapéu já é em caixa alta).
- Abrir pela instituição ("Senado aprova...", "STF dá...") é permitido, mas teste abrir por quem é
  afetado ou pelo que muda: "Indígenas do MS..." no lugar de "STF dá 5 dias...".
- Nunca mais conclusivo que a fonte (seção 3 do manual): "PF apura", "segundo", "teria" ficam no
  título quando a fonte diz assim.

## O que esta skill não faz

Não escolhe a pauta, não apura, não substitui o revisor da notícia nem o de design. Se a melhor
fórmula exigir um número que a apuração não tem, escreva sem o número: nunca invente.
