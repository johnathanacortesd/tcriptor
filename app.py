import streamlit as st
import os
import tempfile
from groq import Groq
from moviepy.editor import AudioFileClip
import re
from difflib import SequenceMatcher

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro v2",
    page_icon="🎙️",
    layout="wide"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .search-result { 
        background-color: #f0f2f6;
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        border-left: 5px solid #ff4b4b;
    }
    .highlight { 
        background-color: #ffff00; 
        font-weight: bold; 
        color: #000;
        padding: 0 4px;
    }
    .match-tag {
        font-size: 0.8em;
        background-color: #e0e0e0;
        padding: 2px 6px;
        border-radius: 4px;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- ESTADO ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "transcript_text" not in st.session_state: st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state: st.session_state.transcript_segments = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "search_results" not in st.session_state: st.session_state.search_results = None
if "password_attempts" not in st.session_state: st.session_state.password_attempts = 0

# --- UTILIDADES ---
def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def normalize_text(text):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower().strip()

# --- SEGURIDAD ---
def check_password():
    if st.session_state.authenticated: return True
    st.title("🔒 Acceso Restringido")
    with st.form("login"):
        pwd = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            try:
                if pwd == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("Contraseña incorrecta")
            except: st.error("Configura secrets.toml primero")
    return False

def get_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: return None

# --- PROCESAMIENTO DE AUDIO (CORREGIDO PARA EVITAR RECORTES) ---
def process_audio_file(uploaded_file):
    """
    Lógica mejorada:
    1. Guarda el archivo original.
    2. Si es video, extrae audio SIN comprimir agresivamente primero.
    3. Verifica el tamaño del AUDIO resultante.
    4. Solo comprime si el AUDIO supera los 25MB.
    Esto evita recortar el inicio en archivos de video grandes (ej. 39MB MP4).
    """
    try:
        temp_dir = tempfile.gettempdir()
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        input_path = os.path.join(temp_dir, f"raw_{uploaded_file.name}")
        
        # Guardar archivo subido
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
            
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = file_ext in ['.mp4', '.mov', '.mkv', '.avi', '.webm']
        
        st.info(f"📁 Archivo recibido: {file_size_mb:.2f} MB ({'Video' if is_video else 'Audio'})")

        # Ruta final esperada
        final_audio_path = os.path.join(temp_dir, "ready_to_transcribe.mp3")
        
        # Caso 1: Es Video -> Extraer audio primero (Calidad media para ver tamaño real)
        if is_video:
            status = st.empty()
            status.info("🔄 Extrayendo audio del video...")
            try:
                clip = AudioFileClip(input_path)
                # Escribir a un archivo temporal intermedio para verificar tamaño
                temp_audio_path = os.path.join(temp_dir, "temp_extracted.mp3")
                
                # Usamos logger=None para velocidad, bitrate estándar 128k primero
                clip.write_audiofile(temp_audio_path, bitrate="128k", logger=None)
                clip.close()
                
                extracted_size = os.path.getsize(temp_audio_path) / (1024 * 1024)
                
                # Si el audio extraído sigue siendo > 25MB, comprimimos agresivamente
                if extracted_size > 24.5:
                    status.warning(f"📉 Audio extraído grande ({extracted_size:.1f}MB). Comprimiendo...")
                    clip = AudioFileClip(temp_audio_path)
                    clip.write_audiofile(
                        final_audio_path, 
                        bitrate="32k",  # Bitrate bajo
                        nbytes=2,
                        codec='libmp3lame',
                        ffmpeg_params=["-ac", "1", "-ar", "16000"], # Mono, 16kHz
                        logger=None
                    )
                    clip.close()
                else:
                    # Si el audio es pequeño, lo usamos tal cual (evita recortes)
                    if os.path.exists(final_audio_path): os.remove(final_audio_path)
                    os.rename(temp_audio_path, final_audio_path)
                    
                status.success("✅ Audio listo")
                return final_audio_path
                
            except Exception as e:
                st.error(f"Error extrayendo audio: {e}")
                return None

        # Caso 2: Es Audio
        else:
            # Si es audio y > 25MB, comprimir
            if file_size_mb > 24.5:
                st.warning("🔄 El audio supera 25MB. Comprimiendo...")
                try:
                    clip = AudioFileClip(input_path)
                    clip.write_audiofile(
                        final_audio_path, 
                        bitrate="32k", 
                        ffmpeg_params=["-ac", "1", "-ar", "16000"],
                        logger=None
                    )
                    clip.close()
                    return final_audio_path
                except Exception as e:
                    st.error(f"Error comprimiendo: {e}")
                    return None
            else:
                return input_path

    except Exception as e:
        st.error(f"❌ Error crítico en archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio(client, file_path, model, prompt_txt):
    try:
        with open(file_path, "rb") as file:
            # Prompt mejorado para evitar cortes de palabras
            final_prompt = prompt_txt + " Asegúrate de transcribir cada palabra completa sin cortar finales. Usa puntuación correcta."
            
            return client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model=model,
                response_format="verbose_json",
                language="es",
                temperature=0.0, # Temperatura 0 para máxima precisión
                prompt=final_prompt
            )
    except Exception as e:
        st.error(f"Error API: {e}")
        return None

# --- CORRECCIÓN ORTOGRÁFICA (OPCIONAL) ---
def correct_style(client, text):
    """
    Usa Llama para arreglar puntuación, PERO advierte al usuario
    que esto puede causar discrepancias con la búsqueda.
    """
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Eres un editor experto. Corrige SOLO ortografía, acentos y puntuación. NO cambies palabras, NO resumas. Devuelve solo el texto corregido."},
                {"role": "user", "content": text}
            ]
        )
        return resp.choices[0].message.content
    except:
        return text

