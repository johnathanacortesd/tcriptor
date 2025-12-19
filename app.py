import streamlit as st
import os
import tempfile
import unicodedata
from groq import Groq
from difflib import SequenceMatcher
import hashlib
import json

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
        padding: 2px 5px; 
        border-radius: 4px; 
        color: #000;
        box-shadow: 0 1px 3px rgba(0,0,0,0.2);
    }
    .context-text {
        color: #777;
        font-style: italic;
        line-height: 1.6;
    }
    .segment-text {
        color: #333;
        font-weight: 400;
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
        margin-bottom: 10px;
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
if "corrected_segments" not in st.session_state: st.session_state.corrected_segments = None
if "raw_transcript" not in st.session_state: st.session_state.raw_transcript = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "search_results" not in st.session_state: st.session_state.search_results = None
if "last_search_query" not in st.session_state: st.session_state.last_search_query = ""
if "context_sentences" not in st.session_state: st.session_state.context_sentences = 3
if "password_attempts" not in st.session_state: st.session_state.password_attempts = 0
if "correction_applied" not in st.session_state: st.session_state.correction_applied = False

# --- UTILIDADES ---
def format_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def normalize_text(text):
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def fuzzy_search_score(query, text):
    return SequenceMatcher(None, normalize_text(query), normalize_text(text)).ratio()

# --- SEGURIDAD ---
def check_password():
    if st.session_state.authenticated: 
        return True
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
                    st.rerun()
                else: 
                    st.error("⛔ Contraseña incorrecta")
                    st.session_state.password_attempts += 1
            except:
                st.error("❌ Error: No se encontró 'app_password' en secrets.toml")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: return None

def validate_audio_file(uploaded_file):
    MAX_SIZE_MB = 25
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size_mb > MAX_SIZE_MB:
        return False, f"El archivo ({file_size_mb:.1f}MB) excede el límite de {MAX_SIZE_MB}MB"
    return True, f"Archivo válido: {file_size_mb:.1f}MB"

def save_audio_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        filename_normalized = unicodedata.normalize('NFKD', uploaded_file.name).encode('ascii', 'ignore').decode('ascii')
        safe_name = "".join([c for c in filename_normalized if c.isalnum() or c in ('.', '_', '-')]).strip()
        file_path = os.path.join(temp_dir, f"original_{safe_name}")
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except: return None

# --- PROCESAMIENTO ---
def transcribe_audio_precision(client, file_path, model_name):
    try:
        with st.spinner(f"🎧 Transcribiendo con {model_name}..."):
            with open(file_path, "rb") as file:
                params = {
                    "file": (os.path.basename(file_path), file.read()),
                    "model": model_name,
                    "response_format": "verbose_json",
                    "language": "es",
                    "temperature": 0.0,
                    "prompt": "Transcripción precisa en español. Mantén TODAS las palabras, muletillas y repeticiones."
                }
                transcription = client.audio.transcriptions.create(**params)
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"❌ Error en Groq: {e}")
        return None, None

def correct_orthography_only(client, raw_text, segments, max_chunk_size=6000):
    if len(raw_text) > max_chunk_size:
        chunks = []
        current_chunk = ""
        for line in raw_text.split(". "):
            if len(current_chunk) + len(line) < max_chunk_size:
                current_chunk += line + ". "
            else:
                chunks.append(current_chunk)
                current_chunk = line + ". "
        if current_chunk: chunks.append(current_chunk)
        corrected_chunks = [_correct_single_chunk(client, c) for c in chunks]
        corrected_text = " ".join(corrected_chunks)
    else:
        corrected_text = _correct_single_chunk(client, raw_text)
    
    # Mapeo a segmentos
    corrected_segments = []
    corrected_sentences = corrected_text.replace('. ', '.|').replace('? ', '?|').replace('! ', '!|').split('|')
    for i, seg in enumerate(segments):
        text = corrected_sentences[i].strip() if i < len(corrected_sentences) else seg['text']
        corrected_segments.append({'start': seg['start'], 'end': seg['end'], 'text': text})
    
    return corrected_text, corrected_segments

