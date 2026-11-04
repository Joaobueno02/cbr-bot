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
   - se o Actions não renderizar/publicar em 8 minutos depois do push, trate como falha;
   - **dados velhos** (os agendamentos do GitHub atrasam ou falham às vezes): se
     `radar/atual.json` tiver mais de 70 min, rode `gh workflow run radar.yml -R Joaobueno02/cbr-bot`
     e espere ~2 min (git pull) antes de pesquisar; se `registro/saude.json` tiver mais de 26 h,
     rode `gh workflow run manutencao.yml -R Joaobueno02/cbr-bot -f tarefa=saude`; sempre rode
     `gh workflow run alertas.yml -R Joaobueno02/cbr-bot` no início da rodada (garante o aviso de
     collab aceita mesmo se o agendamento falhar); na rodada das 23h, se `radar/benchmark.json`
     tiver mais de 3 h, rode `gh workflow run manutencao.yml -R Joaobueno02/cbr-bot -f tarefa=benchmark`
     e espere ~2 min antes do dossiê. Se o `gh` não funcionar, siga com o que houver e registre
     no resumo da rodada;
   - **disparos fixos (pedido do João, 04/11/2026)**: o agendamento do GitHub está atrasando até 7 h
     (o benchmark das 22h45 chegava às 5h30; a saúde das 6h40, às 14h18). Por isso: na **rodada das 22h**,
     dispare o benchmark logo no início, mesmo em rodada curta (`gh api -X POST
     repos/Joaobueno02/cbr-bot/actions/workflows/manutencao.yml/dispatches -f ref=main -f "inputs[tarefa]=benchmark"`),
     para o ChatGPT do João ler o dia inteiro às 22h50; na **rodada das 7h**, se `registro/saude.json` tiver
     mais de 20 h, dispare a saúde do mesmo jeito (`-f "inputs[tarefa]=saude"`). Os horários do
     `manutencao.yml` ficam como reserva;
   - **registro de rodadas** (desde 04/11/2026, se existir `bot/registrar_rodada.py`): a rodada curta é
     gravada sozinha pelo `bot/rodada_curta.py`; no fim da rodada completa, rode
     `python bot/registrar_rodada.py --tipo completa --candidatos N --publicados N --descartados-antes N
     --descartados-depois N --sites "dominio1,dominio2" --ia-ok true|false`. Nos dois casos, commit e push
     só de `registro/rodadas.jsonl` (é gerado por script; o resto de `registro/` continua intocável). O
     dossiê das 23h conta rodadas curtas, descartes, sites bloqueados e quedas do Gemini por esse arquivo.
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
2. Pesquise as notícias **da janela desta rodada**: desde a rodada anterior até agora (ex.: na
   rodada das 11h, o que saiu entre 10h e 11h; na das 7h, desde as 23h da véspera). Filtre o que
   é mais importante ou merece visibilidade **com a lente de uma página socialista** (seção 2) e
   publique ainda nesta rodada. **Comece pela triagem** (regra do João, 20/10/2026, para gastar menos):
   - **`radar/triagem.json` primeiro** (Read, é curto). No radar.yml, o `bot/triagem.py` passa em todos os
     itens da pauta (A, A2, B, C e D): **regras** (sem IA) tiram o que está fora dos eixos (esporte,
     entretenimento, crime comum, tragédia, internacional sem Brasil nem América Latina) e o que já
     publicamos e juntam manchetes do mesmo assunto; depois o **Gemini** (API grátis) dá a nota I/V/P,
     editoria, formato e risco a cada candidato (campo `ia`). Traz `candidatos` (ordenados pela nota do
     Gemini), `rebaixados` (o Gemini achou fraco, fora ou repetido), `descartados_mais_quentes` (a regra
     tirou), `obrigatorios` (BFC/Luz/movimentos de hoje), `esquentou`/`esquentaram` (assunto que ganhou
     muitos veículos desde que entrou) e `ia.ok`/`ia.erro`. **A nota final é sua**: o Gemini só leu a
     manchete e erra; confira os rebaixados e os descartes quentes e resgate o que for pauta nossa
     (registre no resumo, para o dossiê propor ajuste);
   - **`radar/pre_apuracao.json`**: os veículos independentes do radar para os 3 primeiros candidatos.
     Comece a apuração por ele (ainda abra as matérias e preencha `apuracao`; `bot/cruzar.py` continua
     valendo para os outros);
   - **Rodada curta** (script desde 26/10/2026): `python bot/rodada_curta.py` confere tudo de uma vez
     (triagem ok e recente, candidatos/obrigatórios com `na_pauta_desde` na última hora, `esquentou`,
     rebaixados a conferir, fila, acompanhamento, calendário das 18h, dossiê das 23h, relatório de segunda).
     **Roda antes de ler este manual.** `VEREDITO: CURTA` → encerre a rodada sem ler o manual nem a pauta.md
     e sem buscar na web; o resumo diz "triagem sem candidatos novos" (os "descartes quentes" listados só se
     resgatam se a manchete for pauta nova). Triagem velha → dispare o radar, espere ~2 min e rode de novo.
     `VEREDITO: COMPLETA` → leia o manual e trabalhe só sobre os itens listados;
   - com candidatos, trabalhe só sobre eles: confirme a nota, aprofunde os melhores com a pré-apuração,
     `bot/cruzar.py`, `radar/atual.json` e a busca na web. **Não leia a pauta.md inteira** quando a triagem
     está ok; o item de A, A2 e B "avaliado nesta rodada" passa a ser o que a triagem avaliou mais a sua nota;
   - se `ok` for false ou o arquivo tiver mais de 70 min, siga o caminho antigo abaixo, a partir da
     pauta.md, e cite o erro no resumo. Com `ia.ok` false (sem chave, cota), a triagem vale só com as
     regras: dê você a nota a todos os candidatos;
   - **Boletim de notícias e tendências do dossiê** saem pelo ChatGPT do João (tarefas agendadas dele,
     lendo este radar público). Não é tarefa da rodada.
   **Caminho antigo (só sem triagem)**:
   - **`radar/pauta.md` primeiro, lido INTEIRO com a ferramenta Read** (nunca por WebFetch, que
     resume e perde itens). Atualizado às :20 e :50. Tem três partes: (A) tudo que a BFC e a Luz
     postaram hoje, cruzado com o radar; (B) assuntos em alta (desde 16/10, **2 veículos já bastam**
     para entrar; ganharam veículos nas últimas 3 h, mesmo que tenham começado ontem); (C) novos das
     últimas 3 h com vagas para Brasil, internacional, pesquisa e universidades; (D) os eixos
     **América Latina**, **Campo e alimento** (agricultura familiar, reforma agrária) e **Famosos e a eleição**, das
     últimas 6 h. **Todo item de A e B com "na pauta desde" depois da
     rodada anterior precisa ser avaliado nesta rodada**: publique, ou registre no resumo da
     rodada por que descartou. A regra da janela vale para o fato novo, mas assunto que estourou
     agora (B) ou que os parceiros deram hoje (A) entra mesmo que tenha começado antes;
   - **Monitor da BFC/Luz**: `radar/parceiros.json` é atualizado a cada 20 min (alertas.yml). Se a
     seção A parecer atrasada, leia direto o parceiros.json (posts de hoje, com legenda e link);
   - **Movimentos sociais** (seção A2 da pauta; `radar/movimentos.json`, lido às 12h30, 18h30 e 21h30, meia hora depois dos picos de postagem deles):
     MST, MTST, CUT, UNE, Apib, Sleeping Giants, Greenpeace Brasil (lista em `config.json` >
     `movimentos`). É pauta que não sai em jornal: post deles é **ponto de partida**, nunca fonte
     única; confirme com veículo profissional ou fonte oficial (seção 3). Perfil com "erro" no
     movimentos.json = @ errado ou conta não comercial: avise o João no dossiê;
   - `radar/atual.json` (~235 fontes: nacionais, imprensa de esquerda, regionais; imprensa
     internacional sobre Brasil e América Latina de EUA (NYT, WSJ, Washington Post), Europa
     (Guardian, Le Monde, El País, FT, DW, Euronews), Oriente Médio (Al Jazeera, Middle East Eye,
     Al Mayadeen), Ásia (SCMP, Xinhua, The Hindu), África (Africanews, Mail & Guardian, AllAfrica)
     e agências (Reuters, AP, AFP, EFE); latino-americanas, campo, institutos e universidades, últimas
     26 h, agrupado por assunto; `temperatura` = veículos diferentes) é o acervo completo: use
     para aprofundar um assunto (todos os veículos e links), não para varrer. O radar é ponto de
     partida, não fonte: a apuração (seção 3) continua obrigatória;
   - **rodada das 7h**: se existir, leia `radar/estouraram.json` > `pautas_que_nao_demos` (o que estourou ontem nas
     páginas de referência, na nossa lente, e não demos). Se o assunto ainda tiver fato novo ou desdobramento
     hoje, trate como candidato, com a apuração de sempre; post velho de outra página não é pauta;
   - depois complete com a busca na web, principalmente para fatos das últimas 1–2 h, que
     podem ainda não estar no radar. Escolha **no máximo 2** pautas.
   Se nada passar no filtro, não publique nada. Volume varia com o que acontece.