# --- BÚSQUEDA ---
def search_segments(query, segments):
    results = []
    if not query or not segments: return results
    
    q_norm = normalize_text(query)
    
    for i, seg in enumerate(segments):
        t_norm = normalize_text(seg['text'])
        
        # Búsqueda exacta y parcial
        if q_norm in t_norm:
            # Contexto
            start_idx = max(0, i - 1)
            end_idx = min(len(segments), i + 2)
            context_prev = " ".join([s['text'] for s in segments[start_idx:i]])
            context_next = " ".join([s['text'] for s in segments[i+1:end_idx]])
            
            results.append({
                "time": seg['start'],
                "fmt_time": format_timestamp(seg['start']),
                "match": seg['text'],
                "prev": context_prev,
                "next": context_next
            })
    return results

# --- APP PRINCIPAL ---
def main():
    client = get_client()
    if not client: return

    # BARRA LATERAL
    with st.sidebar:
        st.header("⚙️ Configuración")
        model = st.selectbox("Modelo", ["whisper-large-v3", "whisper-large-v3-turbo"])
        
        st.divider()
        st.markdown("### 🎯 Modo de Precisión")
        
        use_ai_correction = st.checkbox(
            "✨ Mejorar ortografía con IA", 
            value=False,
            help="Si se activa, Llama corregirá el texto. NOTA: Puede haber diferencias entre lo que lees y lo que busca el buscador."
        )
        
        if use_ai_correction:
            st.warning("⚠️ Al activar esto, el texto mostrado ('podría') puede ser distinto a lo que el buscador encuentra en el audio ('podr'). Desactívalo para fidelidad total.")
        else:
            st.success("✅ Modo Fidelidad: Lo que ves es exactamente lo que el modelo escuchó.")

        st.divider()
        if st.button("🚪 Salir"):
            st.session_state.clear()
            st.rerun()

    # INTERFAZ PRINCIPAL
    st.title("🎙️ Transcriptor Pro v2")
    
    uploaded_file = st.file_uploader("Subir archivo (Video/Audio)", type=['mp3','mp4','m4a','wav','mov'])
    
    if uploaded_file:
        if st.button("🚀 Transcribir", type="primary", use_container_width=True):
            with st.status("Procesando...", expanded=True) as status:
                
                # 1. Procesamiento de audio mejorado
                st.write("🔧 Preparando audio (Sin recortar inicio)...")
                audio_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = audio_path
                
                if audio_path:
                    # 2. Transcripción
                    st.write(f"🎧 Transcribiendo con {model}...")
                    result = transcribe_audio(client, audio_path, model, "Transcripción exacta, palabra por palabra.")
                    
                    if result:
                        raw_text = result.text
                        segments = result.segments
                        
                        # 3. Manejo de corrección
                        if use_ai_correction:
                            st.write("✨ Aplicando corrección de estilo...")
                            final_text = correct_style(client, raw_text)
                        else:
                            final_text = raw_text
                            
                        st.session_state.transcript_text = final_text
                        st.session_state.transcript_segments = segments
                        
                        status.update(label="✅ Completado", state="complete", expanded=False)
                        st.rerun()
                    else:
                        status.update(label="❌ Falló la transcripción", state="error")

    # RESULTADOS
    if st.session_state.transcript_text:
        # Reproductor
        if st.session_state.audio_path:
            st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

        tab1, tab2 = st.tabs(["🔍 Búsqueda y Texto", "📥 Exportar"])
        
        with tab1:
            # Búsqueda con ENTER habilitado
            with st.form(key="search_form"):
                col_in, col_btn = st.columns([5,1])
                with col_in:
                    query = st.text_input("Buscar palabra o frase", placeholder="Escribe y presiona Enter...")
                with col_btn:
                    searched = st.form_submit_button("🔎")
            
            # Lógica de búsqueda
            if searched or query:
                results = search_segments(query, st.session_state.transcript_segments)
                
                if results:
                    st.success(f"Encontrado {len(results)} veces")
                    for r in results:
                        col_play, col_txt = st.columns([1, 6])
                        with col_play:
                            if st.button(f"▶ {r['fmt_time']}", key=r['time']):
                                st.session_state.audio_start_time = int(r['time'])
                                st.rerun()
                        with col_txt:
                            # Resaltar la coincidencia
                            match_display = r['match'].replace(query, f"<span class='highlight'>{query}</span>")
                            # Si usamos búsqueda flexible/case-insensitive, mejor resaltar visualmente sin replace simple
                            
                            st.markdown(f"""
                            <div class='search-result'>
                                <span class='match-tag'>Seguridad: Alta</span><br>
                                <i>...{r['prev']}</i> 
                                <strong>{r['match']}</strong> 
                                <i>{r['next']}...</i>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    if query:
                        st.warning(f"No se encontró '{query}'.")
                        if use_ai_correction:
                            st.info("💡 Consejo: Tienes la 'Mejora con IA' activada. La palabra podría estar corregida en el texto pero incompleta en el audio original. Prueba desactivar la IA en la barra lateral.")

            st.divider()
            st.text_area("Texto Completo", st.session_state.transcript_text, height=400)

        with tab2:
            st.download_button("Descargar TXT", st.session_state.transcript_text, "transcripcion.txt")

if __name__ == "__main__":
    if check_password():
        main()
