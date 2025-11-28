import streamlit as st
import os
import tempfile
import unicodedata
import math
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
        color: #333;
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
    /* FONDO NEGRO LETRA BLANCA PARA NO RESULTADOS */
    .no-results {
        background-color: #000000;
        color: #ffffff;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
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
    if not isinstance(text, str): return ""
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def fuzzy_search_score(query, text):
    return SequenceMatcher(None, normalize_text(query), normalize_text(text)).ratio()

# --- SEGURIDAD ---
def check_password():
    if st.session_state.authenticated: return True
    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            password_input = st.text_input("Contraseña", type="password", key=f"pwd_{st.session_state.password_attempts}")
            submit_button = st.form_submit_button("Ingresar", use_container_width=True)
        if submit_button:
            try:
                if password_input == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.success("✅ Acceso concedido")
                    st.balloons()
                    st.rerun()
                else: 
                    st.error("⛔ Contraseña incorrecta")
                    st.session_state.password_attempts += 1
            except: st.error("❌ Configura 'app_password' en secrets.toml")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: 
        st.error("❌ Falta 'groq_api_key' en secrets.toml")
        return None

# --- PROCESAMIENTO DE ARCHIVOS ---
def process_audio_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"input_{safe_name}")
        output_path = os.path.join(temp_dir, f"processed_{os.path.splitext(safe_name)[0]}.mp3")

        with open(input_path, "wb") as f: f.write(uploaded_file.getbuffer())

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv', '.avi', '.flv'))
        
        st.info(f"📊 Archivo: {file_size_mb:.1f} MB | Tipo: {'Video' if is_video else 'Audio'}")
        
        if is_video or file_size_mb > 24.0:
            with st.spinner(f"🔄 Optimizando archivo de {file_size_mb:.1f} MB..."):
                try:
                    clip = AudioFileClip(input_path)
                    clip.write_audiofile(output_path, bitrate="32k", nbytes=2, codec='libmp3lame', ffmpeg_params=["-ac", "1", "-ar", "16000"], logger=None)
                    clip.close()
                    if os.path.exists(input_path): os.remove(input_path)
                    return output_path
                except Exception as e:
                    st.error(f"❌ Error conversión: {e}")
                    return None
        
        if input_path != output_path:
            if os.path.exists(output_path): os.remove(output_path)
            os.rename(input_path, output_path)
        return output_path
    except Exception as e:
        st.error(f"❌ Error archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name, enable_punctuation=True):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ Archivo muy grande ({size_mb:.1f}MB).")
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
                params["prompt"] = "Transcripción en español, nombres propios como Popayán, Bogotá con tildes."
            
            transcription = client.audio.transcriptions.create(**params)
            
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"❌ Error Groq: {e}")
        return None, None

# --- CORRECCIÓN DE SEGMENTOS (LA MAGIA) ---
def correct_segments_batch(client, segments, batch_size=20):
    """
    Corrección inteligente que mantiene la sincronización con los timestamps.
    Agrupa segmentos, los corrige respetando separadores y los devuelve.
    """
    corrected_segments = segments.copy()
    total_segments = len(segments)
    num_batches = math.ceil(total_segments / batch_size)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    system_prompt = """Eres un corrector experto. Tu tarea es corregir ortografía, tildes (ej: Popayán, Bogotá) y mayúsculas.
    IMPORTANTE:
    1. Recibirás un texto con el separador '|||'.
    2. Debes devolver el texto corregido manteniendo EXACTAMENTE el mismo número de separadores '|||'.
    3. No unas frases que están separadas.
    4. No agregues saludos ni comentarios, solo el texto."""

    for i in range(0, total_segments, batch_size):
        batch_end = min(i + batch_size, total_segments)
        batch = segments[i:batch_end]
        
        # Unir con separador
        text_chunk = " ||| ".join([s['text'].strip() for s in batch])
        
        try:
            status_text.text(f"✨ Mejorando ortografía: Lote {i//batch_size + 1}/{num_batches}")
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": text_chunk}
                ],
                temperature=0.1
            )
            result = completion.choices[0].message.content.strip()
            
            # Limpieza básica
            for prefix in ["Texto corregido:", "Corrección:"]:
                result = result.replace(prefix, "")
            
            corrected_parts = result.split("|||")
            
            # Verificación de integridad: Si el número de partes coincide, actualizamos
            if len(corrected_parts) == len(batch):
                for idx, corrected_text in enumerate(corrected_parts):
                    corrected_segments[i + idx]['text'] = corrected_text.strip()
            else:
                # Si Llama falló con los separadores, mantenemos el original para no romper timestamps
                pass 
                
        except Exception as e:
            pass # Si falla API, se queda el original
            
        progress_bar.progress(min((i + batch_size) / total_segments, 1.0))
    
    status_text.empty()
    progress_bar.empty()
    return corrected_segments