3. Para cada pauta: apure (seção 3), escreva o `post.json` (seção 4) com `status: "renderizar"`,
   commit e push. O GitHub Actions baixa a foto e gera a arte.
4. Espere a arte (`git pull` a cada ~30 s; leva de 1 a 4 min). **Não empurre correção do mesmo `post.json`
   enquanto o run dele estiver rodando** (pedido do João, 04/11/2026): espere o commit "bot: render/publicação"
   chegar no `git pull` e só depois corrija; senão o commit do robô bate com o seu e o run falha. Status vira `renderizado`
   ou `erro_render` (o motivo está em `render.erro`).
5. **Revisão de design** (seção 6): leia `design_auto` no post.json (medidas automáticas), confira
   a arte você mesmo contra `referencias/<editoria>.jpg` e rode o **revisor de design** (subagente).
6. Rode o **revisor da notícia** (seção 7). As duas revisões são obrigatórias e independentes.
7. Mude o status para `publicar`, commit e push. O Actions publica e grava o resultado em
   `publicacao` (link do post, collab) e em `registro/posts.jsonl`.
8. Confira o resultado e mande a notificação (seção 9).

**Segunda-feira, primeira rodada depois das 7h40**: leia o relatório mais recente em
`registro/relatorios/`. Mande ao João (SendUserMessage) um resumo curto: seguidores no
início e no fim da semana, os 3 posts de maior alcance, o que funcionou melhor por editoria,
formato, faixa de horário e collab, e no máximo 3 sugestões de ajuste com o número que as
sustenta. Não mude o manual por conta própria: as sugestões dependem do OK dele. Se o relatório
vier com aviso de permissão, avise que falta gerar o token com `instagram_manage_insights`.

**Ritmo e erro da Meta (regra do João, 15/10/2026)**: notícia boa sai **na rodada em que foi
apurada**, sem segurar para depois. Esperar demais tira a cara de noticiário e abre espaço para
acusação de cópia. O erro 4/2207051 no `media_publish` é o anti-spam da Meta: a API responde erro
mas quase sempre publica. O publicador cuida sozinho:
- confere no perfil **antes** de publicar (mesmo texto já no ar = não reenvia);
- depois de erro, confere se o post saiu; se não saiu, faz o **"tentar novamente"** que o João fazia
  à mão: até 2 novas tentativas (após 1 min e após 2,5 min), sempre conferindo antes o perfil e o
  status do container, para nunca duplicar;
- mínimo de **15 min** entre posts e teto de **12 posts/dia** (`config.json`); pausa aleatória de
  20–45 s antes de publicar. Os avisos ficam em `registro/avisos_api.jsonl` (para o dossiê).
O que cabe à rodada:
- até 2 posts por rodada. Publique o primeiro assim que o revisor aprovar. O segundo vai a
  `publicar` quando passarem 15 min do primeiro, **na mesma rodada** (espere com `git pull`); se
  o publicador devolver `agendado` por intervalo, espere o horário e mude para `publicar`;
