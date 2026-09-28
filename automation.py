"""Discovery and original, text-only video rendering. No third-party media downloads."""
import datetime
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path


def _api(endpoint, params):
    url = 'https://www.googleapis.com/youtube/v3/' + endpoint + '?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def discover_recent(query, key, days=3):
    if not query.strip() or not key:
        raise ValueError('Faltan tema o clave de YouTube.')
    after = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat().replace('+00:00', 'Z')
    found = _api('search', {'part':'snippet','type':'video','q':query,'maxResults':25,
                            'order':'date','publishedAfter':after,'key':key}).get('items', [])
    ids = [x['id']['videoId'] for x in found if x.get('id', {}).get('videoId')]
    if not ids:
        return []
    stats = _api('videos', {'part':'statistics','id':','.join(ids),'key':key}).get('items', [])
    views = {x['id']:int(x.get('statistics', {}).get('viewCount', 0)) for x in stats}
    items = [{'title':x['snippet']['title'], 'url':'https://www.youtube.com/watch?v='+x['id']['videoId'],
              'published':x['snippet']['publishedAt'], 'views':views.get(x['id']['videoId'], 0)}
             for x in found if x.get('id', {}).get('videoId')]
    return sorted(items, key=lambda x:x['views'], reverse=True)


def create_briefs(items, topic):
    return [{'topic':topic, 'source_title':x['title'], 'source_url':x['url'],
             'published':x['published'], 'views':x['views'],
             'script':f'¿Qué está pasando con {topic}?\nUna tendencia reciente está llamando la atención.\nConsulta la fuente y escribe aquí tu análisis original antes de publicar.'}
            for x in items]


def render_original_video(script):
    """Make a simple 9:16 graphic video with no copied footage, audio or music."""
    if not shutil.which('ffmpeg'):
        raise RuntimeError('FFmpeg no está instalado en el servidor.')
    if not script.strip() or len(script) > 1200:
        raise ValueError('Escribe un guion de 1 a 1200 caracteres.')
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError('Instala Pillow para generar el vídeo.') from exc
    font_path = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font = ImageFont.truetype(font_path, 54)
    words = script.strip().split()
    lines, line = [], ''
    for word in words:
        candidate = (line + ' ' + word).strip()
        if ImageDraw.Draw(Image.new('RGB',(1,1))).textlength(candidate,font=font) > 850 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line: lines.append(line)
    if len(lines) > 18:
        raise ValueError('El texto no cabe en pantalla; acorta el guion.')
    im = Image.new('RGB', (1080,1920), '#14243a')
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((75,180,1005,1740),radius=55,fill='#203956')
    draw.text((115,270),'EN TENDENCIA',font=font,fill='#49e2b4')
    y = 440
    for line in lines:
        draw.text((115,y),line,font=font,fill='white')
        y += 70
    with tempfile.TemporaryDirectory() as tmp:
        png, mp4 = Path(tmp)/'card.png', Path(tmp)/'video.mp4'
        im.save(png)
        result = subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-loop','1','-framerate','25',
                                 '-i',str(png),'-t','12','-c:v','libx264','-pix_fmt','yuv420p',
                                 '-movflags','+faststart','-y',str(mp4)],capture_output=True,text=True,timeout=90)
        if result.returncode:
            raise RuntimeError(result.stderr[-600:])
        return mp4.read_bytes()
