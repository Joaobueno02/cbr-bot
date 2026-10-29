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

1. **Story automático**: publicar o `story.jpg` (Story nativo 9:16, já gerado pelo render) como Story pela API, logo depois do post. Não mexe na trava visual (é `bot/publicar.py`), mas precisa de aprovação do João.
2. **Slide de fechamento padrão do carrossel**: tipo `fechamento` (logo grande, @comunabrasileira_, "salve e compartilhe").
3. **Arquivar as fontes**: ao publicar, enviar cada link de `fontes`/`apuracao` ao Save Page Now do Internet Archive e gravar o link arquivado no `post.json` (sem travar a publicação se o arquivo falhar).
4. **Registro de rodadas**: script que o Claude chama para gravar uma linha por rodada em `registro/rodadas.jsonl` (hora, curta/completa, candidatos, publicados, descartados antes/depois do render).
5. **Cruzamento BFC × matérias** (`bot/radar.py`, `_cruzar_parceiros`): exigir mais semelhança e ignorar palavras genéricas (Lula, eleição, presidente, governo); sem correspondência boa → "sem correspondência".
6. **Site automático** (GitHub Pages): cada post publicado vira uma página com texto, fontes e imagem; páginas de expediente, "como checamos" e correções; sitemap e RSS. Gerado por workflow, sem custo.
7. **Threads**: publicar o mesmo post no Threads pela API da Meta, no mesmo passo do Instagram, sem quebrar a publicação se o Threads falhar.
8. **`bot/cruzar.py`**: funcionar mesmo sem `feedparser` instalado (import tardio).
