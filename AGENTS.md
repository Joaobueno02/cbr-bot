# AGENTS.md — guia do cbr-bot para agentes de código (Codex e outros)

Leia este arquivo inteiro antes de qualquer mudança, e **leia também `CONTEXTO_CBR.md`** (o que é a
página, o que ela defende, a identidade visual e quem faz o quê). Escreva sempre em português do Brasil
(código, comentários, mensagens de commit e descrição de pull request).

## 1. O que é o projeto

Robô que mantém a página de Instagram **CBR – Comuna Brasileira** (@comunabrasileira_), de notícias
com linha de esquerda, voltada para a classe trabalhadora. Dono e único aprovador: **João**.

Três partes trabalham juntas:

| Quem | O que faz | Onde mexe |
| --- | --- | --- |
| GitHub Actions (`.github/workflows/`) | Radar de notícias, renderização das artes, publicação, alertas, manutenção | Commits automáticos na `main` |
| Claude (tarefa agendada de hora em hora, 7h–23h) | Escolhe a pauta, apura, escreve o `post.json`, revisa e manda publicar | `fila/`, `dossies/`, `pautas/` (direto na `main`) |
| **Você (agente de código)** | Melhora o código, por pull request | Só por branch + PR (seção 4) |

## 2. Mapa do repositório

- `MANUAL.md` — regras editoriais e o passo a passo de cada rodada do Claude. **Não edite sem pedido explícito do João.**
- `config.json` — chaves de operação (`publicacao_ativa`, `max_posts_dia`, collab, `visual_aprovado`...).
- `bot/radar.py` + `bot/fontes.json` — lê ~290 feeds (RSS e Google Notícias) e gera `radar/` (pauta.md, atual.json, saude_fontes.json...).
- `bot/triagem.py`, `bot/triagem_ia.py` — pré-seleção dos candidatos (Gemini).
- `bot/arte.py` — gera o HTML de cada arte (post único 1080x1350, slides de carrossel). Padrões visuais por editoria em `EDITORIAS`, `LOCKUPS`, `PADROES`.
- `bot/render.py` — baixa a foto, captura o HTML com Chromium (Playwright), gera story e Reels (ffmpeg).
- `bot/conferir_design.py` — checagem automática de design.
- `bot/trilha.py` — põe a trilha da editoria no `reels.mp4`.
- `bot/publicar.py` — publica via Instagram Graph API; tem a **trava visual** (seção 5).
- `bot/checar_vazamento.py` — trava contra vazamento do token.
- `fila/<id>/post.json` — um post por pasta; status: `renderizar → renderizado → publicar → publicado` (ou `descartado`, `erro_render`, `erro_publicacao`, `agendado`).
- `registro/` — histórico de publicações, seguidores, relatórios, saúde. **Gerado por scripts; nunca edite à mão.**
- `radar/`, `dossies/`, `pautas/`, `status/` — dados gerados. Não edite.
- `assets/` (fontes, textura) e `referencias/` (posts modelo por editoria) — identidade visual.

## 3. Regras invioláveis

1. **Nunca** escreva, imprima, logue ou commite o token do Instagram (`IG_TOKEN`), chaves de API (`GEMINI_API_KEY`) ou qualquer segredo. Eles só existem nos Secrets do GitHub.
2. **Nunca** faça push direto na `main`. Sempre branch + pull request para o João aprovar.
3. **Nunca** altere `fila/`, `registro/`, `radar/`, `dossies/`, `pautas/`, `status/`. São do robô e do Claude.
4. **Nunca** mude `config.json` → `publicacao_ativa` nem desligue travas (vazamento, visual, intervalo entre posts).
5. Não publique nada no Instagram, não rode `bot/publicar.py` com o token real e não dispare workflows de publicação.
6. Regras editoriais (checagem em duas fontes, acusação com resposta do acusado, opinião separada de fato) estão no `MANUAL.md` e valem para qualquer texto que o código gere.

