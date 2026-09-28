
import streamlit as st
from pathlib import Path
import json, datetime, urllib.parse, urllib.request, subprocess, tempfile, shutil, os
from automation import discover_recent, create_briefs, render_original_video

DATA=Path("data"); DATA.mkdir(exist_ok=True)
QUEUE=DATA/"queue.json"
CLIPS=DATA/"clips.json"
BRIEFS=DATA/"briefs.json"
WATCHLIST=DATA/"watchlist.json"
DEFAULT_CREATORS=['auronplay','agustin51','ibai','elxokas','thegrefg','elrubius','peereira7','illojuan','rivers_gg','quackity','westcol','davoo_xeneize']

def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
def save(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")

def setting(name):
    try: return st.secrets.get(name,os.environ.get(name,''))
    except FileNotFoundError: return os.environ.get(name,'')

st.set_page_config(page_title="topclipsflama",page_icon="🎬",layout="centered")
st.title("🎬 topclipsflama")
st.caption("Buscador y editor de clips · uso desde el móvil")

sources=["Twitch","YouTube","Instagram","TikTok","X/Twitter"]
sources.append("Kick")

def search_youtube(query, key, period):
    after = (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=30)).isoformat().replace('+00:00','Z') if period == 'Últimos 30 días' else None
    params={'part':'snippet','type':'video','q':query,'maxResults':25,'key':key,'order':'viewCount' if after else 'relevance'}
    if after: params['publishedAfter']=after
    url='https://www.googleapis.com/youtube/v3/search?'+urllib.parse.urlencode(params)
    with urllib.request.urlopen(url,timeout=15) as response:
        payload=json.load(response)
    results=[{'id':item['id']['videoId'],'title':item['snippet']['title'],
             'url':'https://www.youtube.com/watch?v='+item['id']['videoId'],
             'published':item['snippet']['publishedAt']} for item in payload.get('items',[]) if item.get('id',{}).get('videoId')]
    if results:
        p={'part':'statistics','id':','.join(x['id'] for x in results),'key':key}
        with urllib.request.urlopen('https://www.googleapis.com/youtube/v3/videos?'+urllib.parse.urlencode(p),timeout=15) as response:
            stats=json.load(response)
        counts={x['id']:int(x.get('statistics',{}).get('viewCount',0)) for x in stats.get('items',[])}
        for x in results: x['views']=counts.get(x['id'],0)
        results.sort(key=lambda x:x['views'],reverse=True)
    return results

