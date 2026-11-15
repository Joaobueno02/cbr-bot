import re, asyncio
R='/home/claude/cbr-bot'
ICONE='''<svg width="46" height="46" viewBox="0 0 100 100" aria-hidden="true"><g fill="none" stroke="{c}" stroke-linecap="round"><path d="M43 16 A32 32 0 1 1 24 57" stroke-width="10"/><path d="M25 63 L11 80" stroke-width="12"/><path d="M38 38 L82 82" stroke-width="10"/></g><path d="M14 40 L40 14 L52 26 L26 52 Z" fill="{c}"/></svg>'''
def barras(c): return f'<span class="e"><i style="background:{c}"></i><i style="background:{c}"></i><i style="background:{c}"></i></span>'
def saude_e(c): return f'<span class="se"><b style="background:{c}"></b><i style="background:{c}"></i><i style="background:{c};width:11px"></i><i style="background:{c}"></i></span>'
ED={
 'politica':dict(cor='#E0302A',icone='#E0302A',tt='#fff',nome='POLÍTICA',
   chapeu='Placar zerado',titulo='Fux interrompe votação que estava *4 a 0* pelo calendário das 42 horas',
   foto=f'{R}/fila/20261114-1815-fux-trava-42h/candidatas/02-story.jpg',pos='50% 28%',cred='Foto: Nelson Jr./SCO/STF · Fontes: Metrópoles, Gazeta do Povo · 14/11/2026'),
 'eleicoes':dict(cor='#FED700',icone='#FED700',tt='#101010',nome='EL'+barras('#FED700')+'IÇÕES <span class="ano">2026</span>',
   chapeu='Voto é livre',titulo='Denúncias de assédio eleitoral no trabalho chegam a *4,3 mil* em três dias',
   foto=f'{R}/fila/20261114-1315-13-salario-prazo/candidatas/06-story.jpg',pos='50% 40%',cred='Foto provisória · Fontes: Metrópoles, Jovem Pan · 31/10/2026'),
 'economia':dict(cor='#1646E0',icone='#E3AD16',tt='#fff',nome=barras('#1646E0')+'CONOMIA',
   chapeu='Contas públicas',titulo='Benefícios fiscais encolhem até *20%* com ajuste aprovado pelo Senado',
   foto=f'{R}/fila/20261113-0715-senado-ajuste-isencoes/candidatas/02-grande.jpg',pos='58% 50%',cred='Foto: Ton Molina/Agência Senado · Fontes: Metrópoles, Brasil de Fato · 13/11/2026'),
 'america_latina':dict(cor='#FF5A1F',icone='#FF5A1F',tt='#fff',nome='AMÉRICA LATINA',pais='Paraguai',
   chapeu='Quebra do Ueno',titulo='Professores do Paraguai param as aulas para salvar *US$ 60 milhões* da aposentadoria',
   foto=f'{R}/fila/20261114-1915-exercito-da-pos/candidatas/07-story.jpg',pos='50% 40%',cred='Foto provisória · Fontes: ABC Color, AP · 09/11/2026'),
 'roca':dict(cor='#4F7A1C',icone='#E3AD16',tt='#fff',nome='<span class="mao">da roça</span>',
   chapeu='Demora do Estado',titulo='Demarcação Mura começou em *1993*, e Justiça condena União e Funai pela demora',
   foto=f'{R}/fila/20261114-1115-mura-demarcacao/candidatas/03-grande.jpg',pos='50% 45%',cred='Foto provisória · Fontes: MPF, A Crítica · 14/11/2026'),
 'saude':dict(cor='#087A6D',icone='#E3AD16',tt='#fff',nome='SAÚD'+saude_e('#0FA390'),
   chapeu='Vacina em dia',titulo='Covid aparece em *26,9%* das mortes por vírus respiratório, aponta Fiocruz',
   foto=f'{R}/fila/20261113-1315-covid-reforco/candidatas/07-story.jpg',pos='50% 45%',cred='Foto provisória · Fontes: Fiocruz, Agência Brasil · 13/11/2026'),
}
TECIDO=["#FF5A1F","#FED700","#2BA84A","#1E88E5","#8E3FBF","#E53935"]
def rgba(h,a): return f'rgba({int(h[1:3],16)},{int(h[3:5],16)},{int(h[5:7],16)},{a})'
def titulo(t,c,a):
    return re.sub(r'\*(.+?)\*',lambda m:f'<span class="mk" style="--mk:{rgba(c,a)}">{m.group(1)}</span>',t).replace('US$ ','US$ ').replace('4,3 mil','4,3 mil')
def pagina(k,e):
    if k=='america_latina':
        x,bl,i=0,[],0; pad=[26,10,26,10,54,10]
        while x<952:
            w=min(pad[i%6],952-x); bl.append(f'<i style="left:{x}px;width:{w}px;background:{TECIDO[i%6]}"></i>'); x+=w+4; i+=1
        barra=f'<div class="tecido">{"".join(bl)}</div>'
    else:
        barra=f'<div class="barra" style="background:linear-gradient(90deg,{e["cor"]} 0 86%,rgba(255,255,255,.3) 86%)"></div>'
    selo=f'<div class="selo" style="border-color:{e["cor"]}"><span style="background:{e["cor"]}"></span>{e["pais"]}</div>' if e.get('pais') else ''
    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face{{font-family:'Fraunces';src:url('file://{R}/assets/fonts/fraunces-latin-full-normal.woff2') format('woff2');font-weight:100 900}}