- `agendado` só para notícia apurada de madrugada (publicar às 7h) ou para o teto diário;
- 2207051 com o post publicado é **aviso, não falha**: siga normal e não avise o João por isso;
- `erro_publicacao` mesmo depois das tentativas: confira se o post não está no ar (dispare
  `teste-conexao.yml` e veja `status/teste-conexao.json` > `recentes`). Se não está, mude de novo
  para `publicar` **uma vez** na mesma rodada. Falhou de novo: avise o João e deixe para a próxima
  rodada. Duas rodadas seguidas com `erro_publicacao`: pare de publicar e avise o João;
- no dossiê das 23h, informe quantos avisos 2207051 houve no dia.
`gh workflow run` não funciona nas sessões do Claude (GraphQL bloqueado); use
`gh api -X POST repos/Joaobueno02/cbr-bot/actions/workflows/<arquivo>.yml/dispatches -f ref=main`
(com `-f "inputs[tarefa]=saude"` etc. quando o workflow pede entrada).

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
- `america_latina` — **América Latina** (aprovada em 16/10/2026, laranja #FF5A1F, faixa colorida
  embaixo): governos, eleições, protestos, repressão, EUA na região, Mercosul. **Preencha `pais`**
  (ex.: "Argentina"), que vira o selo acima do chapéu. Notícia de vários países: "América Latina".
- `roca` — **da roça** (aprovada em 16/10/2026, paleta café e folha, "da roça" escrito à mão sob
  o CBR): agricultura familiar, reforma agrária, MST, agroecologia, agrotóxico, preço do
  alimento, fome, conflito no campo, trabalho escravo no campo. Hashtag de editoria: `#DaRoça`.
- **Famosos e a eleição** (até o 2º turno): artista, atleta ou influenciador grande que declara
  voto ou apoio. Vai em `eleicoes`. Só com a declaração confirmada na fonte (vídeo ou post do
  próprio famoso, ou veículo profissional que o mostre); "indireta" só se o próprio veículo
  tratar como declaração, e o título diz o que ele falou, sem exagerar. A seção D da pauta junta
  esses assuntos.

Notícia fora desses eixos (esporte, celebridade, crime comum sem ligação política) fica de fora.

### Critério de escolha
A CBR é uma página socialista: escolha pensando em quem trabalha. Têm prioridade: direitos e
condições de trabalho (salário, jornada, emprego, aposentadoria), serviços públicos (SUS, educação
pública, transporte, moradia), desigualdade e quem paga a conta (impostos, juros, privilégios),
vitórias de trabalhadores e movimentos sociais, e contradições, escândalos e ataques a direitos
vindos da direita e da extrema-direita. Notícia que só interessa ao mercado ou a celebridade
fica de fora, a não ser que mexa no bolso de quem trabalha. A lente decide **o que** cobrir e o
tom da legenda; os fatos seguem a seção 3 à risca.
**Ângulo de mobilização (pedido do João, 04/11/2026)**: em 03/11 a Mídia Ninja fez 82 interações por mil
seguidores com "78% dos brasileiros é favorável ao fim das bets" e o nosso Reels das bets (fala do Fux) teve
13 de alcance. Quando a pauta for um tema em que a maioria da população quer uma coisa e o Congresso, o STF,
o governo ou as empresas seguram (bets, 6x1, juros, isenção do IR, tarifa zero), prefira o ângulo "o povo
quer x eles seguram": título com o número da pesquisa (`*78%*`), instituto e data no subtítulo ou na legenda,
e quem está segurando. A fala de autoridade entra como apoio, não como manchete. A pesquisa precisa ser de
instituto identificado, com data e, de preferência, margem de erro (seção 3); nada de enquete de rede social.
A chamada de envio da legenda vira chamada de pressão ("Manda pra quem ainda acha que bet é diversão.").
Pontue cada candidata de 0 a 3 nos dois eixos e fique com as de maior soma (mínimo 4):
- **Impacto**: afeta muita gente, bolso, direito, serviço público, ou o resultado da eleição.
- **Potencial de viralizar**: conflito claro, número forte, contradição de político,
  vitória concreta de quem trabalha, algo que a pessoa quer mandar no grupo.

**Ângulo próprio (desempate, pedido do João, 04/11/2026; adaptado do newsjacking do marketingskills)**: entre
duas pautas de nota parecida, fique com a que tem um ângulo que os grandes veículos não estão dando. É isso que
faz a pessoa mandar o NOSSO post, e não o da Folha. Ângulos da CBR, em ordem de preferência:
1. **quem paga a conta**: a mesma notícia contada por quem perde (trabalhador, aposentado, morador);
2. **o número na escala da pessoa**: o dado oficial dividido por pessoa, por dia ou em salários mínimos
   (skill `titulo-cbr`), com a conta explicada na legenda;
3. **discurso x prática**: o que o político disse e o que fez, com data e fonte das duas coisas;
4. **não é caso isolado**: o 3º caso do mês, ligado aos anteriores (só com os casos apurados, e citando
   nossos posts de `registro/posts.jsonl` quando houver);
5. **o explicador**: a notícia é complicada e a cobertura está confusa (carrossel "Entenda").
Sem ângulo próprio e sem fato novo, o assunto que todo mundo já deu há mais de 24 h fica de fora.

Descarte o que já está em `registro/posts.jsonl` (mesmo fato, mesmo que com outra manchete),
a menos que haja fato novo relevante. Prefira notícia das últimas horas.

**Madrugada**: as execuções vão das 7h às 23h. A primeira do dia (7h) cobre tudo o que
aconteceu desde a última da noite e publica as melhores logo cedo.