def twitch_get(endpoint, params, client, token):
    req=urllib.request.Request('https://api.twitch.tv/helix/'+endpoint+'?'+urllib.parse.urlencode(params),
                               headers={'Client-Id':client,'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=15) as response: return json.load(response).get('data',[])

def search_twitch(channel, period, client, token):
    people=twitch_get('users',{'login':channel.strip().removeprefix('@')},client,token)
    if not people: return []
    params={'broadcaster_id':people[0]['id'],'first':100}
    if period=='Últimos 30 días':
        now=datetime.datetime.now(datetime.timezone.utc)
        params.update(started_at=(now-datetime.timedelta(days=30)).isoformat(),ended_at=now.isoformat())
    clips=twitch_get('clips',params,client,token)
    return sorted([{'id':x['id'],'title':x['title'],'url':x['url'],
                   'published':x['created_at'],'views':x.get('view_count',0)} for x in clips],
                  key=lambda x:x['views'],reverse=True)

def discovery_url(platform, query):
    q=urllib.parse.quote(query)
    return {'Twitch':f'https://www.twitch.tv/search?term={q}',
            'Instagram':f'https://www.instagram.com/explore/search/keyword/?q={q}',
            'TikTok':f'https://www.tiktok.com/search?q={q}',
            'Kick':f'https://kick.com/search?query={q}',
            'X/Twitter':f'https://x.com/search?q={q}&src=typed_query'}[platform]

page=st.sidebar.radio("Menú",["Radar de canales","Automático","Buscador","Cola","Añadir fuente","Generador","Configuración"])

if page=="Radar de canales":
    st.header('📡 Radar hispanohablante')
    st.caption('Canales iniciales sugeridos. Revisa los perfiles y modifica sus nombres si es necesario.')
    handles=load(WATCHLIST) if WATCHLIST.exists() else DEFAULT_CREATORS
    raw=st.text_area('Creadores, uno por línea',value='\n'.join(handles),height=230)
    if st.button('Guardar lista'):
        handles=list(dict.fromkeys(x.strip().lstrip('@') for x in raw.splitlines() if x.strip()))[:50]
        save(WATCHLIST,handles)
        st.success(f'{len(handles)} canales guardados.')
    days=st.slider('Buscar últimos días',1,30,7,key='radar_days')
    ytkey=setting('YOUTUBE_API_KEY')
    client=setting('TWITCH_CLIENT_ID')
    token=setting('TWITCH_ACCESS_TOKEN')
    if st.button('Explorar canales',type='primary'):
        found=[]; errors=[]
        for handle in handles[:25]:
            if ytkey:
                try:
                    for x in discover_recent(handle,ytkey,days)[:5]:
                        x.update(platform='YouTube',creator=handle)
                        found.append(x)
                except Exception as exc: errors.append(f'YouTube {handle}: {exc}')
            if client and token:
                try:
                    for x in search_twitch(handle,'Últimos 30 días',client,token):
                        if datetime.datetime.fromisoformat(x['published'].replace('Z','+00:00')) < datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=days): continue
                        x.update(platform='Twitch',creator=handle)
                        found.append(x)
                except Exception as exc: errors.append(f'Twitch {handle}: {exc}')
        st.session_state['radar_results']=sorted(found,key=lambda x:x.get('views',0),reverse=True)
        st.session_state['radar_errors']=errors
    if not ytkey and not (client and token): st.info('Añade credenciales de YouTube o Twitch en Configuración para obtener resultados verificables.')
    for error in st.session_state.get('radar_errors',[]): st.warning(error)
    results=st.session_state.get('radar_results',[])
    st.write(f'{len(results)} resultados. Vistas totales; no representan crecimiento ni viralidad verificada.')
    if results:
        st.download_button('Descargar resultados JSON',json.dumps(results,ensure_ascii=False,indent=2),
                           'radar_clips.json','application/json')
    for x in results[:100]:
        with st.container(border=True):
            st.write(f"**{x['creator']} · {x['platform']}** · {x['title']}")
            st.caption(f"{x['published'][:10]} · {x.get('views',0):,} vistas")
            st.link_button('Abrir clip o vídeo',x['url'])
    st.subheader('Buscar en otras plataformas')
    for handle in handles:
        with st.expander(handle):
            for platform in ['Instagram','TikTok','Kick','X/Twitter']:
                st.link_button(platform,discovery_url(platform,handle),key=f'{handle}{platform}')
elif page=="Automático":
    st.header('⚡ Tendencias recientes')
    st.write('Busca vídeos nuevos y prepara piezas originales basadas en el tema. No copia el vídeo ni el audio de la fuente.')
    topic=st.text_input('Tema o creador',value='streamers españoles')
    days=st.slider('Días recientes',1,30,3)
    if st.button('Buscar y preparar propuestas',type='primary'):
        key=setting('YOUTUBE_API_KEY')
        if not key: st.error('Configura YOUTUBE_API_KEY para la búsqueda automática.')
        else:
            try:
                items=discover_recent(topic,key,days)
                existing=load(BRIEFS)
                seen={x['source_url'] for x in existing}
                new=create_briefs([x for x in items if x['url'] not in seen],topic)
                save(BRIEFS,new+existing)
                st.success(f'{len(new)} propuestas nuevas guardadas.')
            except Exception as exc: st.error(f'Error de búsqueda: {exc}')
    for i,x in enumerate(load(BRIEFS)):
        with st.container(border=True):
            st.write(f"**{x['topic']}** · {x['published'][:10]} · {x['views']:,} vistas")
            st.link_button('Comprobar la tendencia',x['source_url'])
            st.caption('El titular de la fuente es solo una pista; comprueba los hechos antes de publicarlos.')
            script=st.text_area('Guion original',value=x.get('script',''),key=f'brief{i}',height=120)
            if st.button('Crear vídeo de texto original',key=f'render{i}'):
                try:
                    video=render_original_video(script)
                    st.video(video)
                    st.download_button('Descargar MP4',video,file_name='clip_original.mp4',mime='video/mp4',key=f'dl{i}')
                except Exception as exc: st.error(str(exc))
elif page=="Buscador":
    st.header('🔎 Buscador de clips')
    query=st.text_input('Streamer, juego o tema',placeholder='Ej.: Auronplay Minecraft')
    period=st.selectbox('Fecha',['Todas las fechas','Últimos 30 días'])
    platform=st.selectbox('Plataforma',['Todas']+sources)
    if query.strip():
        st.subheader('Búsqueda en plataformas')
        chosen=sources if platform=='Todas' else [platform]
        key=setting('YOUTUBE_API_KEY')
        for p in chosen:
            if p=='YouTube':
                if key and st.button('Buscar vídeos en YouTube'):
                    try: st.session_state['yt_results']=('YouTube',search_youtube(query,key,period))
                    except Exception as exc: st.error(f'YouTube no respondió: {exc}')
                elif not key: st.caption('YouTube: configura YOUTUBE_API_KEY para resultados dentro de la app.')
                st.link_button('Abrir búsqueda de YouTube',f'https://www.youtube.com/results?search_query={urllib.parse.quote(query)}')
            elif p=='Twitch':
                client=setting('TWITCH_CLIENT_ID')
                token=setting('TWITCH_ACCESS_TOKEN')
                if client and token and st.button('Buscar clips del canal en Twitch'):
                    try: st.session_state['tw_results']=('Twitch',search_twitch(query,period,client,token))
                    except Exception as exc: st.error(f'Twitch no respondió: {exc}')
                elif not client or not token: st.caption('Twitch: configura Client ID y token de API para buscar un canal dentro de la app.')
                st.link_button('Abrir Twitch',discovery_url(p,query))
            else:
                st.link_button(f'Abrir {p}',discovery_url(p,query))
        for k in ('yt_results','tw_results'):
            label,items=st.session_state.get(k,('',[]))
            if label not in chosen: continue
            for item in items:
                with st.container(border=True):
                    st.write(f"**{item['title']}** · {item['published'][:10]} · {item['views']:,} vistas")
                    st.link_button('Ver vídeo',item['url'])
                    if st.button('Guardar enlace',key=k+item['id']):
                        q=load(QUEUE)
                        if not any(x['url']==item['url'] for x in q):
                            q.append({'id':item['id'],'url':item['url'],'platform':label,'rights':'Pendiente de comprobar','commercial':False,'attribution':False,'notes':item['title'],'proof':'','status':'REVISIÓN DE DERECHOS','created':datetime.datetime.now().isoformat()})
                            save(QUEUE,q)
                        st.success('Guardado para revisión de derechos.')
    st.subheader('Enlaces guardados')
    saved=load(QUEUE)
    for x in reversed(saved):
        if platform!='Todas' and x['platform']!=platform: continue
        if query and query.casefold() not in (x['url']+' '+x.get('notes','')).casefold(): continue
        st.write(f"{x['platform']} · {x['status']} · {x['created'][:10]}")
        st.link_button('Abrir fuente',x['url'])

elif page=="Añadir fuente":
    st.header("➕ Nueva fuente")
    url=st.text_input("URL")
    platform=st.selectbox("Plataforma",sources)
    rights=st.selectbox("Base para reutilización",[
        "Licencia que permite reutilización comercial",
        "Autorización/licencia propia",
        "Dominio público",
        "Pendiente de comprobar"
    ])
    commercial=st.checkbox("Permite uso comercial")
    attribution=st.checkbox("Requiere atribución")
    notes=st.text_area("Condiciones / notas")
    proof=st.text_input('Enlace al documento de licencia o autorización comercial')
    if st.button("Guardar",type="primary",use_container_width=True):
        if not url.strip(): st.error("Falta la URL.")
        else:
            q=load(QUEUE)
            q.append({"id":datetime.datetime.now().strftime("%Y%m%d%H%M%S%f"),
                      "url":url.strip(),"platform":platform,"rights":rights,
                      "commercial":commercial,"attribution":attribution,
                      "notes":notes,"proof":proof.strip(),"status":"REVISIÓN DE DERECHOS",
                      "created":datetime.datetime.now().isoformat()})
            save(QUEUE,q); st.success("Añadido a la cola.")

elif page=="Cola":
    st.header("📋 Cola de fuentes")
    q=load(QUEUE)
    if not q: st.info("No hay fuentes.")
    for i,x in enumerate(q):
        with st.container(border=True):
            st.write(f"**{x['platform']} · {x['status']}**")
            st.write(x["url"])
            st.caption(f"Derechos: {x['rights']} · Comercial: {'Sí' if x['commercial'] else 'No'}")
            if x["attribution"]: st.caption("⚠️ Añadir atribución al publicar.")
            if x["notes"]: st.caption(x["notes"])
            c1,c2,c3=st.columns(3)
            if c1.button("Aprobar",key=f"ok{i}",use_container_width=True):
                if x["rights"]=="Pendiente de comprobar" or not x.get('commercial') or not x.get('proof'):
                    st.warning("Hace falta una licencia comercial verificable o prueba de titularidad.")
                else:
                    x["status"]="APROBADO"
                    save(QUEUE,q); st.rerun()
            if c2.button("Procesar",key=f"proc{i}",use_container_width=True):
                if x["status"]!="APROBADO":
                    st.warning("Aprueba primero la fuente.")
                else:
                    x["status"]="EN COLA DE PROCESADO"
                    save(QUEUE,q); st.rerun()
            if c3.button("Eliminar",key=f"del{i}",use_container_width=True):
                q.pop(i); save(QUEUE,q); st.rerun()

elif page=="Generador":
    st.header("✂️ Generador de clips")
    st.write('Sube un archivo tuyo o cuyo uso comercial tengas autorizado. El servidor necesita FFmpeg instalado.')
    source=st.file_uploader('Vídeo MP4 o MOV',type=['mp4','mov'])
    owned=st.checkbox('Confirmo que tengo los derechos necesarios para editar y publicar este vídeo, incluido su audio')
    start=st.number_input('Inicio (segundos)',min_value=0.0,value=0.0,step=1.0)
    duration=st.slider('Duración (segundos)',5,180,40)
    title=st.text_input('Título para la publicación')
    description=st.text_area('Descripción y créditos')
    if st.button('Crear MP4 vertical',type='primary',disabled=not(source and owned),use_container_width=True):
        if not shutil.which('ffmpeg'): st.error('Instala FFmpeg en el servidor para crear vídeos.')
        elif source.size>500_000_000: st.error('El archivo supera el límite de 500 MB.')
        else:
            with tempfile.TemporaryDirectory() as tmp:
                inp=Path(tmp)/('input.mov' if source.name.lower().endswith('.mov') else 'input.mp4')
                out=Path(tmp)/'clip.mp4'
                inp.write_bytes(source.getvalue())
                cmd=['ffmpeg','-hide_banner','-loglevel','error','-ss',str(start),'-i',str(inp),'-t',str(duration),
                     '-vf','scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2',
                     '-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart','-y',str(out)]
                result=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
                if result.returncode: st.error('FFmpeg: '+result.stderr[-1500:])
                else:
                    st.session_state['rendered_video']=out.read_bytes()
                    st.session_state['rendered_meta']={'title':title,'description':description,'source_file':source.name}
    if st.session_state.get('rendered_video'):
        st.video(st.session_state['rendered_video'])
        st.download_button('Descargar clip MP4',st.session_state['rendered_video'],'clip_vertical.mp4','video/mp4',use_container_width=True)
        st.download_button('Descargar título y descripción',json.dumps(st.session_state['rendered_meta'],ensure_ascii=False,indent=2),'publicacion.json','application/json')
        meta=st.session_state['rendered_meta']
        clean_title=(meta.get('title') or 'Nuevo vídeo de topclipsflama').strip()
        clean_description=(meta.get('description') or '').strip()
        package={
            'account':'topclipsflama',
            'youtube':{'title':clean_title[:100], 'description':clean_description, 'format':'Shorts'},
            'tiktok':{'caption':(clean_title+'\n'+clean_description)[:2200]},
            'instagram':{'caption':(clean_title+'\n'+clean_description)[:2200], 'format':'Reels'},
            'publication_status':'Borrador: revisión y publicación manual; cuentas sin conexión API'
        }
        st.download_button('Descargar paquete para las tres cuentas',json.dumps(package,ensure_ascii=False,indent=2),
                           'topclipsflama_publicacion.json','application/json',use_container_width=True)

else:
    st.header("⚙️ Configuración")
    st.write('Cuentas indicadas por el titular: **@topclipsflama** en TikTok, Instagram y YouTube.')
    st.write('Estado de integración: **sin conexión API**. El paquete de publicación se descarga desde Generador; subir el vídeo requiere iniciar sesión en cada plataforma.')
    st.write("Modo de publicación: **revisión manual**")
    st.write("Fuentes: Twitch · YouTube · Instagram · TikTok · Kick · X/Twitter")
    st.code('YOUTUBE_API_KEY = "..."\nTWITCH_CLIENT_ID = "..."\nTWITCH_ACCESS_TOKEN = "..."',language='toml')
    st.write("Procesamiento automático de material: **solo tras aprobación de derechos**")
    st.divider()
    st.subheader("Arquitectura")
    st.code("Fuente → derechos → transcripción → detección → clip 9:16 → subtítulos → revisión → publicación")
