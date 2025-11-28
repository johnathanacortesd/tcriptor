import streamlit as st
import os
import tempfile
from groq import Groq
from moviepy.editor import AudioFileClip
import re
from difflib import SequenceMatcher

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro",
    page_icon="🎙️",
    layout="wide"
)

# --- ESTILOS CSS MEJORADOS ---
st.markdown("""
<style>
    .search-result { 
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 12px; 
        border-left: 5px solid #ff4b4b;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .search-result:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .highlight { 
        background-color: #ffeb3b; 
        font-weight: bold; 
        padding: 3px 6px; 
        border-radius: 4px; 
        color: #000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .context-text {
        color: #666;
        font-style: italic;
        line-height: 1.6;
    }
    .no-results {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .confidence-badge {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.85em;
        font-weight: bold;
    }
    .confidence-high { background-color: #28a745; color: white; }
    .confidence-medium { background-color: #ffc107; color: black; }
    .confidence-low { background-color: #dc3545; color: white; }
    
    /* Ajuste para alinear botones en formularios */
    div[data-testid="stForm"] {border: none; padding: 0;}
</style>
""", unsafe_allow_html=True)

# --- ESTADO (SESSION STATE) ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "transcript_text" not in st.session_state: st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state: st.session_state.transcript_segments = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "search_results" not in st.session_state: st.session_state.search_results = None
if "last_search_query" not in st.session_state: st.session_state.last_search_query = ""
if "context_sentences" not in st.session_state: st.session_state.context_sentences = 3
if "enable_punctuation" not in st.session_state: st.session_state.enable_punctuation = True
if "enable_diarization" not in st.session_state: st.session_state.enable_diarization = False
if "password_attempts" not in st.session_state: st.session_state.password_attempts = 0

# --- UTILIDADES MEJORADAS ---
def format_timestamp(seconds):
    """Formato mejorado de timestamp con horas si es necesario"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def normalize_text(text):
    """Normaliza texto para búsqueda más flexible"""
    import unicodedata
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def fuzzy_search_score(query, text):
    """Calcula similitud para búsqueda difusa"""
    return SequenceMatcher(None, normalize_text(query), normalize_text(text)).ratio()

# --- SEGURIDAD ---
def check_password():
    """Sistema de autenticación con soporte para tecla Enter"""
    if st.session_state.authenticated: 
        return True
    
    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            password_input = st.text_input(
                "Contraseña", 
                type="password", 
                key=f"pwd_{st.session_state.password_attempts}"
            )
            submit_button = st.form_submit_button("Ingresar", use_container_width=True)
            
        if submit_button:
            try:
                correct_password = st.secrets["general"]["app_password"]
                if password_input == correct_password:
                    st.session_state.authenticated = True
                    st.success("✅ Acceso concedido")
                    st.balloons()
                    st.session_state.password_attempts += 1
                    st.rerun()
                else: 
                    st.error("⛔ Contraseña incorrecta")
                    st.session_state.password_attempts += 1
            except KeyError:
                st.error("❌ Error: No se encontró 'app_password' en secrets.toml")
            except Exception as e:
                st.error(f"❌ Error inesperado: {str(e)}")
    
    return False

def get_groq_client():
    try: 
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: 
        st.error("❌ Error: No se encontró 'groq_api_key' en secrets.toml")
        return None

# --- PROCESAMIENTO DE ARCHIVOS ---
def process_audio_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"input_{safe_name}")
        output_path = os.path.join(temp_dir, f"processed_{os.path.splitext(safe_name)[0]}.mp3")

        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv', '.avi', '.flv'))
        
        st.info(f"📊 Archivo: {file_size_mb:.1f} MB | Tipo: {'Video' if is_video else 'Audio'}")
        
        if is_video or file_size_mb > 24.0:
            status_text = f"🔄 Optimizando archivo de {file_size_mb:.1f} MB..."
            with st.spinner(status_text):
                try:
                    clip = AudioFileClip(input_path)
                    clip.write_audiofile(
                        output_path, 
                        bitrate="48k",
                        nbytes=2, 
                        codec='libmp3lame', 
                        ffmpeg_params=["-ac", "1", "-ar", "16000"],
                        logger=None
                    )
                    clip.close()
                    if os.path.exists(input_path): 
                        os.remove(input_path)
                    return output_path
                except Exception as e:
                    st.error(f"❌ Error en conversión: {e}")
                    return None
        
        if input_path != output_path:
            if os.path.exists(output_path): 
                os.remove(output_path)
            os.rename(input_path, output_path)
        return output_path

    except Exception as e:
        st.error(f"❌ Error procesando archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name, enable_punctuation=True):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ Archivo ({size_mb:.1f}MB) supera el límite de 25MB de Groq.")
            return None, None

        with open(file_path, "rb") as file:
            params = {
                "file": (file_path, file.read()),
                "model": model_name,
                "response_format": "verbose_json",
                "language": "es",
                "temperature": 0.0
            }
            if enable_punctuation:
                params["prompt"] = "Transcripción en español con puntuación correcta, tildes y mayúsculas apropiadas."
            
            transcription = client.audio.transcriptions.create(**params)
            
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"❌ Error API Groq: {e}")
        return None, None

# --- CORRECCIÓN ---
def correct_text_with_llama(client, raw_text):
    system_prompt = """Eres un corrector ortográfico experto en español.
