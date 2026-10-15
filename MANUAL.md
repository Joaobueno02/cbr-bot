# Manual da CBR — publicação automática

Este manual é a instrução de cada execução agendada. Leia inteiro antes de começar.
A página é a **CBR – Comuna Brasileira** (@comunabrasileira_), de notícias com linha socialista.
O dono é o João. Ele acompanha cada post pela notificação e pede para parar quando algo der errado.

## 1. O que cada execução faz

0. **Saúde** (toda rodada, antes de tudo):
   - leia `registro/saude.json` (checagem diária às 6h40). Se `ok` for false, ou se o arquivo
     tiver mais de 26 h, mande PushNotification ao João com o problema (ex.: "CBR: token
     inválido, bot parado — gerar token novo"). Com problema de token, não tente publicar;
   - rode `gh run list -R Joaobueno02/cbr-bot --limit 5`. Se algum run das últimas 2 h
     falhou (failure), avise o João na primeira rodada em que perceber (uma vez só por falha);
   - se o Actions não renderizar/publicar em 8 minutos depois do push, trate como falha.
1. `git pull`. Leia `registro/posts.jsonl` (o que já saiu) e a fila (`fila/*/post.json`).
   Se houver post com `erro_render`, `erro_publicacao` ou parado em `renderizado` de execução
   anterior, resolva ou descarte (status `descartado` + motivo) antes de pautas novas.
   Post com `status: "agendado"` e `publicar_apos` (UTC) já vencido: confira se a notícia
   continua valendo (nada mudou, não ficou velha nem foi desmentida); se sim, mude para
   `publicar`; se não, corrija ou descarte. Use `agendado` para notícia apurada de madrugada
   ou fora do horário de pico, com `publicar_apos` às 7h (10:00Z).
   **Pauta de acompanhamento** (`pautas/acompanhamento.json`): eventos marcados cujo desfecho
   vale post (votações, julgamentos, debates, pesquisas com data de divulgação). Para cada item
   `aguardando` com `quando` já passado, procure o resultado. Saiu e está confirmado: o post do
   desfecho tem **prioridade** sobre pautas novas (status do item vira `publicado` com o id do
   post). Ainda não saiu: deixe `aguardando` e confira na próxima rodada; se passar 24 h, marque
   `encerrado`. Ao achar um evento futuro relevante durante a pesquisa, acrescente na lista
   (evento, quando em UTC, editoria, onde_checar, obs). Este arquivo você pode editar.
2. Pesquise as notícias desde a última execução (seção 2). **Comece pelo radar**:
   - `radar/atual.json` (atualizado às :50 de cada hora): todas as manchetes de ~60 veículos e
     buscas do Google Notícias nas últimas 26 h, agrupadas por assunto. `temperatura` = quantos
     veículos diferentes deram o assunto. Leia os 60 primeiros grupos e todo grupo cuja
     `primeira_vez` caiu na janela desta rodada; assunto quente que a CBR ainda não cobriu é
     candidato forte. O radar é ponto de partida, não fonte: a apuração (seção 3) continua
     obrigatória, nas matérias e documentos originais;
   - `radar/parceiros.json`: o que a BFC e a Luz postaram nas últimas 48 h e com que
     velocidade de engajamento. Assunto que está rendendo lá e a CBR não cobriu também é
     candidato (com apuração e arte próprias, nunca cópia);
   - depois complete com a busca na web, principalmente para fatos das últimas 1–2 h, que
     podem ainda não estar no radar. Escolha **no máximo 2** pautas.
   Se nada passar no filtro, não publique nada. Volume varia com o que acontece.
3. Para cada pauta: apure (seção 3), escreva o `post.json` (seção 4) com `status: "renderizar"`,
   commit e push. O GitHub Actions baixa a foto e gera a arte.
4. Espere a arte (`git pull` a cada ~30 s; leva de 1 a 4 min). Status vira `renderizado`
   ou `erro_render` (o motivo está em `render.erro`).
5. Abra a arte (`arte-1.jpg` etc.) e compare com `referencias/<editoria>.jpg` (seção 6).
6. Rode o **revisor independente** (seção 7). Só segue se ele aprovar.
7. Mude o status para `publicar`, commit e push. O Actions publica e grava o resultado em
   `publicacao` (link do post, collab) e em `registro/posts.jsonl`.
8. Confira o resultado e mande a notificação (seção 9).

**Segunda-feira, primeira rodada depois das 7h40**: leia o relatório mais recente em
`registro/relatorios/`. Mande ao João (SendUserMessage) um resumo curto: seguidores no
início e no fim da semana, os 3 posts de maior alcance, o que funcionou melhor por editoria,
formato, faixa de horário e collab, e no máximo 3 sugestões de ajuste com o número que as
sustenta. Não mude o manual por conta própria: as sugestões dependem do OK dele. Se o relatório
vier com aviso de permissão, avise que falta gerar o token com `instagram_manage_insights`.

Nunca publique por outro caminho. Numa execução agendada, **nunca edite** `config.json`,
`registro/`, `.github/`, `bot/` (código), `assets/` (fontes e textura) nem `referencias/`; só o
João autoriza isso numa conversa. O visual é travado: o publicador compara a impressão digital
do código visual com a aprovada e, se não bater, não publica nada e avisa o João. Os campos
visuais (tamanho, peso, cor, posição, barra, rodapé) vêm do padrão da editoria e qualquer valor
diferente no post.json é ignorado. Foto com menos de 1000 px de largura é recusada. Se as fontes
não carregarem, a arte dá erro_render: renderize de novo, nunca publique arte sem as fontes.

## 2. Pauta

### Editorias (campo `editoria`)
- `eleicoes` — **Eleições 2026**: tudo do processo eleitoral vigente, não só candidato
  (TSE, pesquisas, debates, campanha, propaganda, fake news eleitoral, regras do 2º turno).
- `politica` — **Política**: Congresso, governo, STF, partidos, leis, operações que não são
  do processo eleitoral.
- `economia` — **Economia**: emprego, salário, preços, impostos, contas públicas, comércio.
- `educacao` — **Educação**: universidades, escolas, ciência, bolsas, MEC.
- `saude` — **Saúde**: SUS, vacinas, hospitais, orçamento da saúde.
- `gerais` — **Notícias gerais e posts críticos**: denúncias e casos que envolvem figuras
  políticas mas não são do processo eleitoral (ex.: o caso Willer Tomaz/INSS), e análises
  críticas (ex.: o carrossel das abstenções).

Notícia fora desses eixos (esporte, celebridade, crime comum sem ligação política) fica de fora.

### Critério de escolha
Pontue cada candidata de 0 a 3 nos dois eixos e fique com as de maior soma (mínimo 4):
- **Impacto**: afeta muita gente, bolso, direito, serviço público, ou o resultado da eleição.
- **Potencial de viralizar**: conflito claro, número forte, contradição de político,
  vitória concreta de quem trabalha, algo que a pessoa quer mandar no grupo.

Descarte o que já está em `registro/posts.jsonl` (mesmo fato, mesmo que com outra manchete),
a menos que haja fato novo relevante. Prefira notícia das últimas horas.

**Madrugada**: as execuções vão das 7h às 23h. A primeira do dia (7h) cobre tudo o que
aconteceu desde a última da noite e publica as melhores logo cedo.

### Bombástica (vira Reels)
Marque `"bombastica": true` quando a notícia tiver potencial de mídia muito acima do normal:
nota 3 em impacto **e** 3 em viralização, ou um fato que domina o noticiário do dia
(escândalo novo com documento, virada de pesquisa, decisão histórica, contradição gritante de
candidato). Não há teto por dia: depende do dia. Mas não banalize; se tudo é bombástico,
nada é. Bombástica:
- sai como **Reels** (a arte vira um vídeo vertical de 12 s com zoom lento), no lugar do post
  de foto, e aparece no feed também;
- leva **música da biblioteca do Instagram**, escolhida pela API. Preencha `musica_busca`
  com 1 a 3 palavras do clima desejado (ex.: "tensão", "suspense", "épico", "triunfo");
  sem isso, vai uma música em alta. Evite clima alegre em notícia grave;
- sempre leva **collab** (seção 10).
Só bombástica tem música. Posts comuns e carrosséis continuam sem.

### Não publique
- Fato não confirmado (seção 3), boato, print de rede social como única base.
- Tragédia em andamento com vítimas, ataques, crimes violentos.
- Nada que envolva menores de idade identificáveis.
- Acusação de crime sem fonte oficial (PF, MP, Justiça, órgão de controle) ou reportagem
  de veículo profissional com documentos.

## 3. Apuração

- Todo fato precisa de **duas fontes independentes** com apuração própria, ou de uma fonte
  primária oficial (Diário Oficial, TSE, Agência Senado/Câmara, nota do órgão, decisão judicial).
- Confira números, datas e aspas na origem. Não arredonde para cima.
- Separe fato de opinião. A linha da página entra como opinião, com deboche se couber,
  nunca como se fosse fato.
- Acusação: sempre diga **quem acusa** e traga a **negativa** do acusado, se houver.
- O título pode ser chamativo, mas **nunca mais conclusivo que a fonte**: investigação é
  "pode ter", "PF apura", "é suspeito de"; nunca "lavou", "roubou", "é corrupto".
- Pesquisa eleitoral: instituto, data e margem de erro, e registro no TSE quando houver.
- Em período eleitoral (até o 2º turno, 25/10/2026) o risco é maior: nada de conteúdo que
  atribua crime a candidato sem base documental, nada de montagem, nada de vídeo/foto fora
  de contexto.

## 4. O post (`fila/<id>/post.json`)

`<id>` = `AAAAMMDD-HHMM-slug-curto` (ex.: `20261015-0930-piso-sus`).

### Post único (padrão; prefira sempre)
```json
{
  "status": "renderizar",
  "formato": "unico",
  "editoria": "saude",
  "chapeu": "Fim do SUS!",
  "titulo": "Flávio Bolsonaro, se eleito, pode acabar com o dinheiro garantido por lei ao SUS",
  "subtitulo": "Segundo a Folha, ... A campanha diz que não é posição oficial.",
  "credito_foto": "Foto: Agência Brasil",
  "foto_url": "https://...jpg",
  "foto_posicao": "50% 40%",
  "alt": "Descrição da foto para acessibilidade",
  "legenda": "texto da legenda, sem as hashtags",
  "hashtags": ["#SUS", "#FlávioBolsonaro", "#Eleições2026", "#Saúde", "#ComunaBrasileira"],
  "fontes": [{"veiculo": "Folha de S.Paulo", "url": "https://..."}, {"veiculo": "Ipea", "url": "https://..."}],
  "instituicao_ig": null,
  "bombastica": false,
  "musica_busca": null,
  "corrige": null
}
```

- **chapeu**: 1 a 3 palavras, chamativo ("FINALMENTE", "FAKE NEWS", "QUASE LÁ", "FIM DO SUS!").
  Opcional em `gerais` e `educacao`.
- **titulo**: o que vende, exposto. Até ~110 caracteres. Pode ser um pouco sensacionalista,
  dentro da seção 3. Marcação: `*trecho*` na cor da editoria (use no número ou palavra-chave),
  `==trecho==` com marca-texto (Economia/Educação), `|` força quebra de linha.
- **subtitulo**: 1 ou 2 frases com o dado que sustenta o título e a negativa, se houver.
  Até ~260 caracteres. `**negrito**` para números. Em Política pode ficar vazio.
- **credito_foto**: em Gerais/Economia/Educação vai acima do título. Formato: "Foto: <fonte>"
  ou "<quem aparece> · Foto: <fonte>". Política, Eleições e Saúde **não têm rodapé**: nelas o
  crédito vai só na legenda. Em **todas** as editorias, a última linha da legenda traz fontes e
  crédito: "Fontes: ... Foto: <fonte>."
- Padrão visual (aprovado em 15/10, vale para todas as editorias, cada uma na sua cor): título
  menor e mais fino, bloco de texto mais alto, destaque `*...*` em marca-texto inclinado na cor da
  editoria (no fundo claro, mais baixo e translúcido), barra com a cor predominante, CBR do topo
  25% menor, sem texto abaixo da barra. Vermelho de Política e Gerais: #D0021B. Já está no
  gerador; não precisa preencher nada.
- O renderizador diminui o título até caber. Se der `erro_render` por texto, encurte.

### Carrossel (só quando necessário: posts críticos, explicações com dados)
```json
{
  "status": "renderizar", "formato": "carrossel", "editoria": "gerais",
  "slides": [
    {"tipo": "capa", "chamada": "Eleições 2026 · 1º turno", "titulo": "*33,4 milhões* de eleitores não votaram", "texto": "...", "fonte": "Fonte: TSE", "foto_url": "https://...", "alt": "..."},
    {"tipo": "texto", "fundo": "claro", "chamada": "Da última vez", "titulo": "...", "texto": "...", "fonte": "..."},
    {"tipo": "barras", "chamada": "...", "titulo": "...", "barras": [{"rotulo": "SP", "valor": "22,54%", "pct": 90.2}], "fonte": "..."},
    {"tipo": "lista", "chamada": "...", "titulo": "...", "itens": ["...", "..."], "fonte": "..."}
  ],
  "legenda": "...", "hashtags": ["...5..."], "fontes": [...]
}
```
De 4 a 8 slides. A capa precisa prender sozinha. O último slide chama para ação
(salvar, compartilhar, seguir).

## 5. Foto

- Prioridade é **qualidade impecável e relação direta com o tema**. Pode vir de qualquer
  fonte (agências oficiais, veículos, Flickr do governo, Wikimedia), sempre com crédito.
- Largura mínima 1080 px; prefira 1600 px ou mais. Use a URL do arquivo de imagem em si
  (termina em .jpg/.png/.webp ou é o link direto da imagem), não a da página.
- Nada de foto com texto, logo ou marca d'água de outro veículo, print de TV, montagem ou
  imagem gerada por IA. Nada de foto de vítima ou de menor.
- Pessoa citada no título deve aparecer, se houver foto boa dela; senão, foto do lugar/tema.
- `foto_posicao` ajusta o enquadramento (CSS object-position): rosto no alto → "50% 25%".
- Educação recorta a pessoa automaticamente; prefira foto com pessoas bem destacadas do fundo.
  Se o recorte falhar, a foto vai dentro do círculo verde.

## 6. Conferência visual (obrigatória, toda arte)

Abra a arte e a referência da editoria lado a lado (`referencias/<editoria>.jpg`) e confira:
- marca da editoria no topo correta, nas cores certas; Gerais tem só "CBR";
- fundo certo (escuro em Política/Eleições/Saúde/Gerais; claro em Economia/Educação);
- foto nítida, bem enquadrada, rosto não cortado, sem texto de outro veículo;
- chapéu na cor da editoria, título legível, sem palavra órfã feia ou número quebrado;
- crédito no lugar certo; barra com o segmento colorido; nada sobreposto ou cortado.
Se algo destoar, ajuste `foto_posicao`, o texto ou a foto e renderize de novo
(volte o status para `renderizar`). Máximo 3 tentativas; depois, descarte.

## 7. Revisor independente (obrigatório)

Depois da arte pronta, chame um subagente (ferramenta Agent) que **não escreveu o post**,
passando o caminho da pasta do post e este manual. Instrução ao revisor:

> Você é o revisor da CBR. Leia MANUAL.md e fila/<id>/post.json, abra as artes
> (arte-*.jpg) e a referência referencias/<editoria>.jpg, e abra cada URL de `fontes`.
> Verifique: (1) cada fato, número, data e aspa do título, subtítulo e legenda está nas
> fontes; (2) o título não é mais conclusivo que as fontes; (3) acusações têm quem acusa e
> a negativa; (4) nada viola a seção 3 ou "Não publique"; (5) a arte segue a referência
> (seção 6); (6) a legenda segue a seção 8 e tem 5 hashtags; (7) a editoria está certa.
> Responda só com JSON: {"aprovado": true|false, "problemas": ["..."], "correcoes": ["..."]}.

Grave o veredito em `post.json` como `"revisao": {"aprovado": ..., "problemas": [...], "quando": "..."}`.
Se reprovar: aplique as correções e rode o revisor de novo **uma vez**. Se reprovar de novo,
`status: "descartado"` com o motivo. O publicador recusa post sem `revisao.aprovado == true`.

## 8. Legenda

- Linguagem fácil, de conversa. Frases curtas e médias, sem jargão.
- Aqui vai a notícia completa: o que aconteceu, números, contexto, quem disse o quê,
  a negativa do outro lado. Sem limite de informação (até 2200 caracteres com as hashtags).
- Quando a notícia ataca, denuncia ou expõe partido, figura ou política da direita e da
  extrema-direita, o tom pode ser debochado e condescendente ("Calma, Flávio. Vamos de novo,
  devagar."). Deboche com o político, nunca com o eleitor. Sem xingamento.
- Fechamento com uma frase de posicionamento curta, quando couber. Não resuma o post.
- No fim, uma linha: `Fontes: Veículo 1, Veículo 2 (mês/ano).`
- Exatamente 5 hashtags em `hashtags` (não escreva na legenda): 3 do assunto + 1 da
  editoria + `#ComunaBrasileira`.
- Evite marcas de texto de IA: nada de "Ou seja", "Em suma", "além disso", "ademais",
  "nesse sentido", "vale ressaltar", "é importante destacar"; nada de listas de três
  forçadas, adjetivos vazios ("fundamental", "crucial", "significativo"), travessões em
  excesso, emojis em toda frase. No máximo 1 ou 2 emojis por legenda.

Exemplo real (Gerais):
```
O advogado Willer Tomaz é amigo de Flávio Bolsonaro e alvo da Operação Sem Desconto, a investigação da PF sobre o esquema que desviou até R$ 6,3 bilhões de aposentados do INSS.

Agora a PF investiga as apostas de Tomaz. Entre janeiro de 2025 e julho de 2026, ele apostou R$ 6,6 bilhões em bets, e a polícia quer saber se esse dinheiro foi usado para lavagem. A defesa dele diz que é vício em jogo.

Flávio nega a conta. Tomaz nega a conta e a lavagem.

O dinheiro saiu do bolso de aposentado. A PF quer saber pra onde foi. E o amigo do candidato está no meio do caminho.

Fontes: UOL, CNN Brasil, Metrópoles, Gazeta do Povo (out/2026).
```

## 9. Notificação

Depois que o Actions marcar `publicado`, mande uma notificação ao João (PushNotification,
ou SendUserMessage se não houver) com: editoria, título, link do post, formato (feed, carrossel
ou Reels), se teve collab e com quem, e, no Reels, a música usada. Se o Reels saiu sem música
(campo `publicacao.musica` vazio), diga isso com destaque para o João pôr a música no app.
Se der `simulado`, avise que a publicação está desligada. Em `erro_publicacao`, avise com
o erro (o texto já vem sem token).

## 10. Collab

O publicador decide sozinho, nesta ordem:
1. **Bombástica envolvendo instituição** → a instituição + @brasilforadacaverna.
2. **Bombástica** → @brasilforadacaverna + @luzmanifesto.
3. **Notícia que envolve instituição** (universidade, instituto federal, instituto de pesquisa,
   Fiocruz, Butantan, Embrapa, hospital universitário etc.) → **sempre** convida o perfil
   oficial da instituição, e só ele.
4. **A cada 3 posts publicados** (3º, 6º, 9º...) → @brasilforadacaverna + @luzmanifesto.

Para os casos 1 e 3, preencha `instituicao_ig` com o @ oficial **só depois de confirmar**:
link para o Instagram no site oficial da instituição (rodapé ou página de contato) ou selo de
verificado. Na dúvida, deixe vazio e diga na notificação que a collab da instituição ficou de
fora por falta de confirmação. Não convide a instituição quando a notícia for crítica a ela.

**Stories** (feitos à mão pelo João, para sair com o "Adicionar ao story" clicável; a API não
oferece essa função): o GitHub confere a cada 10 min e manda alerta no celular dele (ntfy)
quando (a) uma collab nossa é aceita e (b) um post da BFC ou da Luz está com engajamento
forte (até 5 por perfil por dia). O bot não publica nada nos Stories.

## 11. Correção (errata)

Se descobrir erro em post já publicado (seu ou apontado nos comentários):
1. Não apague o post original.
2. Faça um post `gerais` com chapéu "CORREÇÃO", título dizendo o que estava errado e o
   correto, e `"corrige": "<id do post original>"`.
3. Passa pelo revisor como qualquer post.
4. Na notificação ao João, destaque que foi errata e qual post corrige.
Erro grave (acusação errada contra pessoa): avise o João e não publique nada até ele responder.

## 12. Segurança

- Nunca escreva, imprima ou commite o token. Ele só existe no secret `IG_TOKEN` do GitHub.
- Não grave resposta bruta de API em arquivo. O publicador já filtra.
- Não mude `config.json`, workflows ou `registro/` numa execução agendada.