## 4. Como trabalhar

- Crie uma branch por tarefa: `codex/<assunto-curto>` (ex.: `codex/site-automatico`).
- A `main` recebe commits automáticos várias vezes por hora: faça `git pull --rebase origin main` antes de abrir o PR e resolva conflitos sem desfazer commits do robô.
- Um PR por assunto, pequeno. Na descrição: o que mudou, por quê, como testou, e (se for visual) as imagens de antes e depois.
- Mensagens de commit em português, no imperativo ou descritivas: `radar: corrige feed da Prensa Latina`.

## 5. Trava visual (importante)

`bot/publicar.py` calcula `impressao_visual()` = sha256 de `bot/arte.py`, `bot/render.py` e de tudo em `assets/`.
Se o resultado for diferente de `config.json` → `visual_aprovado`, **a publicação trava**.

Portanto, em qualquer PR que mexa em `bot/arte.py`, `bot/render.py` ou `assets/`:

1. Renderize artes de teste (seção 6) e anexe as imagens no PR.
2. Calcule o novo valor e atualize `visual_aprovado` **no mesmo PR**:
   ```bash
   python -c "import sys; sys.path.insert(0,'bot'); from publicar import impressao_visual; print(impressao_visual())"
   ```
3. Escreva no PR, em destaque: "muda o visual — precisa da aprovação do João".

## 6. Como testar

```bash
pip install -r requirements.txt
python -m playwright install chromium   # e ffmpeg instalado no sistema
```

Teste de arte sem internet: copie um `post.json` publicado para uma pasta temporária **fora de `fila/`**,
troque `status` por `renderizar` e `foto_url` por `repo:<caminho de uma foto do repositório>`
(ex.: `repo:fila/<id>/candidatas/01-grande.jpg`), e rode `render.processar(pasta, pagina)` com uma página do
Playwright (1080x1350). Confira `arte-1.jpg`, `story.jpg` e `reels.mp4`. Não commite essas saídas.

Teste do radar: `python bot/radar.py` (precisa de internet) e confira `radar/saude_fontes.json`; não commite `radar/`.

## 7. Identidade visual (resumo)

- Grade **branca**: economia, educação, saúde, da roça. Grade **preta**: política, eleições, gerais, América Latina.
- Título em Fraunces (serifada), apoio em Archivo, marca em Unbounded. Lockup "EDITORIA + CBR" com o nome vazado no logo (aprovado em 16/10/2026: é intencional).
- Texto de apoio do post único: 24 px. Carrossel: itens 34 px, apoio 30 px.
- Reels: foto com zoom lento de 8%, marca fixa, texto e barra entram juntos (3 camadas, `camadas_reels`).
- Story nativo 9:16 (`post_unico(..., altura=1920)`): foto na metade de cima, título 12% maior, ~300 px livres embaixo para o adesivo de link. A capa do Reels é `capa.jpg` (a arte 4:5 no quadro vertical, para o recorte do grid).
- Nada de imagem gerada por IA como foto de notícia.

## 8. Fila de tarefas (em ordem de prioridade)

0. **Destravar a arte e as rodadas (pedido do João, 15/11/2026; prioridade máxima).** Três PRs separados:
   - **Marca adaptativa** (`bot/arte.py`, `bot/conferir_design.py`; mexe na trava visual): quando o contraste da marca do
     topo com a foto ficar abaixo do limite, o gerador usa sozinho a versão da marca que contrasta (branca em foto escura,
     escura em foto clara) ou uma sombra suave só atrás do logo, sem faixa sólida e sem mudar o layout. A conferência
     automática passa a reprovar só se nem essa versão ficar legível. Antes e depois de 3 artes que caíram por marca
     (Covid/InfoGripe 13/11, garimpo em Seabra 13/11, Mura 14/11). O João recusou a faixa fixa: nada de faixa.
   - **Título sem órfã no Story** (`bot/arte.py`): no `encaixar()`, se o título ficar com palavra solta na última linha ou
     com preposição separada do número ("das | 42 horas"), diminui até 56 px procurando uma quebra boa; se não achar,
     volta ao tamanho original. Caso de teste: `fila/20261114-1815-fux-trava-42h`.
   - **Rodada curta de verdade** (`bot/rodada_curta.py`, `bot/registrar_rodada.py`; não mexe no visual): o registro de
     rodadas passa a gravar as manchetes descartadas (campo `descartes`), e a rodada curta não conta como novo o candidato
     já descartado no mesmo dia, salvo se ele ganhou veículo novo desde o descarte.