def _correct_single_chunk(client, text_chunk):
    system_prompt = "Eres un corrector ortográfico ULTRA CONSERVADOR. Solo corrige tildes, puntuación y mayúsculas. NUNCA cambies, quites o agregues palabras ni muletillas."
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text_chunk}],
            temperature=0.0
        )
        return completion.choices[0].message.content.strip()
    except: return text_chunk

# --- MEJORADO: FUNCIÓN DE BÚSQUEDA ---
def search_in_segments(query, segments, corrected_segments, context_size=3, fuzzy_threshold=0.7):
    results = []
    if not query or not segments: return results
    
    query_normalized = normalize_text(query)
    
    for i, seg in enumerate(segments):
        # Usar texto corregido para visualización si existe
        display_text = corrected_segments[i]['text'] if corrected_segments else seg['text']
        text_normalized = normalize_text(display_text)
        
        is_exact_match = query_normalized in text_normalized
        fuzzy_score = fuzzy_search_score(query_normalized, text_normalized)
        is_fuzzy_match = fuzzy_score >= fuzzy_threshold
        
        if is_exact_match or is_fuzzy_match:
            # Lógica de resaltado preciso
            before_match_in_seg = display_text
            match_word = ""
            after_match_in_seg = ""

            if is_exact_match:
                start_idx = text_normalized.find(query_normalized)
                end_idx = start_idx + len(query_normalized)
                before_match_in_seg = display_text[:start_idx]
                match_word = display_text[start_idx:end_idx]
                after_match_in_seg = display_text[end_idx:]
            
            # Contexto de segmentos adyacentes
            s_idx = max(0, i - context_size)
            prev_context = " ".join([corrected_segments[j]['text'] if corrected_segments else segments[j]['text'] for j in range(s_idx, i)])
            
            e_idx = min(len(segments), i + context_size + 1)
            next_context = " ".join([corrected_segments[j]['text'] if corrected_segments else segments[j]['text'] for j in range(i+1, e_idx)])
            
            results.append({
                "start": seg['start'], 
                "formatted": format_timestamp(seg['start']),
                "prev_context": prev_context,
                "before_in_seg": before_match_in_seg,
                "match": match_word if is_exact_match else display_text, 
                "after_in_seg": after_match_in_seg if is_exact_match else "",
                "next_context": next_context,
                "confidence": "high" if is_exact_match else ("medium" if fuzzy_score >= 0.85 else "low"),
                "score": 1.0 if is_exact_match else fuzzy_score
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# --- EXPORTACIÓN ---
def export_with_timestamps(segments):
    return "\n".join([f"[{format_timestamp(s['start'])}] {s['text']}" for s in segments])

def export_srt_format(segments):
    output = []
    for i, seg in enumerate(segments, 1):
        start = format_srt_timestamp(seg['start'])
        end = format_srt_timestamp(seg['end'])
        output.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(output)

def format_srt_timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

# --- APLICACIÓN PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    with st.sidebar:
        st.title("⚙️ Configuración")
        model_choice = st.selectbox("Modelo", ["whisper-large-v3", "whisper-large-v3-turbo"])
        enable_correction = st.checkbox("Corregir ortografía", value=True)
        st.divider()
        st.session_state.context_sentences = st.slider("Contexto (oraciones)", 1, 10, 3)
        enable_fuzzy = st.checkbox("Búsqueda inteligente", value=True)
        fuzzy_threshold = st.slider("Sensibilidad", 0.5, 1.0, 0.7) if enable_fuzzy else 1.0
        
        if st.session_state.transcript_text:
            st.divider()
            st.markdown(f"""<div class='stats-card'><h3>{len(st.session_state.transcript_text.split()):,}</h3>Palabras</div>""", unsafe_allow_html=True)
            st.metric("Segmentos", len(st.session_state.transcript_segments))
            if st.button("🚪 Cerrar Sesión"):
                st.session_state.clear()
                st.rerun()

    st.title("🎙️ Transcriptor Pro")
    uploaded_file = st.file_uploader("Subir audio o video", type=["mp3", "mp4", "wav", "m4a", "mov"])

    if uploaded_file:
        is_valid, msg = validate_audio_file(uploaded_file)
        if not is_valid: st.error(msg)
        elif st.button("🚀 Iniciar Transcripción", type="primary"):
            path = save_audio_file(uploaded_file)
            if path:
                raw, segs = transcribe_audio_precision(client, path, model_choice)
                if raw:
                    st.session_state.audio_path = path
                    st.session_state.raw_transcript = raw
                    st.session_state.transcript_segments = segs
                    if enable_correction:
                        txt, c_segs = correct_orthography_only(client, raw, segs)
                        st.session_state.transcript_text = txt
                        st.session_state.corrected_segments = c_segs
                        st.session_state.correction_applied = True
                    else:
                        st.session_state.transcript_text = raw
                        st.session_state.corrected_segments = segs
                    st.rerun()

    if st.session_state.transcript_text:
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)
        
        tab_search, tab_compare, tab_chat, tab_export = st.tabs(["🔍 Búsqueda & Texto", "🔄 Comparar", "💬 Chat IA", "📥 Exportar"])

        with tab_search:
            # Buscador UI
            with st.form("search_form"):
                c1, c2 = st.columns([5, 1])
                q = c1.text_input("Buscar en la transcripción...", value=st.session_state.last_search_query)
                if c2.form_submit_button("🔎"):
                    st.session_state.last_search_query = q
                    st.session_state.search_results = search_in_segments(q, st.session_state.transcript_segments, st.session_state.corrected_segments, st.session_state.context_sentences, fuzzy_threshold)
            
            if st.session_state.search_results:
                for i, r in enumerate(st.session_state.search_results):
                    with st.container():
                        col_btn, col_text = st.columns([1, 8])
                        if col_btn.button(f"▶️ {r['formatted']}", key=f"p_{i}"):
                            st.session_state.audio_start_time = int(r['start'])
                            st.rerun()
                        
                        confidence_class = f"confidence-{r['confidence']}"
                        col_text.markdown(f"""
                        <div class='search-result'>
                            <span class='confidence-badge {confidence_class}'>{r['confidence'].upper()}</span><br>
                            <span class='context-text'>...{r['prev_context']} </span>
                            <span class='segment-text'>{r['before_in_seg']}</span>
                            <span class='highlight'>{r['match']}</span>
                            <span class='segment-text'>{r['after_in_seg']}</span>
                            <span class='context-text'> {r['next_context']}...</span>
                        </div>
                        """, unsafe_allow_html=True)
                if st.button("Limpiar Búsqueda"):
                    st.session_state.search_results = None
                    st.session_state.last_search_query = ""
                    st.rerun()
            
            st.divider()
            st.text_area("Texto Completo", st.session_state.transcript_text, height=400)

        with tab_compare:
            if st.session_state.correction_applied:
                c1, c2 = st.columns(2)
                c1.markdown("#### Original")
                c1.text_area("Original", st.session_state.raw_transcript, height=400, label_visibility="collapsed")
                c2.markdown("#### Corregida")
                c2.text_area("Corregida", st.session_state.transcript_text, height=400, label_visibility="collapsed")
            else: st.info("Activa la corrección para comparar.")

        with tab_chat:
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if p := st.chat_input("Pregunta sobre el contenido..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.markdown(p)
                with st.chat_message("assistant"):
                    h = st.empty()
                    f = ""
                    stream = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": f"Responde basándote en esta transcripción: {st.session_state.transcript_text[:15000]}"}, {"role": "user", "content": p}],
                        stream=True
                    )
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            f += chunk.choices[0].delta.content
                            h.markdown(f + "▌")
                    h.markdown(f)
                    st.session_state.chat_history.append({"role": "assistant", "content": f})

        with tab_export:
            st.download_button("Descargar TXT", st.session_state.transcript_text, "transcripcion.txt")
            st.download_button("Descargar SRT", export_srt_format(st.session_state.corrected_segments), "subtitulos.srt")
            st.download_button("Descargar con Timestamps", export_with_timestamps(st.session_state.corrected_segments), "tiempos.txt")
            
            json_out = {"metadata": {"model": model_choice}, "transcript": st.session_state.transcript_text, "segments": st.session_state.corrected_segments}
            st.download_button("Descargar JSON", json.dumps(json_out, indent=2), "data.json")

if __name__ == "__main__":
    if check_password(): main_app()
