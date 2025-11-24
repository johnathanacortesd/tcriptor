import streamlit as st
import os
import tempfile
from groq import Groq
from moviepy.editor import AudioFileClip

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro",
    page_icon="🎙️",
    layout="wide"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .search-result { background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #ff4b4b; }
    .highlight { background-color: #ffffcc; font-weight: bold; padding: 2px 4px; border-radius: 3px; color: #333; }
    /* Ajuste para que el formulario de búsqueda se vea compacto */
    .stForm { border: none; padding: 0; }
</style>
""", unsafe_allow_html=True)

# --- ESTADO ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "transcript_text" not in st.session_state: st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state: st.session_state.transcript_segments = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "search_results" not in st.session_state: st.session_state.search_results = None # Guardamos resultados para persistencia

# --- UTILIDADES ---
def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

# --- SEGURIDAD ---
def check_password():
    if st.session_state.authenticated: return True
    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            try:
                if pwd == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("⛔ Incorrecta")
            except: st.error("Error en secrets.toml")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: return None

# --- PROCESAMIENTO ROBUSTO DE ARCHIVOS ---
def process_audio_file(uploaded_file):
    """
    Gestión manual de archivos temporales para evitar errores de 'No such file'.
    Soporta archivos grandes (>100MB).
    """
    try:
        # 1. Definir rutas explícitas en el directorio temporal del sistema
        temp_dir = tempfile.gettempdir()
        # Limpiamos el nombre de espacios para evitar problemas con FFmpeg
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"input_{safe_name}")
        output_path = os.path.join(temp_dir, f"processed_{os.path.splitext(safe_name)[0]}.mp3")

        # 2. Escribir el archivo de entrada (usando getbuffer para eficiencia)
        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # 3. Verificar tamaño y tipo
        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv'))
        
        # GROQ tiene límite de 25MB.
        # Si es video O es un audio pesado (>24MB), convertimos.
        if is_video or file_size_mb > 24.0:
            status_text = f"Comprimiendo archivo de {file_size_mb:.1f} MB..."
            with st.spinner(status_text):
                try:
                    # Cargamos clip
                    clip = AudioFileClip(input_path)
                    
                    # Conversión forzada a MP3, Mono (1 canal), 32k bitrate
                    # Esto asegura máxima compatibilidad y mínimo tamaño
                    clip.write_audiofile(
                        output_path, 
                        bitrate="32k", 
                        nbytes=2, 
                        codec='libmp3lame', 
                        ffmpeg_params=["-ac", "1"], # Forzar mono
                        logger=None
                    )
                    clip.close()
                    
                    # Limpiamos entrada para ahorrar espacio
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    
                    # Verificación final
                    new_size = os.path.getsize(output_path) / (1024 * 1024)
                    if new_size > 25.0:
                        st.warning(f"⚠️ El archivo comprimido pesa {new_size:.1f}MB. Puede que Groq lo rechace (Límite 25MB).")
                    
                    return output_path
                    
                except Exception as e:
                    st.error(f"Error interno en conversión (MoviePy): {e}")
                    return None
        
        # Si es audio pequeño, usamos el original
        # Renombramos el input al output deseado para mantener consistencia
        if input_path != output_path:
             # Si ya existe un output viejo, lo borramos
            if os.path.exists(output_path):
                os.remove(output_path)
            os.rename(input_path, output_path)
            
        return output_path

    except Exception as e:
        st.error(f"Error gestionando archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ Archivo demasiado grande ({size_mb:.1f}MB) para la API. Intente recortarlo.")
            return None, None

        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model=model_name,
                response_format="verbose_json",
                language="es",
                temperature=0.0
            )
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"Error API Groq: {e}")
        return None, None

# --- CORRECCIÓN ---
def correct_text_with_llama(client, raw_text):
    system_prompt = (
        "Corrige ortografía y tildes. NO saludos. NO intros. NO resúmenes. "
        "Devuelve SOLO el texto corregido idéntico en contenido."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
            temperature=0.0
        )
        res = completion.choices[0].message.content
        return res.replace("Aquí está el texto corregido:", "").replace("Texto corregido:", "").strip()
    except:
        return raw_text

# --- BÚSQUEDA ---
def search_in_segments(query, segments):
    results = []
    if not query or not segments: return results
    q = query.lower()
    for i, seg in enumerate(segments):
        if q in seg['text'].lower():
            s_idx = max(0, i - 2)
            e_idx = min(len(segments), i + 3)
            prev = " ".join([s['text'] for s in segments[s_idx:i]])
            nxt = " ".join([s['text'] for s in segments[i+1:e_idx]])
            results.append({
                "start": seg['start'],
                "formatted": format_timestamp(seg['start']),
                "match": seg['text'],
                "prev": prev,
                "next": nxt
            })
    return results

# --- MAIN ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    with st.sidebar:
        st.title("⚙️ Configuración")
        model_choice = st.selectbox(
            "Modelo", 
            options=["whisper-large-v3-turbo", "whisper-large-v3"],
            help="Turbo es más rápido. V3 es más preciso."
        )
        st.divider()
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ Transcriptor Pro")

    uploaded_file = st.file_uploader("Subir archivo (MP3, MP4, WAV)", type=["mp3", "mp4", "wav", "m4a"])

    if uploaded_file:
        if st.button("🚀 Procesar", type="primary"):
            with st.status("Procesando...", expanded=True) as status:
                st.write("🔍 Optimizando archivo (puede tardar si es grande)...")
                
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    raw, segs = transcribe_audio_verbose(client, final_path, model_choice)
                    
                    if raw and segs:
                        st.write("✨ Corrección final...")
                        fixed = correct_text_with_llama(client, raw)
                        st.session_state.transcript_text = fixed
                        st.session_state.transcript_segments = segs
                        st.session_state.audio_start_time = 0
                        st.session_state.search_results = None # Limpiar búsquedas previas
                        status.update(label="¡Listo!", state="complete", expanded=False)
                    else: status.update(label="Error Transcripción", state="error")
                else: status.update(label="Error Archivo", state="error")

    # --- REPRODUCTOR DE AUDIO ---
    # Se coloca fuera de pestañas para que esté siempre visible
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    if st.session_state.transcript_text:
        tab_txt, tab_chat = st.tabs(["📝 Transcripción", "💬 Chat"])

        with tab_txt:
            st.markdown("### 🔍 Búsqueda")
            
            # --- FORMULARIO DE BÚSQUEDA (SOLUCIÓN AL STOPPING) ---
            # Al usar st.form, la página NO se recarga mientras escribes, 
            # por lo que el audio NO se detiene hasta que das Enter o click en Buscar.
            with st.form(key="search_form"):
                col_input, col_btn = st.columns([5, 1])
                with col_input:
                    search_query = st.text_input("Palabra clave", placeholder="Escribe y presiona Enter...")
                with col_btn:
                    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                    submit_search = st.form_submit_button("Buscar")
            
            # Lógica de búsqueda
            if submit_search:
                if search_query:
                    st.session_state.search_results = search_in_segments(search_query, st.session_state.transcript_segments)
                else:
                    st.session_state.search_results = None

            # Mostrar resultados (Persistentes)
            if st.session_state.search_results:
                st.success(f"{len(st.session_state.search_results)} coincidencias")
                for i, r in enumerate(st.session_state.search_results):
                    with st.container():
                        b_col, t_col = st.columns([1, 8])
                        with b_col:
                            # Este botón SI recargará la página para mover el audio
                            if st.button(f"▶ {r['formatted']}", key=f"j_{i}"):
                                st.session_state.audio_start_time = int(r['start'])
                                st.rerun()
                        with t_col:
                            st.markdown(
                                f"<div class='search-result'><span style='color:#888'>...{r['prev']}</span> "
                                f"<span class='highlight'>{r['match']}</span> "
                                f"<span style='color:#888'>{r['next']}...</span></div>", 
                                unsafe_allow_html=True
                            )
                if st.button("Limpiar Búsqueda"):
                    st.session_state.search_results = None
                    st.rerun()
                st.divider()

            st.text_area("Texto Completo", value=st.session_state.transcript_text, height=500)
            st.download_button("Descargar", st.session_state.transcript_text, "transcripcion.txt")

        with tab_chat:
            # Chat igual que antes...
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if p := st.chat_input("Pregunta..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.markdown(p)
                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": f"Contexto:\n{st.session_state.transcript_text}"},
                                {"role": "user", "content": p}
                            ], stream=True
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: st.error(str(e))

if __name__ == "__main__":
    if check_password(): main_app()