0b. **Dois formatos novos aprovados pelo João em 15/11/2026** (mexem na trava visual: antes e depois no PR e "muda o visual — precisa da aprovação do João"):
   - **Feed quadrado** (`formato: "quadrado"`, 1080 × 1080, publicado como imagem de feed): modelo em
     `prototipos/feed-quadrado/modelo.html` e `modelo.png`. Foto ocupando o quadrado inteiro, com brilho reduzido
     (`brightness(.62) contrast(.9) saturate(.88)`), degradê escuro no topo e no pé e cantos escurecidos; acabamento fosco
     (textura `assets/papel.jpg` em overlay a 0,32, grão fino a 0,2 e véu claro a 0,05). Marca no canto superior esquerdo
     (64 px): foice e martelo na cor do ícone da editoria + "CBR" branco em Unbounded 60 px; embaixo, o nome da editoria
     menor (20 px), branco, com só a letra estilizada na cor da editoria. Texto encostado embaixo (132 px do pé):
     chapéu numa **tarja** sólida na cor da editoria com letra branca (Fraunces 740, 56 px, caixa alta); título branco
     (Fraunces 640, 52 px, `text-wrap:balance`, destaque `*...*` com marca-texto na cor da editoria); **sem subtítulo na
     arte** (vai para a legenda). Barra na cor da editoria a 990 px e crédito de 15 px logo abaixo. Margem única de 64 px.
     Sem grade.
   - **Reels "cartão com margem"** (o João escolheu a opção 2 do simulador): quadro 1080 × 1920 com a grade de fundo da
     editoria na tela toda, foto num cartão com 90 px de margem e cantos de 28 px, de 330 a 1070 px; marca a 180 px com 90%
     do tamanho; texto de 1070 a 1640 px (chapéu 48, título 58, apoio 28, margem 90). Imagens em `prototipos/reels-cartao/`.
     Mantém o zoom lento e as 3 camadas do Reels de hoje.
   - **Cores do quadrado por editoria** (modelos em `prototipos/feed-quadrado/editorias/`): tarja e barra na cor de destaque
     (política #E0302A, eleições #FED700 com letra preta, economia #1646E0, América Latina #FF5A1F com o selo do país e a
     barra tecida colorida, roça #4F7A1C com "da roça" escrito à mão embaixo do CBR, saúde #0BB39B, mais vivo que o
     #087A6D de hoje); foice e martelo na cor do ícone da editoria. O "E" de barras (economia, eleições, saúde no fim da
     palavra) tem exatamente a altura das maiúsculas: 3 barras de 3,3 px com 1,8 px entre elas para letra de 20 px (cap
     height 13,5 px), largura 12,3 px, centrado na linha. Foto clara demais leva mais escurecimento.
   - **Termômetro automático na triagem** (`bot/triagem.py`): para cada candidato, gravar em `radar/triagem.json` o campo
     `termometro` com os pontos da regra do MANUAL (nome conhecido +3, aspas ou contradição +2, editoria quente +2, assunto
     quente +2, horário +1/-1), a soma e o formato sugerido (`reels` com 5 ou mais, `quadrado` abaixo). Lista de nomes
     conhecidos em `bot/nomes_conhecidos.json`, editável. O Claude confere e decide; o campo só adianta a conta.
   - O `render.py` gera `arte-1.jpg` no tamanho do formato; `conferir_design.py` aplica as mesmas checagens (contraste da
     marca, órfã, número quebrado) no quadrado. O Claude passa a escolher o formato pelo termômetro da seção 2 do MANUAL.