### Formato: feed, carrossel ou Reels (regra do João, 16/10/2026)
Depois de pontuar Impacto (I) e Viralização (V), pontue também **Profundidade (P)**, de 0 a 3:
quanto a notícia rende para destrinchar (números para comparar, linha do tempo, quem é quem,
"o que muda pra você", vários lados, antes x depois). Conte os blocos com informação própria e
verificada: 4 blocos ou mais = P 3; 3 = P 2; 2 = P 1.
- **Reels** (`bombastica: true`): I = 3 **e** V = 3, ou o fato domina o noticiário do dia.
  É a notícia que explode sozinha, não precisa ser explicada.
- **Reels comum** (`"reels": true`, regra do João, 20/10/2026, para alcançar quem não segue: post de
  feed só aparece para seguidor, Reels e carrossel são recomendados para fora). **Desde 01/11/2026
  (regra do João, dossiê de 31/10: Reels com média de 58 de alcance contra 4 do feed), todo post único
  sai como Reels comum** enquanto a página tiver menos de 1.000 seguidores, sem meta nem teto por dia.
  Só fica no feed a errata (seção 11) ou o post cuja foto não serve para o quadro vertical depois de
  trocar a foto (registre o motivo no resumo da rodada). É a
  **mesma arte aprovada** (o vídeo é o quadro vertical com zoom lento, idêntico ao da bombástica),
  então passa pela mesma revisão de design; confira também `story.jpg` (é a capa do Reels e o que
  aparece na grade do perfil: a arte inteira tem de ficar visível no recorte 4:5 central, sem nada
  cortado). Leva música (ver "Bombástica") e segue a regra comum de collab (não força BFC + Luz).
- **Carrossel**: não é Reels, I + V ≥ 5 **e** P ≥ 2. É a notícia que fica melhor contada em
  partes: a pessoa salva e manda no grupo. Capa que prende sozinha, 4 a 8 slides, último com
  chamada (salvar, compartilhar, seguir). Até 3 carrosséis por dia.
- **Feed (post único)**: só as exceções do Reels comum acima (errata ou foto sem quadro vertical). O
  resto que passou no filtro (I + V ≥ 4) e não é carrossel sai como Reels comum.
Na dúvida entre carrossel e Reels: se o valor está no **choque** do fato, Reels; se está na
**explicação**, carrossel. Registre a nota no resumo da rodada (ex.: "I3 V2 P3 → carrossel").

### Carrossel "Entenda" (explicativo)
Não é semanal fixo: só quando aparece uma pauta **muito chamativa e complicada**, que o público
precisa entender (ex.: fim da 6x1 — a jornada não cai para 40 h de uma vez, é gradual; quando
começa; o que muda no contracheque; quem votou contra; a pressão de empresários para Flávio rever).
Critério: I = 3, V ≥ 2 e P = 3. No máximo **2 por semana**. Estrutura: capa com a pergunta
("Fim da 6x1: o que muda pra você?"), linha do tempo, números, "o que muda pra você", os riscos
e quem está contra, último slide com chamada (salvar, compartilhar, seguir). Sai de manhã
(9h–11h), de preferência num dia de pouca notícia. Mesma apuração comparada (seção 3) e as duas
revisões, como qualquer post.

### Calendário de datas (`pautas/calendario.json`)
Datas que a página sabe com antecedência, para posts de conscientização e críticos (ex.:
Consciência Negra, Dia pela Eliminação da Violência contra a Mulher, Direitos Humanos, AI-5).
Cada item tem data, nome, editoria, ângulo, formato e fontes sugeridas. **Na rodada das 18h da
véspera**, leia o calendário: para cada item do dia seguinte com `status: "pendente"`, apure com
dados atuais (seção 3), monte o post, passe pelas duas revisões e deixe `status: "agendado"` com
`publicar_apos` às 9h (12:00Z). No calendário, o item vira `"preparado"` com o id do post. Data
que perdeu o sentido (ex.: notícia maior no dia) pode ser pulada: registre o motivo. Ao achar
uma data relevante nova na pesquisa, acrescente no arquivo (você pode editá-lo).

### Bombástica (vira Reels)
Marque `"bombastica": true` quando a notícia tiver potencial de mídia muito acima do normal:
nota 3 em impacto **e** 3 em viralização, ou um fato que domina o noticiário do dia
(escândalo novo com documento, virada de pesquisa, decisão histórica, contradição gritante de
candidato). Não há teto por dia: depende do dia. Mas não banalize; se tudo é bombástico,
nada é. Bombástica:
- sai como **Reels** (a arte vira um vídeo vertical de 12 s com zoom lento), no lugar do post
  de foto, e aparece no feed também;
- leva **trilha própria da editoria** (vale também para o Reels comum e o carrossel em Reels; pedido do João,
  27/10/2026). A busca de músicas da API volta vazia para a nossa conta (`radar/musicas.json`), então o
  pipeline embute no `reels.mp4` a trilha `trilhas/<editoria>.m4a` (sintetizada por `bot/gerar_trilhas.py`,
  sem direito de terceiros) logo depois do render, sem recodificar a arte; `render.reels.trilha` registra.
  `"trilha": false` no post deixa o Reels mudo. Se um dia a API achar música (`config.json` > `musicas`),
  ela substitui a trilha; a falha fica em `publicacao.musica_erro`. Na notificação, diga a trilha usada;
- sempre leva **collab** (seção 10).
Só Reels tem música (bombástica e Reels comum). Feed e carrossel continuam sem.

### Modo eleição (até o 2º turno, 25/10/2026)
- Prioridade de pauta: debate, pesquisa registrada no TSE, propaganda e fake news da campanha, decisões
  do TSE, apoios relevantes. Na dúvida entre duas pautas de mesmo peso, a eleitoral.
- **Domingo, 25/10**: além das rodadas de hora em hora, há rodadas extras às :34 das 17h às 23h (tarefa
  "CBR – noite da eleição"). Os desfechos estão em `pautas/acompanhamento.json`: fim da votação (17h),
  primeiras parciais do TSE, **resultado** (quando o TSE ou a imprensa projetarem matematicamente), discurso
  do eleito e do derrotado. O post do resultado é **bombástica (Reels)**, com o número do TSE (percentual
  de votos válidos e urnas apuradas no momento) e a hora da apuração; nada de "venceu" antes de o TSE ou
  a apuração tornarem matematicamente impossível a virada. Fonte primária: resultados.tse.jus.br.
