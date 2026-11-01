# cbr-bot

Publicação automática da CBR – Comuna Brasileira (@comunabrasileira_).

- `MANUAL.md` — regras editoriais e o passo a passo de cada execução
- `fila/<id>/post.json` — posts; o status anda: renderizar → renderizado → publicar → publicado
- `bot/` — gerador de arte (`render.py`, `arte.py`), publicador (`publicar.py`), trava anti-vazamento
- `referencias/` — posts de referência de cada editoria (padrão visual)
- `registro/` — histórico do que foi publicado e contador da collab
- `config.json` — `publicacao_ativa` liga/desliga a publicação real

O token fica só no secret `IG_TOKEN`. Nunca no código.