0c. **Foto específica (pedido do João, 15/11/2026; não mexe na trava visual)** — `bot/sondar.py` e a regra da seção 5 do MANUAL:
   - **Nota de especificidade** por candidata, gravada em `fotos.json` como `especificidade: {nota, motivos, gemini}`:
     +4 do próprio fato (data da foto ou do caminho da URL igual à do fato e legenda que cita o evento), +3 aparece a pessoa
     citada, +2 lugar específico, +1 últimos 6 meses, −2 arquivo com mais de 1 ano, −3 banco de imagem/ilustração/montagem.
     O `sondar.json` passa a trazer `entidades` (pessoas, lugares, evento) e `data_fato`; o sondar lê legenda (`figcaption`),
     `alt`, `title`, crédito e data perto de cada imagem e compara com as entidades. Depois manda as 6 melhores miniaturas
     ao Gemini (visão, mesma chave da triagem; falha não trava) com a pergunta: quem aparece, que lugar é, parece foto do dia
     ou de arquivo, é banco de imagem/ilustração. Ordena por nota, desempate por qualidade.
   - **Filtro de qualidade mais duro:** corte em 1600 px de largura (hoje 1000), sem aviso de ampliação, nitidez mínima,
     e detecção simples de marca d'água/logo/texto nas bordas (descarta ou marca `aviso`). Até 40 candidatas por pauta (hoje 15).
   - **Ondas:** `sondar.json` aceita `onda: 1|2|3`. Onda 1: páginas de todos os veículos que deram o fato. Onda 2: buscas nos
     acervos oficiais (Agência Brasil, Agência Senado, Agência Câmara, Flickr do STF, do Planalto, de ministérios e governos)
     pelas entidades. Onda 3: Wikimedia Commons só com fotos de até 1 ano, mais URLs que o Claude achar na web. O resumo
     do `fotos.json` diz a melhor nota da onda, para o Claude decidir se pede a próxima.
   - Teste: rodar nas pastas `fila/20261114-1815-fux-trava-42h` (deve preferir Fux no STF do dia) e
     `fila/20261113-0715-senado-ajuste-isencoes` (plenário do dia x arquivo) e anexar a ordem antes e depois no PR.

1. **Story automático**: publicar o `story.jpg` (Story nativo 9:16, já gerado pelo render) como Story pela API, logo depois do post. Não mexe na trava visual (é `bot/publicar.py`), mas precisa de aprovação do João.
2. **Slide de fechamento padrão do carrossel**: tipo `fechamento` (logo grande, @comunabrasileira_, "salve e compartilhe").
3. **Arquivar as fontes**: ao publicar, enviar cada link de `fontes`/`apuracao` ao Save Page Now do Internet Archive e gravar o link arquivado no `post.json` (sem travar a publicação se o arquivo falhar).
4. **Registro de rodadas**: script que o Claude chama para gravar uma linha por rodada em `registro/rodadas.jsonl` (hora, curta/completa, candidatos, publicados, descartados antes/depois do render).
5. **Cruzamento BFC × matérias** (`bot/radar.py`, `_cruzar_parceiros`): exigir mais semelhança e ignorar palavras genéricas (Lula, eleição, presidente, governo); sem correspondência boa → "sem correspondência".
6. **Site automático** (GitHub Pages): cada post publicado vira uma página com texto, fontes e imagem; páginas de expediente, "como checamos" e correções; sitemap e RSS. Gerado por workflow, sem custo.
7. **Threads**: publicar o mesmo post no Threads pela API da Meta, no mesmo passo do Instagram, sem quebrar a publicação se o Threads falhar.
8. **`bot/cruzar.py`**: funcionar mesmo sem `feedparser` instalado (import tardio).
