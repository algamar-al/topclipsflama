# topclipsflama · radar de clips y vídeo original para móvil

El usuario indica que ha creado **@topclipsflama** en TikTok, Instagram y YouTube. El proyecto no contiene credenciales, no ha autenticado esos perfiles y no publica en ellos. La pestaña Generador exporta un MP4 y un paquete JSON con título/descripción adaptados a Shorts, TikTok y Reels para revisión y subida manual.

La pestaña **Automático** consulta vídeos recientes de YouTube mediante su API, los ordena por visitas y guarda propuestas sin duplicados. Cada propuesta conserva el enlace para comprobar la noticia y permite editar un guion propio y descargar un MP4 vertical de texto, sin audio ni imágenes ajenas. Configura `YOUTUBE_API_KEY` y FFmpeg en el servidor. La búsqueda se ejecuta al pulsar el botón; no hay tareas en segundo plano ni publicación automática.

**Antes de publicar:** comprueba los hechos, sustituye el texto provisional por tu análisis y revisa la calidad del vídeo. La detección de una tendencia no otorga derechos sobre el vídeo original. Una pieza de texto repetitiva puede no cumplir las reglas de monetización. Crear canales, conectar cuentas y publicar mediante las API requiere autenticación del titular y configuración adicional por plataforma.

## Radar de canales
Incluye una lista editable de 12 creadores hispanohablantes para empezar. Con credenciales de YouTube y Twitch, el botón **Explorar canales** consulta resultados fechados y con vistas, y permite descargar un JSON. Twitch consulta clips del canal; la búsqueda de YouTube usa el nombre del creador como término y **puede incluir vídeos de terceros**. Comprueba el canal de cada resultado. Instagram, TikTok, Kick y X se abren como búsquedas externas: no hay extracción automática ni métricas verificadas de esas redes. Las credenciales no se incluyen en el ZIP.

MVP orientado a Android mediante una interfaz web.

Incluye:
- YouTube, Twitch, Instagram, TikTok, Kick y X/Twitter como fuentes.
- Búsqueda interna de YouTube mediante YouTube Data API (requiere clave), con número de visualizaciones.
- Búsqueda de clips de un canal Twitch mediante Helix (requiere Client ID y token); clips recientes o de cualquier fecha, ordenados por visualizaciones.
- Enlaces de búsqueda para las otras cinco plataformas y catálogo local filtrable.
- Filtro de vídeos recientes (30 días) o de cualquier fecha en YouTube y Twitch.
- Editor de archivos MP4/MOV subidos por el usuario: recorte temporal, formato vertical 1080×1920 y descarga del vídeo y sus metadatos. Requiere FFmpeg en el servidor.
- Registro de derechos y condiciones.
- Cola de aprobación.
- Parámetros de generación de clips.
- Preparación para integrar transcripción, detección de momentos y renderizado.

## Próximo módulo
Conectar un backend de procesamiento de vídeo autorizado:
1. obtener el archivo mediante una vía permitida;
2. transcribir;
3. puntuar segmentos;
4. seleccionar candidatos;
5. renderizar 9:16;
6. generar subtítulos;
7. devolver el clip a la cola de revisión.

## Instalación desde Android
Descomprime el ZIP. En un ordenador o servidor con Python 3.10+ y FFmpeg, ejecuta `pip install -r requirements.txt` y `streamlit run app.py --server.address 0.0.0.0`. Abre la dirección del servidor desde Chrome en el móvil (misma red o alojamiento HTTPS). También puedes usar un alojamiento Python que admita Streamlit y FFmpeg. El ZIP por sí solo no es una app Android instalable.

Para la búsqueda interna, añade a `.streamlit/secrets.toml` las variables `YOUTUBE_API_KEY`, `TWITCH_CLIENT_ID` y `TWITCH_ACCESS_TOKEN`; también se aceptan como variables de entorno. Crea la clave de YouTube Data API v3 en Google Cloud y un cliente/token de Twitch Developer. Mantén los tokens fuera del ZIP y no compartas ese archivo de configuración.

## Abrir desde Android mediante Streamlit Community Cloud
Sube `app.py`, `automation.py`, `requirements.txt` y `packages.txt` a la raíz de un repositorio GitHub bajo tu control. En Streamlit Community Cloud crea una app desde ese repositorio con archivo principal `app.py`. En Advanced settings → Secrets puedes configurar las claves para consultar las API. `packages.txt` instala FFmpeg en el servidor. Conserva los secretos fuera de GitHub. Necesitas iniciar sesión en GitHub y Streamlit; el ZIP por sí solo no crea una URL pública.

La búsqueda externa abre la página de cada plataforma: sus resultados no se importan automáticamente. La clasificación por visualizaciones es una señal aproximada, no una predicción de viralidad. Un enlace guardado entra en revisión de derechos. El editor procesa únicamente el archivo que subes; no descarga vídeos ajenos. No hay transcripción, selección automática de momentos ni publicación directa en cuentas todavía. La aprobación exige registrar uso comercial y un enlace de prueba, pero no verifica jurídicamente la licencia. Una licencia tampoco garantiza que la plataforma acepte el contenido para monetización.