TAREA: Corrige SOLO ortografía, tildes, puntuación y mayúsculas. Mantén el CONTENIDO EXACTO."""
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1,
            max_tokens=8000
        )
        result = completion.choices[0].message.content
        for prefix in ["Aquí está el texto corregido:", "Texto corregido:", "Corrección:"]:
            result = result.replace(prefix, "")
        return result.strip()
    except Exception as e:
        st.warning(f"⚠️ Corrección omitida: {e}")
        return raw_text

# --- BÚSQUEDA ---
def search_in_segments(query, segments, context_size=3, fuzzy_threshold=0.7):
    results = []
    if not query or not segments: return results
    
    query_normalized = normalize_text(query)
    
    for i, seg in enumerate(segments):
        text_normalized = normalize_text(seg['text'])
        is_exact_match = query_normalized in text_normalized
        fuzzy_score = fuzzy_search_score(query_normalized, text_normalized)
        is_fuzzy_match = fuzzy_score >= fuzzy_threshold
        
        if is_exact_match or is_fuzzy_match:
            s_idx = max(0, i - context_size)
            prev = " ".join([s['text'] for s in segments[s_idx:i]])
            e_idx = min(len(segments), i + context_size + 1)
            nxt = " ".join([s['text'] for s in segments[i+1:e_idx]])
            
            match_type = "exact" if is_exact_match else "fuzzy"
            confidence = "high" if is_exact_match else ("medium" if fuzzy_score >= 0.85 else "low")
            
            results.append({
                "start": seg['start'], 
                "formatted": format_timestamp(seg['start']),
                "match": seg['text'], 
                "prev": prev, 
                "next": nxt,
                "confidence": confidence,
                "score": fuzzy_score if is_fuzzy_match else 1.0
            })
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# --- EXPORTACIÓN ---
def export_with_timestamps(segments):
    output = []
    for seg in segments:
        output.append(f"[{format_timestamp(seg['start'])}] {seg['text']}")
    return "\n".join(output)

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    # SIDEBAR
    with st.sidebar:
        st.title("⚙️ Configuración")
        model_choice = st.selectbox(
            "Selecciona modelo", 
            options=["whisper-large-v3-turbo", "whisper-large-v3"],
            help="Turbo: Rápido | V3: Preciso"
        )
        st.divider()
        st.session_state.enable_punctuation = st.checkbox("✏️ Mejorar puntuación", value=True)
        st.divider()
        st.session_state.context_sentences = st.slider("Oraciones contexto", 1, 10, 3)
        enable_fuzzy = st.checkbox("🎯 Búsqueda inteligente (fuzzy)", value=True)
        fuzzy_threshold = st.slider("Sensibilidad", 0.5, 1.0, 0.7, 0.05) if enable_fuzzy else 1.0
        st.divider()
        large_mode = st.checkbox("📂 Modo Archivo Grande")
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # HEADER
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎙️ Transcriptor Pro")
    with col2:
        if st.session_state.transcript_text: st.success("✅ Listo")

    # UPLOAD
    uploaded_file = st.file_uploader("📁 Subir archivo", type=["mp3", "mp4", "wav", "m4a", "mov", "mkv", "avi"])

    if uploaded_file:
        if st.button("🚀 Iniciar Transcripción", type="primary", use_container_width=True):
            st.session_state.search_results = None
            st.session_state.last_search_query = ""
            with st.status("⚙️ Procesando...", expanded=True) as status:
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    raw, segs = transcribe_audio_verbose(client, final_path, model_choice, st.session_state.enable_punctuation)
                    if raw and segs:
                        st.session_state.transcript_text = raw if large_mode else correct_text_with_llama(client, raw)
                        st.session_state.transcript_segments = segs
                        st.session_state.audio_start_time = 0
                        st.session_state.chat_history = []
                        status.update(label="✅ Completado", state="complete", expanded=False)
                    else: status.update(label="❌ Error transcripción", state="error")
                else: status.update(label="❌ Error archivo", state="error")

    # REPRODUCTOR
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.markdown("### 🎵 Reproductor")
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    # TABS
    if st.session_state.transcript_text:
        tab_txt, tab_chat, tab_export = st.tabs(["📝 Transcripción & Búsqueda", "💬 Chat IA", "📥 Exportar"])

        # --- TAB 1: BÚSQUEDA CORREGIDA ---
        with tab_txt:
            st.markdown("### 🔍 Búsqueda Inteligente")
            
            # Layout: [Formulario de Búsqueda (Input + Botón Buscar)] [Botón Limpiar]
            col_search_main, col_clear_btn = st.columns([6, 1])
            
            # Parte 1: El formulario para permitir Enter
            with col_search_main:
                with st.form(key="search_form", clear_on_submit=False):
                    # Columnas anidadas para poner input y botón lado a lado DENTRO del form
                    c_in, c_btn = st.columns([5, 1])
                    with c_in:
                        search_query = st.text_input(
                            "Buscar", 
                            value=st.session_state.last_search_query,
                            placeholder="Buscar término...",
                            label_visibility="collapsed",
                            key="search_input_widget"
                        )
                    with c_btn:
                        submitted = st.form_submit_button("🔎", use_container_width=True)

            # Parte 2: El botón limpiar fuera del formulario (para no activar submit ni recargar todo)
            with col_clear_btn:
                if st.button("🗑️", help="Limpiar resultados", use_container_width=True):
                    st.session_state.search_results = None
                    st.session_state.last_search_query = ""
                    st.rerun()

            # Lógica de búsqueda
            if submitted:
                if search_query:
                    st.session_state.last_search_query = search_query
                    st.session_state.search_results = search_in_segments(
                        search_query, 
                        st.session_state.transcript_segments,
                        st.session_state.context_sentences,
                        fuzzy_threshold if enable_fuzzy else 1.0
                    )
                else:
                    st.session_state.search_results = None
                    st.session_state.last_search_query = ""
                    st.rerun()

            # Mostrar resultados
            if st.session_state.last_search_query:
                if st.session_state.search_results:
                    st.success(f"✅ **{len(st.session_state.search_results)}** resultados para '{st.session_state.last_search_query}'")
                    
                    for i, r in enumerate(st.session_state.search_results):
                        with st.container():
                            col_btn, col_text = st.columns([1, 8])
                            with col_btn:
                                if st.button(f"▶️ {r['formatted']}", key=f"j_{i}", use_container_width=True):
                                    st.session_state.audio_start_time = int(r['start'])
                                    st.rerun()
                            with col_text:
                                conf_map = {"high": "Exacto", "medium": "Probable", "low": "Similar"}
                                st.markdown(
                                    f"""<div class='search-result'>
                                        <span class='confidence-badge confidence-{r['confidence']}'>{conf_map[r['confidence']]}</span>
                                        <br><br>
                                        <span class='context-text'>...{r['prev']}</span> 
                                        <span class='highlight'>{r['match']}</span> 
                                        <span class='context-text'>{r['next']}...</span>
                                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class='no-results'>
                        <strong>⚠️ Sin resultados</strong><br>
                        No se encontró "<em>{st.session_state.last_search_query}</em>"
                    </div>""", unsafe_allow_html=True)
            
            st.divider()
            st.text_area("Transcripción", value=st.session_state.transcript_text, height=400, label_visibility="collapsed")

        with tab_chat:
            st.markdown("### 💬 Asistente IA")
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if p := st.chat_input("💭 Tu pregunta..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.markdown(p)
                
                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"Contexto:\n{st.session_state.transcript_text[:20000]}\nResponde solo basado en esto."},
                                {"role": "user", "content": p}
                            ], 
                            stream=True, temperature=0.2, max_tokens=1000
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: st.error(f"Error: {e}")
            
            if st.session_state.chat_history:
                if st.button("🗑️ Limpiar chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        with tab_export:
            st.markdown("### 📥 Exportar")
            c1, c2 = st.columns(2)
            with c1:
                st.download_button("📄 .txt", st.session_state.transcript_text, "transcripcion.txt", use_container_width=True)
                st.download_button("📝 .md", st.session_state.transcript_text, "transcripcion.md", "text/markdown", use_container_width=True)
            with c2:
                ts_txt = export_with_timestamps(st.session_state.transcript_segments)
                st.download_button("⏱️ Con tiempo", ts_txt, "t_timestamps.txt", use_container_width=True)
            st.code(ts_txt[:500] + "...", language="text")

if __name__ == "__main__":
    if check_password(): main_app()