@font-face{{font-family:'Archivo';src:url('file://{R}/assets/fonts/archivo-latin-wght-normal.woff2') format('woff2');font-weight:100 900}}
@font-face{{font-family:'Unbounded';src:url('file://{R}/assets/fonts/unbounded-latin-900-normal.woff2') format('woff2');font-weight:900}}
@font-face{{font-family:'PermanentMarker';src:url('file://{R}/assets/fonts/permanent-marker-latin-400-normal.woff2') format('woff2')}}
html,body{{margin:0}}*{{box-sizing:border-box}}
#q{{width:1080px;height:1080px;position:relative;overflow:hidden;background:#101010;font-family:Archivo,sans-serif;color:#fff}}
#q p{{margin:0}}
.foto{{position:absolute;inset:0}}.foto img{{width:100%;height:100%;object-fit:cover;object-position:{e['pos']};display:block;filter:brightness(.62) contrast(.9) saturate(.88)}}
.escuro{{position:absolute;inset:0;background:linear-gradient(to bottom,rgba(10,10,12,.55) 0%,rgba(10,10,12,0) 20%,rgba(10,10,12,0) 45%,rgba(10,10,12,.8) 75%,rgba(10,10,12,.92) 100%),radial-gradient(ellipse at 50% 45%,rgba(0,0,0,0) 55%,rgba(0,0,0,.35) 100%)}}
.papel{{position:absolute;inset:0;background:url('file://{R}/assets/papel.jpg') center/cover;mix-blend-mode:overlay;opacity:.32}}
.grao{{position:absolute;inset:0;mix-blend-mode:overlay;opacity:.2;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1.2 -.1'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}}
.fosco{{position:absolute;inset:0;background:rgba(235,232,225,.05)}}
.marca{{position:absolute;left:64px;top:52px;line-height:1}}
.topo{{display:flex;align-items:center;gap:12px}}.cbr{{font-family:Unbounded;font-weight:900;font-size:60px;letter-spacing:-3px}}
.ed{{margin:6px 0 0 60px;display:flex;align-items:center;gap:5px;font-weight:600;font-size:20px;letter-spacing:1px}}
.ed .e{{display:flex;flex-direction:column;gap:2.5px;margin-right:1px}}.ed .e i{{display:block;width:13px;height:3.5px;border-radius:2px}}
.ed .ano{{margin-left:6px}}
.ed .se{{position:relative;display:inline-block;width:14px;height:15px;margin-left:1px}}.ed .se b{{position:absolute;left:0;top:0;width:4px;height:15px;border-radius:2px}}
.ed .se i{{position:absolute;left:0;height:4px;width:14px;border-radius:2px}}.ed .se i:nth-of-type(1){{top:0}}.ed .se i:nth-of-type(2){{top:5.5px}}.ed .se i:nth-of-type(3){{top:11px}}
.ed .mao{{font-family:PermanentMarker,cursive;font-size:30px;letter-spacing:0;transform:rotate(-5deg);display:inline-block;border-bottom:3px solid #7DB43A;padding-bottom:1px;margin-top:2px}}
.bloco{{position:absolute;left:64px;right:110px;bottom:132px}}
.selo{{display:inline-flex;align-items:center;gap:9px;padding:6px 14px 6px 10px;border:2px solid;border-radius:40px;font-weight:700;font-size:17px;letter-spacing:3px;text-transform:uppercase;margin-bottom:16px}}
.selo span{{width:11px;height:11px;border-radius:50%;display:inline-block}}
.chapeu{{display:inline-block;padding:10px 16px 6px;font-family:Fraunces,serif;font-weight:740;font-size:56px;line-height:1;letter-spacing:-1px;text-transform:uppercase;font-variation-settings:'SOFT' 0,'WONK' 0}}
.titulo{{margin-top:18px!important;font-family:Fraunces,serif;font-weight:640;font-size:52px;line-height:1.08;letter-spacing:-1px;text-wrap:balance;font-variation-settings:'SOFT' 0,'WONK' 0}}
.mk{{position:relative;z-index:0;font-weight:740;white-space:nowrap}}
.mk::before{{content:'';position:absolute;z-index:-1;left:-.04em;right:-.1em;top:60%;bottom:2%;background:var(--mk);transform:skewX(-16deg)}}
.barra{{position:absolute;left:64px;right:64px;top:990px;height:3px}}
.tecido{{position:absolute;left:64px;width:952px;top:987px;height:6px}}.tecido i{{position:absolute;top:0;height:6px}}
.cred{{position:absolute;left:64px;right:64px;top:1006px;font-weight:700;font-size:15px;letter-spacing:1.6px;text-transform:uppercase;color:rgba(255,255,255,.62);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style></head><body><div id="q">
<div class="foto"><img src="file://{e['foto']}"></div><div class="escuro"></div><div class="papel"></div><div class="grao"></div><div class="fosco"></div>
<div class="marca"><div class="topo">{ICONE.format(c=e['icone'])}<div class="cbr">CBR</div></div><div class="ed">{e['nome']}</div></div>
<div class="bloco">{selo}<div><p class="chapeu" style="background:{e['cor']};color:{e['tt']}">{e['chapeu']}</p></div>
<p class="titulo">{titulo(e['titulo'],e['cor'],.65 if k=='eleicoes' else .75)}</p></div>
{barra}<p class="cred">{e['cred']}</p></div></body></html>'''
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1080,'height':1080})
        for k,e in ED.items():
            open(f'{k}.html','w').write(pagina(k,e))
            await pg.goto(f'file:///tmp/claude-0/ed/{k}.html'); await pg.evaluate('document.fonts.ready'); await pg.wait_for_timeout(500)
            await pg.screenshot(path=f'{k}.png')
        await b.close()
asyncio.run(main())