- Pesquisa de boca de urna só com instituto, registro e margem, e dita como pesquisa, não resultado.
- Depois do resultado: reação de movimentos sociais e da BFC/Luz entra pela seção A/A2 normalmente.
- Segunda, 26/10: este bloco deixa de valer (a rodada lê e ignora).

### Não publique
- Fato não confirmado (seção 3), boato, print de rede social como única base.
- Tragédia em andamento com vítimas, ataques, crimes violentos.
- Nada que envolva menores de idade identificáveis.
- Acusação de crime sem fonte oficial (PF, MP, Justiça, órgão de controle) ou reportagem
  de veículo profissional com documentos.

## 3. Apuração

**Checagem comparada (regra do João, 16/10/2026)**: achou uma notícia boa numa fonte? Procure a
mesma notícia nas outras fontes, compare as versões e escreva a **nossa** a partir delas.
1. Rode `python bot/cruzar.py "palavras da notícia"`: mostra todos os veículos do radar que deram o
   mesmo assunto (os marcados com * são candidatos a versão independente). Se o radar não tiver,
   procure na web pelas mesmas palavras.
2. Abra **pelo menos 2 versões independentes** (veículos diferentes, com apuração própria; não
   vale republicação de agência nem agregador). Se uma delas for fonte primária oficial (Diário
   Oficial, TSE, decisão judicial, nota do órgão, Agência Senado/Câmara), uma versão de veículo basta.
3. Compare e grave em `post.json`:
   ```json
   "apuracao": {
     "versoes": [{"veiculo": "UOL", "url": "...", "resumo": "o que essa versão diz, em 1-2 frases"},
                 {"veiculo": "Folha", "url": "...", "resumo": "..."}],
     "em_comum": ["fatos e números que as versões confirmam"],
     "divergencias": ["onde discordam e o que escolhemos"],
     "so_numa_versao": ["fato que só uma traz (entra só na legenda, com 'segundo X')"],
     "fonte_primaria": null
   }
   ```