# --- BÚSQUEDA ---
def search_in_segments(query, segments, context_size=3, fuzzy_threshold=0.7):
    results = []
    if not query or not segments: return results
    
    query_normalized = normalize_text(query)
    
    for i, seg in enumerate(segments):
        text_original = seg['text']
        text_normalized = normalize_text(text_original)
        
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
                "match": text_original,
                "prev": prev, 
                "next": nxt,
                "match_type": match_type,
                "confidence": confidence,
                "score": fuzzy_score if is_fuzzy_match else 1.0
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def export_with_timestamps(segments):
    output = []
    for seg in segments:
        output.append(f"[{format_timestamp(seg['start'])}] {seg['text']}")
    return "\n".join(output)

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    with st.sidebar:
        st.title("⚙️ Configuración")
        model_choice = st.selectbox("Modelo", ["whisper-large-v3-turbo", "whisper-large-v3"])
        st.divider()
        st.session_state.enable_punctuation = st.checkbox("✏️ Puntuación AI", value=True)
        st.divider()
        st.session_state.context_sentences = st.slider("Contexto búsqueda", 1, 10, 3)
        enable_fuzzy = st.checkbox("🎯 Búsqueda inteligente", value=True)
        fuzzy_threshold = st.slider("Sensibilidad", 0.5, 1.0, 0.7) if enable_fuzzy else 1.0
        st.divider()
        large_mode = st.checkbox("📂 Modo Rápido (Sin corrección)", help="Salta corrección para audios muy largos")
        
        if st.session_state.transcript_text:
            st.divider()
            if st.button("🚪 Salir"):
                st.session_state.clear()
                st.rerun()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎙️ Transcriptor Pro")
        st.caption("Transcripción y Búsqueda Sincronizada")
    with col2:
        if st.session_state.transcript_text: st.success("✅ Listo")

    uploaded_file = st.file_uploader("📁 Subir archivo", type=["mp3", "mp4", "wav", "m4a", "mov"])

    if uploaded_file:
        if st.button("🚀 Iniciar", type="primary", use_container_width=True):
            st.session_state.search_results = None
            st.session_state.last_search_query = ""
            
            with st.status("⚙️ Procesando...", expanded=True) as status:
                st.write("🔍 Optimizando archivo...")
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write("🎧 Transcribiendo...")
                    raw_text, segs = transcribe_audio_verbose(client, final_path, model_choice, st.session_state.enable_punctuation)
                    
                    if segs:
                        if not large_mode:
                            st.write("✨ Sincronizando correcciones ortográficas en timestamps...")
                            # AQUÍ ESTÁ EL CAMBIO CLAVE: Corregimos los segmentos, no el texto plano
                            final_segments = correct_segments_batch(client, segs)
                            st.session_state.transcript_segments = final_segments
                            # Reconstruimos el texto completo desde los segmentos corregidos para que coincidan 100%
                            st.session_state.transcript_text = " ".join([s['text'] for s in final_segments])
                        else:
                            st.session_state.transcript_segments = segs
                            st.session_state.transcript_text = raw_text
                        
                        st.session_state.audio_start_time = 0
                        st.session_state.chat_history = []
                        status.update(label="✅ Completado", state="complete", expanded=False)
                        st.balloons()
                    else: status.update(label="❌ Error", state="error")

    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    if st.session_state.transcript_text:
        tab_txt, tab_chat, tab_export = st.tabs(["📝 Transcripción & Búsqueda", "💬 Chat IA", "📥 Exportar"])

        with tab_txt:
            st.markdown("### 🔍 Búsqueda")
            with st.form("search", clear_on_submit=False):
                c1, c2 = st.columns([5,1])
                q = c1.text_input("Buscar", value=st.session_state.last_search_query, placeholder="Ej: popayan")
                if c2.form_submit_button("🔎", use_container_width=True):
                    st.session_state.last_search_query = q
                    st.session_state.search_results = search_in_segments(q, st.session_state.transcript_segments, st.session_state.context_sentences, fuzzy_threshold)
                    st.rerun()

            if st.session_state.last_search_query:
                if st.session_state.search_results:
                    st.success(f"✅ {len(st.session_state.search_results)} resultados")
                    for i, r in enumerate(st.session_state.search_results):
                        with st.container():
                            cb, ct = st.columns([1, 8])
                            if cb.button(f"▶️ {r['formatted']}", key=f"b_{i}"):
                                st.session_state.audio_start_time = int(r['start'])
                                st.rerun()
                            ct.markdown(f"<div class='search-result'><span class='confidence-badge confidence-{r['confidence']}'>{r['confidence']}</span><br><br><span class='context-text'>...{r['prev']}</span> <span class='highlight'>{r['match']}</span> <span class='context-text'>{r['next']}...</span></div>", unsafe_allow_html=True)
                    if st.button("Limpiar"):
                        st.session_state.last_search_query = ""
                        st.session_state.search_results = None
                        st.rerun()
                else:
                    st.markdown(f"<div class='no-results'><strong>⚠️ Sin resultados para '{st.session_state.last_search_query}'</strong></div>", unsafe_allow_html=True)
                    if st.button("Volver"):
                        st.session_state.last_search_query = ""
                        st.rerun()
            
            st.divider()
            st.text_area("Transcripción Completa", value=st.session_state.transcript_text, height=400)

        with tab_chat:
            for m in st.session_state.chat_history:
                st.chat_message(m["role"]).markdown(m["content"])
            if p := st.chat_input("Pregunta sobre el audio..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                st.chat_message("user").markdown(p)
                with st.chat_message("assistant"):
                    stream = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": f"Contexto: {st.session_state.transcript_text}"}, {"role": "user", "content": p}],
                        stream=True
                    )
                    st.write_stream(stream)

        with tab_export:
            st.download_button("Descargar TXT", st.session_state.transcript_text, "transcripcion.txt")
            st.download_button("Descargar con Timestamps", export_with_timestamps(st.session_state.transcript_segments), "timestamps.txt")
            st.code(export_with_timestamps(st.session_state.transcript_segments)[:1000], language="text")

if __name__ == "__main__":
    if check_password(): main_app()