4. **Escreva a nossa versão** juntando as duas, com as nossas palavras (nunca copiar frase de
   ninguém): título e subtítulo só com o que está em `em_comum` (ou na fonte primária); o que só
   uma versão traz vai na legenda com "segundo X"; número divergente → use o mais conservador
   e diga que há outra conta. A linha "Fontes:" da legenda cita as versões comparadas.
   Para posts a partir de 16/10, o publicador recusa post sem `apuracao` com 2 versões (ou
   `fonte_primaria` preenchida com o link).
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
  "corrige": null,
  "reels": false,
  "comentario": "Você sabia que o SUS tem piso garantido por lei? Conta aqui o que mudaria na sua cidade."
}
```
- **reels**: `true` para Reels comum (seção 2, "Formato"). Só em post único; desde 01/11/2026 é o padrão
  de todo post único (`false` só nas exceções).
- **comentario**: o primeiro comentário, que o bot faz logo depois de publicar (20/10/2026). Uma
  pergunta curta e concreta sobre o assunto, que a pessoa consiga responder com a própria experiência
  ou opinião ("Na sua cidade o ônibus já é de graça no domingo?"). Sem link, sem hashtag, sem repetir a
  legenda, no máximo 1 emoji, nunca pergunta que ofenda o eleitor do outro lado. A API não deixa fixar;
  sem a permissão `instagram_manage_comments` no token, o bot só registra `comentario_erro` e o post
  segue normal. Opcional em errata.

- **chapeu**: 1 a 3 palavras, chamativo ("FINALMENTE", "FAKE NEWS", "QUASE LÁ", "FIM DO SUS!").
  Opcional em `gerais` e `educacao`.
- **titulo**: o que vende, exposto. Até ~110 caracteres. **Antes do primeiro render** (desde 04/11/2026), siga a
  skill `.claude/skills/titulo-cbr/SKILL.md` (quando existir): escreva 5 títulos com fórmulas diferentes, rode
  `python bot/conferir_titulo.py` neles, escolha um e confira o post.json inteiro (chapéu, título, subtítulo e
  1ª linha da legenda não repetem as mesmas palavras; a 1ª linha cabe em ~125 caracteres). Os avisos também
  saem em `design_auto.texto` depois do render; não são graves, mas cada um pede uma decisão. Pode ser um pouco sensacionalista,
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
**Visual do carrossel (regra do João, 20/10/2026)**: o carrossel segue a estética da editoria, como o post único
(marca, cor de destaque e fundo da editoria: Saúde em turquesa, Eleições em amarelo, Economia/Educação no fundo claro etc.).
Só Gerais usa o modelo crítico vermelho com o CBR simples. O campo `fundo` dos slides é ignorado fora de Gerais.
De 4 a 8 slides. A capa precisa prender sozinha. O render acrescenta sozinho o último slide (chamada de envio
e fontes): não escreva slide de fechamento. **Antes de escrever os slides (desde 04/11/2026), siga a skill
`.claude/skills/carrossel-cbr/SKILL.md`** (quando existir): escolha uma das 4 estruturas (entenda em N pontos,
o número e a prova, seu direito passo a passo, discurso x prática com o slide do outro lado), títulos internos
com até 10 palavras, e rode `python bot/conferir_titulo.py fila/<id>/post.json` antes do push.

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

## 6. Revisão de design (obrigatória, toda arte, tão rigorosa quanto a da notícia)

Regra do João (16/10/2026): a estética é o que faz a página ser reconhecida. A revisão do design
é **separada** da revisão da notícia e tão minuciosa quanto ela. Arte "quase certa" não sai.

**a) Conferência automática** (`design_auto`, gravada pelo Actions logo depois do render): mede
linhas e palavra órfã do título e do subtítulo, chapéu quebrado, título no tamanho mínimo, número
quebrado entre linhas, texto saindo da margem, contraste da marca do topo com a foto, ampliação e
nitidez da foto. `graves` > 0 = corrija e renderize de novo (o publicador recusa). Leia também os
`avisos`: cada um precisa de uma decisão (corrigir ou justificar no `revisao_design`).

**b) A sua conferência**, com a arte e `referencias/<editoria>.jpg` abertas lado a lado, e depois
**em recortes ampliados** (corte com PIL e abra com Read: topo 0-260 px, foto inteira, bloco de
texto, barra 1180-1350 px):
- marca do topo: editoria certa, cores certas, legível sobre a foto (sem sumir no céu claro);
- fundo: escuro em Política/Eleições/Saúde/Gerais/América Latina; claro em Economia/Educação;
- foto: nítida (sem borrão, sem serrilhado de ampliação), bem enquadrada, rosto inteiro e sem
  corte na testa ou queixo, olhar com espaço, sem texto/logo de outro veículo, sem elemento
  estranho colado na marca ou no texto, tom de cor coerente com a editoria;
- texto: chapéu em 1 linha, na cor da editoria; título sem palavra órfã, sem número/valor
  quebrado, destaque `*...*` no número ou palavra-chave e em no máximo 2 linhas; subtítulo sem
  órfã; alinhamento à esquerda igual ao da referência; nada encostando na margem;
- barra: na altura da referência, segmento colorido certo (América Latina: faixa colorida);
- nada sobreposto, cortado, desalinhado ou com espaçamento diferente da referência.

**Referências** (atualizadas em 26/10/2026): `referencias/politica.jpg`, `eleicoes.jpg`, `gerais.jpg` e
`economia.jpg` são artes publicadas no padrão atual. Nas outras editorias, se a referência divergir do padrão
de 15/10 (seção 4: título menor, bloco mais alto, marca-texto inclinado, CBR 25% menor, nada abaixo da
barra), vale o padrão: isso vem travado do gerador e **não reprova** a arte. Reprove só o que depende do
post (texto, quebras, foto, enquadramento, legibilidade).

**c) Revisor de design** (subagente pela ferramenta Agent com `model: "sonnet"`, para gastar menos;
diferente do revisor da notícia):

> Você é o revisor de design da CBR. Leia a seção 6 do MANUAL.md e fila/<id>/post.json
> (inclusive `design_auto`). Abra fila/<id>/arte-*.jpg e referencias/<editoria>.jpg e compare
> lado a lado; depois corte e amplie com PIL (topo 0-260, foto, bloco de texto, barra 1180-1350)
> e abra cada recorte. Confira um por um os itens da seção 6b. O padrão visual travado (seção 4 e
> "Referências" da seção 6) não reprova. Seja rigoroso com o que depende do post: palavra órfã,
> marca pouco legível, foto borrada ou mal enquadrada reprova. Em Reels, confira também story.jpg. Responda só com JSON:
> {"aprovado": true|false, "problemas": ["..."], "correcoes": ["..."]}.

Grave em `post.json` como `"revisao_design": {"aprovado": ..., "problemas": [...], "quando": "..."}`.
Se reprovar, corrija (texto, `foto_posicao` ou outra foto), renderize de novo e rode o revisor de
design de novo. Máximo 3 renders; depois, descarte com o motivo. Para posts a partir de 16/10, o
publicador recusa post sem `revisao_design.aprovado == true`.

## 7. Revisor da notícia (obrigatório, independente)

Depois da arte pronta, chame um subagente (ferramenta Agent, `model: "sonnet"`) que **não escreveu o post**,
passando o caminho da pasta do post e este manual. Instrução ao revisor:

> Você é o revisor da notícia da CBR. Leia MANUAL.md e fila/<id>/post.json, abra a arte
> (arte-*.jpg, só para conferir o texto que aparece nela) e abra cada URL de `fontes` e de
> `apuracao.versoes`. Verifique: (1) cada fato, número, data e aspa do título, subtítulo e
> legenda está nas fontes; (2) a `apuracao` compara de verdade 2 versões independentes (ou tem
> fonte primária) e o título/subtítulo só usam o que está em `em_comum`; (3) o título não é mais
> conclusivo que as fontes; (4) acusações têm quem acusa e a negativa; (5) nada viola a seção 3
> ou "Não publique"; (6) a legenda segue a seção 8 e tem 5 hashtags; (7) a editoria e o formato
> (feed, carrossel, Reels) seguem a seção 2; (8) **"e daí?"**: cada parágrafo da legenda responde o que
> aquilo muda para quem trabalha, ou traz o fato que sustenta isso (parágrafo que só repete ou só opina sem
> fato sai); (9) **"prove"**: cada número da arte e da legenda aparece numa versão da `apuracao` ou na fonte
> primária, e conta feita por nós (por pessoa, em salários mínimos) está explicada na legenda com a fonte da
> base; (10) no carrossel "discurso x prática", o slide do outro lado existe e é fiel à resposta do acusado.
> Responda só com JSON: {"aprovado": true|false, "problemas": ["..."], "correcoes": ["..."]}.

Grave o veredito em `post.json` como `"revisao": {"aprovado": ..., "problemas": [...], "quando": "..."}`.
Para gastar menos, rode os dois revisores **em paralelo** (mesma mensagem) e, na 2ª passada, continue o
mesmo subagente com SendMessage em vez de abrir outro. Se reprovar: aplique as correções e rode o revisor de novo **uma vez**. Se reprovar de novo,
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

**Pausa (pedido do João, 27/10/2026)**: até `config.json` > `collab_automatica_pausada_ate`
(03/11/2026) o publicador **não convida ninguém** (nem BFC/Luz nas bombásticas, nem a cada 3 posts, nem o
rodízio); só a instituição (regras 1 e 3). Motivo: em 26/10 os Reels com convite pendente tiveram alcance
1-2 contra 1.234-4.734 dos sem collab. O dossiê compara o alcance da semana para decidir se volta.
**Só instituição, sem prazo (pedido do João, 04/11/2026)**: depois de 0 aceites em 12 convites da BFC e da
Luz e 0 em 2 do Sleeping Giants, a pausa foi estendida sem data (`collab_automatica_pausada_ate` = 2099-12-31).
Só se convida a instituição (regras 1 e 3) ou quem o João pedir no post (`collab_forcar`). As regras 2, 4 e 5
abaixo ficam suspensas até ele mandar voltar.

O publicador decide sozinho, nesta ordem:
1. **Bombástica envolvendo instituição** → a instituição + @brasilforadacaverna.
2. **Bombástica** → @brasilforadacaverna + @luzmanifesto.
3. **Notícia que envolve instituição** (universidade, instituto federal, instituto de pesquisa,
   Fiocruz, Butantan, Embrapa, hospital universitário etc.) → **sempre** convida o perfil
   oficial da instituição, e só ele.
4. **A cada 3 posts publicados** (3º, 6º, 9º...) → @brasilforadacaverna + @luzmanifesto.
5. **Rodízio de páginas progressistas** (16/10/2026): página que **pediu collab** (achada pelo
   radar de collab, com 1.000+ seguidores) entra no rodízio e passa a ser convidada nos próximos
   posts: sozinha nos posts sem collab, ou como 3ª convidada junto da BFC e da Luz. Regras: 1 h de
   carência depois de achada (o João recebe "Siga @fulano agora" no celular, porque a API não
   segue perfis), no máximo 1 convite por página a cada 24 h, e sai do rodízio depois de 3
   convites sem aceite ou se a API recusar o convite. Notícia de instituição continua só com a
   instituição. Controle em `registro/collab_rodizio.json` (convites e aceites por página).

Para os casos 1 e 3, preencha `instituicao_ig` com o @ oficial **só depois de confirmar**:
link para o Instagram no site oficial da instituição (rodapé ou página de contato) ou selo de
verificado. Na dúvida, deixe vazio e diga na notificação que a collab da instituição ficou de
fora por falta de confirmação. Não convide a instituição quando a notícia for crítica a ela.

**Números das collabs** (20/10/2026): `radar/collabs.json`, gerado às 22h45, traz por página
convidada os convites, aceites e a taxa de aceite dos últimos 14 dias, e por post com collab o ganho
de seguidores entre as medidas antes e depois (sinal, não prova). O dossiê usa para dizer quais
parceiras valem insistir e quais não aceitam.

**Radar de collab** (pedido do João, 16/10/2026: movimento de páginas progressistas que se ajudam
na visibilidade): às 11h40 e 19h40 o `bot/collab_radar.py` procura posts de páginas de esquerda
chamando parceria ("chama na collab", "divulgue sua página progressista", #esquerdasegueesquerda),
descobre páginas novas (marcadas nesses posts ou que fizeram collab com BFC/Luz/movimentos) e manda
alerta no celular do João com o link (até 4 por dia): ele comenta com o @ da CBR ou manda direct.
A API não comenta nem manda direct por nós. Resultado em `radar/collab_oportunidades.json`
(chamadas e páginas com seguidores). No dossiê, liste as chamadas do dia e as páginas novas
mais promissoras (seguidores, se fazem collab, se o tema bate com a CBR). Quem pediu collab entra
sozinho no rodízio (regra 5 acima).

**Stories** (feitos à mão pelo João, para sair com o "Adicionar ao story" clicável; a API não
oferece essa função): o GitHub confere a cada 10 min e manda alerta no celular dele (ntfy)
quando (a) uma collab nossa é aceita e (b) um post da BFC ou da Luz está com engajamento
forte (até 5 por perfil por dia). O bot não publica nada nos Stories.

## 10b. Dossiê do dia (rodada das 23h)

Na última rodada do dia (a que começa às 23h), depois do trabalho normal, monte o **dossiê de
melhorias** e mande ao João com SendUserMessage. Salve também em `dossies/AAAA-MM-DD.md`
(commit e push). Antes de escrever, leia os dossiês dos últimos 7 dias para não repetir
sugestão já feita (se repetir, diga que é reforço e por quê).

**Dados** (não sugira nada sem dado ou exemplo):
- `radar/benchmark.json` (22h45): posts das últimas 24 h de ~13 páginas de notícia, com
  engajamento, formato, horário, tamanho e começo da legenda, hashtags. A **BFC é a referência
  principal**. Abra as miniaturas em `radar/benchmark/img/` (ferramenta Read) para analisar o
  design dos posts que mais renderam. Compare engajamento por mil seguidores entre páginas de
  tamanhos diferentes;
- o bloco `cbr` do mesmo arquivo: nossos posts do dia com alcance, interações, compartilhamentos e
  salvos;
- `registro/posts.jsonl`, `registro/saude.json`, `radar/saude_fontes.json`, os post.json do dia
  (descartes, `historico_revisao`, erros de render/publicação) e
  `gh run list -R Joaobueno02/cbr-bot --limit 60` para falhas.

**Estrutura** (regra do João, 16/10/2026: o que foi feito em poucas linhas; o foco é **o que fazer
para melhorar**. No máximo ~1.200 palavras, 80% delas propositivas):
1. **O dia em 5 linhas**: posts publicados, melhor e pior (link e número), seguidores, collabs
   aceitas, falhas do sistema. Só isso.
2. **Tendências** (desde 20/10/2026 a análise completa sai pelo ChatGPT do João às 22h50, lendo o
   `radar/benchmark.json`; aqui, só 2 ou 3 linhas com o que muda a nossa pauta ou o nosso sistema).
   **Comece por `radar/estouraram.json`**, quando existir (desde 04/11/2026, gerado logo depois do benchmark): cada post
   das páginas de referência medido contra a mediana da própria página no mesmo formato, já sem bicho,
   esporte, fofoca e crime e só com o que toca a lente da CBR. Diga os 2 ou 3 assuntos que mais estouraram
   (múltiplo, página, link), se já demos, se o radar tinha e por que não demos; e, no bloco `cbr`, quais
   posts nossos ficaram 2x acima da nossa mediana (o que repetir) e quais ficaram abaixo da metade. O
   múltiplo é sinal sobre o assunto, não prova de por que o post rendeu:
   - temas que subiram nas páginas de referência e no radar (o que ganhou veículos e engajamento);
   - formatos e ganchos que estão rendendo (Reels com fala, carrossel "entenda", lista, print,
     antes x depois), músicas/áudios em alta quando aparecerem;
   - o que a BFC fez hoje que funcionou e nós não fizemos, e por quê.
3. **Conteúdo: o que postar e como** (propostas concretas para os próximos dias):
   - pautas e séries para testar (com o porquê e o número que sustenta);
   - formato, título, primeira linha da legenda, horário, mix feed/carrossel/Reels;
   - datas do calendário que vêm aí e o ângulo sugerido.
4. **Bastidores: gestão e sistema** (o que melhorar no "motor" da página):
   - gargalos do dia (descartes, revisões reprovadas, foto ruim, atraso de agendamento, fontes fora
     do ar, perfis de movimentos com erro) e a correção técnica proposta;
   - automação nova que pouparia tempo ou créditos, fonte nova que faltou, processo de revisão;
   - custo: quantas chamadas/rodadas o dia gastou e onde dá para economizar;
   - collab: chamadas de parceria do dia e páginas progressistas novas (radar de collab, seção 10);
     a taxa de aceite por página e o ganho de seguidores depois das collabs aceitas (`radar/collabs.json`);
   - formatos: quantos Reels comuns saíram e o alcance deles contra o feed do mesmo dia (bloco `cbr`
     do benchmark), para saber se a meta de 2 Reels por dia está trazendo gente nova.
5. **Riscos** (pedido do João, 20/10/2026; 3 a 5 linhas, só o que mudou ou piorou, com número):
   avisos 2207051 e queda brusca de alcance (sinal de spam); taxa de aceite das collabs (convites sem
   aceite seguidos); posts do dia com foto de veículo/agência paga em vez de licença aberta; posts com
   acusação de crime ou sobre o resultado eleitoral; pautas boas que a triagem perdeu; falhas do Gemini;
   token (dias até o acesso vencer). Se algum risco ficou alto, diga o que propõe, sem aplicar.
6. **Experimentos**: até 3, cada um com hipótese, como medir e esforço
   (pequeno/médio/grande). Ex.: "Reels com 1ª frase em texto grande: mais alcance que o post de foto
   da mesma editoria? Medir alcance em 24 h."
   **Regras de experimento (pedido do João, 04/11/2026; adaptado do ab-testing do marketingskills)**: com uns
   100 de alcance médio, um dia contra outro é ruído. Todo experimento proposto diz: (a) **uma variável só**
   (horário OU formato OU tipo de título, nunca dois juntos); (b) a **métrica principal escolhida antes**
   (alcance em 24 h, envios ou seguidores ganhos) e uma **métrica de proteção** que não pode piorar (ex.: envios
   quando o teste é de alcance); (c) **duração mínima de 7 dias ou 10 posts de cada lado**, o que vier depois;
   (d) **não declarar vencedor antes do prazo**, mesmo que o primeiro dia pareça claro. Experimento em andamento
   aparece no dossiê só com "dia N de 7, sem conclusão" até fechar. No fim, o dossiê diz o resultado com os dois
   números e a diferença, e chama de sinal se a diferença for pequena.

Regras: separe fato (número) de interpretação; não trate correlação de um dia como regra;
**não aplique nada** por conta própria: toda mudança depende do OK do João numa conversa.

## 11. Correção (errata) e crise

Se descobrir erro em post já publicado (seu ou apontado nos comentários):
1. Não apague o post original.
2. Faça um post `gerais` com chapéu "CORREÇÃO", título dizendo o que estava errado e o
   correto, e `"corrige": "<id do post original>"`.
3. Passa pelo revisor como qualquer post.
4. Na notificação ao João, destaque que foi errata e qual post corrige.
Erro grave (acusação errada contra pessoa): avise o João e não publique nada até ele responder.

**Protocolo de crise (pedido do João, 04/11/2026; adaptado do public-relations do marketingskills).** Página
política pequena é alvo fácil: print fora de contexto, acusação de fake news, ataque coordenado nos comentários.
Classifique pelo nível e, na dúvida, suba um nível (responder pouco a um nível 3 é pior que responder demais a um 2).

| Nível | O que é | O que fazer |
|---|---|---|
| **1. Pequeno** | erro que não muda o sentido: grafia, nome de cargo, data trocada sem efeito | avise o João na mensagem da rodada para ele corrigir a legenda no app (o publicador não edita legenda); sem post de correção |
| **2. Erro de fato** | número, data ou atribuição errados que mudam o entendimento | post de correção (passos 1 a 4 acima) **na mesma rodada**, no feed como manda a seção 2 (o Story automático leva a correção a quem segue); se o original rendeu muito, diga isso ao João, que decide se vale também um Reels; avise o João |
| **3. Grave** | acusação errada contra pessoa; post com erro espalhando (envios ou alcance acima de 2x a nossa mediana); pedido de remoção, notificação ou ameaça de processo; ataque coordenado | **pare de publicar**, avise o João com PushNotification na hora e não publique nada até ele responder |
| **Fake atribuído à CBR** | arte falsa com a nossa marca circulando | avise o João; o desmentido mostra a arte verdadeira ao lado da falsa e diz que a falsa não é nossa |

Regras de qualquer nível:
- **Reconheça antes de explicar.** A correção abre com o que estava errado e o que é o certo, com a fonte.
  Contexto e explicação vêm depois, se couberem.
- **Sem "mas".** "Erramos o número; o certo é X, segundo Y." Nada de "erramos, mas o importante é...".
- **Nunca apague crítica nem o post original.** Apagar vira print e uma segunda história, sobre a CBR esconder.
- **Não especule.** Diga só o que está confirmado e o que ainda está sendo checado.
- **Não discuta nos comentários.** Os fatos vão no post de correção; o bot não responde provocação.
- **Registre** no dossiê do dia: o que errou, em que etapa (apuração, título, revisão) e a mudança proposta
  para não repetir.

## 12. Segurança

- Nunca escreva, imprima ou commite o token. Ele só existe no secret `IG_TOKEN` do GitHub.
- Não grave resposta bruta de API em arquivo. O publicador já filtra.
- Não mude `config.json`, workflows ou `registro/` numa execução agendada.
