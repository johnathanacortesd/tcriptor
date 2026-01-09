import streamlit as st
import os
import tempfile
import unicodedata
from groq import Groq
from difflib import SequenceMatcher
import hashlib
import json
import re

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
        padding: 2px 4px; 
        border-radius: 3px; 
        color: #000;
        box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    .context-text {
        color: #666;
        font-size: 0.95em;
        line-height: 1.6;
    }
    .match-text {
        color: #000;
        font-weight: 600;
        line-height: 1.8;
        font-size: 1.05em;
        background-color: rgba(255, 255, 255, 0.5);
        padding: 2px 0;
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
if "context_sentences" not in st.session_state: st.session_state.context_sentences = 2
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

def highlight_text(text, query):
    """Resalta la consulta dentro del texto usando Regex (Case insensitive)"""
    if not query or not text: return text
    
    query_escaped = re.escape(query)
    # 1. Intentar frase completa
    pattern = re.compile(f"({query_escaped})", re.IGNORECASE)
    if pattern.search(text):
        return pattern.sub(r"<span class='highlight'>\1</span>", text)
    
    # 2. Intentar palabras individuales
    words = query.split()
    highlighted_text = text
    for word in words:
        if len(word) > 2: 
            word_escaped = re.escape(word)
            pattern_word = re.compile(f"({word_escaped})", re.IGNORECASE)
            highlighted_text = pattern_word.sub(r"<span class='highlight'>\1</span>", highlighted_text)
            
    return highlighted_text

# --- SEGURIDAD (CORREGIDO) ---
def check_password():
    if st.session_state.authenticated: 
        return True
    
    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password_input = st.text_input(
            "Contraseña", 
            type="password", 
            key="password_field",
            on_change=validate_password
        )
        
        if st.button("Ingresar", use_container_width=True, type="primary"):
            validate_password()
            
    return False

def validate_password():
    """Función separada para validar contraseña"""
    password_input = st.session_state.get("password_field", "")
    
    if not password_input:
        return
        
    try:
        if password_input == st.secrets["general"]["app_password"]:
            st.session_state.authenticated = True
            st.success("✅ Acceso concedido")
            st.rerun()
        else: 
            st.error("⛔ Contraseña incorrecta")
            st.session_state.password_attempts += 1
    except Exception as e:
        st.error("❌ Error de configuración en secrets.toml")

def get_groq_client():
    try: 
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: 
        st.error("❌ Error: No API Key found")
        return None

# --- AUDIO & TRANSCRIPCIÓN ---
def validate_audio_file(uploaded_file):
    MAX_SIZE_MB = 25
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size_mb > MAX_SIZE_MB:
        return False, f"Archivo ({file_size_mb:.1f}MB) excede 25MB"
    return True, f"Válido: {file_size_mb:.1f}MB"

def save_audio_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        filename_normalized = unicodedata.normalize('NFKD', uploaded_file.name).encode('ascii', 'ignore').decode('ascii')
        safe_name = "".join([c for c in filename_normalized if c.isalnum() or c in ('.', '_', '-')]).strip() or "audio_temp.mp3"
        file_path = os.path.join(temp_dir, f"original_{safe_name}")
        with open(file_path, "wb") as f: 
            f.write(uploaded_file.getbuffer())
        return file_path
    except: 
        return None

def transcribe_audio_precision(client, file_path, model_name):
    try:
        if os.path.getsize(file_path) > 25 * 1024 * 1024: 
            return None, None
        with st.spinner(f"🎧 Transcribiendo con {model_name}..."):
            with open(file_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(file_path), file.read()),
                    model=model_name,
                    response_format="verbose_json",
                    language="es",
                    temperature=0.0
                )
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"Error Groq: {e}")
        return None, None

# --- CORRECCIÓN & ALINEACIÓN (CRÍTICO PARA BÚSQUEDA) ---
def realign_text_to_segments(corrected_text, original_segments):
    """
    Toma el texto corregido completo y lo redistribuye en los segmentos originales
    basándose en el conteo de palabras para mantener la sincronización de audio.
    Esto asegura que la búsqueda muestre el texto corregido (con tildes) en el segmento correcto.
    """
    corrected_words = corrected_text.split()
    aligned_segments = []
    current_word_idx = 0
    total_words = len(corrected_words)
    
    for i, seg in enumerate(original_segments):
        # Contar palabras en el segmento original
        original_word_count = len(seg['text'].split())
        
        # Calcular cuántas palabras tomar del texto corregido
        # (Si es el último segmento, tomar todo lo que sobra)
        if i == len(original_segments) - 1:
            end_idx = total_words
        else:
            end_idx = min(current_word_idx + original_word_count, total_words)
        
        # Extraer palabras corregidas
        segment_words = corrected_words[current_word_idx:end_idx]
        new_text = " ".join(segment_words)
        
        # Actualizar índice
        current_word_idx = end_idx
        
        # Crear nuevo segmento con timestamps originales pero texto corregido
        aligned_segments.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': new_text
        })
        
    return aligned_segments

def correct_orthography_only(client, raw_text, segments, max_chunk_size=6000):
    if len(raw_text) > max_chunk_size:
        chunks, current_chunk = [], ""
        for line in raw_text.split(". "):
            if len(current_chunk) + len(line) < max_chunk_size:
                current_chunk += line + ". "
            else:
                chunks.append(current_chunk)
                current_chunk = line + ". "
        if current_chunk: 
            chunks.append(current_chunk)
        
        corrected_chunks = []
        progress = st.progress(0)
        for i, chunk in enumerate(chunks):
            corrected_chunks.append(_correct_single_chunk(client, chunk))
            progress.progress((i+1)/len(chunks))
        progress.empty()
        corrected_text = " ".join(corrected_chunks)
    else:
        corrected_text = _correct_single_chunk(client, raw_text)
    
    # AQUÍ ESTÁ LA MEJORA CLAVE:
    # Alinear el texto corregido con los segmentos para la búsqueda
    corrected_segments = realign_text_to_segments(corrected_text, segments)
    
    return corrected_text, corrected_segments

def _correct_single_chunk(client, text_chunk):
    system_prompt = "Eres un corrector ortográfico ULTRA CONSERVADOR. MANTÉN TODAS LAS PALABRAS. Solo corrige tildes, mayúsculas y puntuación. NUNCA cambies, quites ni agregues palabras. Devuelve solo el texto."
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": text_chunk}
            ],
            temperature=0.0
        )
        out = res.choices[0].message.content.strip()
        if out.startswith(("Aquí", "Texto", "Corrección")): 
            return out.split(":", 1)[1].strip()
        return out
    except: 
        return text_chunk

# --- BÚSQUEDA MEJORADA CON MÁS CONTEXTO ---
def get_complete_context(segments, match_index, context_size):
    """
    Obtiene contexto completo extendiendo hasta límites naturales de frases.
    Mejora: no corta frases a la mitad, busca puntos finales completos.
    """
    start_idx = max(0, match_index - context_size)
    end_idx = min(len(segments), match_index + context_size + 1)
    
    # Extender hacia atrás hasta encontrar inicio de frase (mayúscula después de punto)
    while start_idx > 0:
        prev_text = segments[start_idx - 1]['text'].strip()
        # Si termina en punto/signo de puntuación fuerte, detener
        if prev_text and prev_text[-1] in '.!?':
            break
        # Si ya llevamos 10 segmentos hacia atrás, detener
        if match_index - start_idx >= context_size + 5:
            break
        start_idx -= 1
    
    # Extender hacia adelante hasta encontrar fin de frase
    while end_idx < len(segments):
        curr_text = segments[end_idx - 1]['text'].strip()
        # Si termina en punto/signo de puntuación fuerte, detener
        if curr_text and curr_text[-1] in '.!?':
            break
        # Si ya llevamos 10 segmentos hacia adelante, detener
        if end_idx - match_index >= context_size + 5:
            break
        end_idx += 1
    
    return start_idx, end_idx

def search_in_segments(query, segments, corrected_segments, context_size=2, fuzzy_threshold=0.7):
    """
    Búsqueda priorizando los segmentos corregidos para visualización.
    MEJORADO: Contexto extendido hasta completar frases.
    """
    results = []
    if not query: 
        return results
    
    # Usar corrected_segments si existen, sino segments originales
    target_segments = corrected_segments if corrected_segments else segments
    
    for i, seg in enumerate(target_segments):
        text_display = seg['text']
        text_norm = normalize_text(text_display)
        query_norm = normalize_text(query)
        
        # Lógica de coincidencia
        is_exact = query_norm in text_norm
        score = fuzzy_search_score(query_norm, text_norm)
        is_fuzzy = score >= fuzzy_threshold
        
        if is_exact or is_fuzzy:
            # MEJORA: Obtener contexto completo sin cortar frases
            start_idx, end_idx = get_complete_context(target_segments, i, context_size)
            
            # Construir contexto con el texto corregido
            prev_txt = " ".join([s['text'] for s in target_segments[start_idx:i]])
            match_txt = highlight_text(text_display, query)
            next_txt = " ".join([s['text'] for s in target_segments[i+1:end_idx]])
            
            results.append({
                "start": seg['start'],
                "formatted": format_timestamp(seg['start']),
                "prev": prev_txt,
                "match": match_txt,
                "next": next_txt,
                "confidence": "high" if is_exact else ("medium" if score > 0.85 else "low"),
                "score": 1.0 if is_exact else score
            })
            
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: 
        st.stop()

    with st.sidebar:
        st.title("⚙️ Configuración")
        model = st.selectbox("Modelo", ["whisper-large-v3", "whisper-large-v3-turbo"])
        enable_corr = st.checkbox("Corrección Ortográfica", value=True)
        st.divider()
        st.markdown("#### 🔍 Búsqueda")
        context_n = st.slider("Contexto (segmentos)", 1, 8, 3, help="Cuántos segmentos antes/después del resultado mostrar. El sistema extenderá automáticamente hasta completar frases.")
        fuzzy = st.checkbox("Búsqueda Fuzzy", value=True)
        thresh = st.slider("Sensibilidad", 0.5, 1.0, 0.75) if fuzzy else 1.0
        st.divider()
        if st.button("🚪 Salir"): 
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ Transcriptor Pro")
    
    uploaded = st.file_uploader("Subir Audio", type=["mp3", "wav", "m4a", "ogg", "mp4"])
    
    if uploaded and st.button("🚀 Transcribir", type="primary", use_container_width=True):
        st.session_state.search_results = None
        with st.status("Procesando...", expanded=True) as status:
            path = save_audio_file(uploaded)
            st.session_state.audio_path = path
            if path:
                raw, segs = transcribe_audio_precision(client, path, model)
                if raw:
                    st.session_state.raw_transcript = raw
                    st.session_state.transcript_segments = segs
                    
                    if enable_corr:
                        st.write("✨ Mejorando texto y realineando segmentos...")
                        # Aquí ocurre la magia de la alineación
                        corr_txt, corr_segs = correct_orthography_only(client, raw, segs)
                        st.session_state.transcript_text = corr_txt
                        st.session_state.corrected_segments = corr_segs # Guardamos segmentos corregidos
                        st.session_state.correction_applied = True
                    else:
                        st.session_state.transcript_text = raw
                        st.session_state.corrected_segments = segs
                        st.session_state.correction_applied = False
                    
                    st.session_state.audio_start_time = 0
                    status.update(label="✅ Listo", state="complete", expanded=False)
                    st.rerun()

    # REPRODUCTOR (Siempre visible si hay audio)
    if st.session_state.audio_path:
        st.markdown("### 🎵 Reproductor")
        # Fix del clic: aseguramos int y un pequeño buffer
        start_t = int(max(0, st.session_state.audio_start_time))
        st.audio(st.session_state.audio_path, start_time=start_t)

    if st.session_state.transcript_text:
        tab1, tab2, tab3 = st.tabs(["🔍 Búsqueda & Texto", "💬 Chat IA", "📥 Exportar"])
        
        with tab1:
            st.markdown("### 🔍 Búsqueda Inteligente")
            with st.form("search"):
                c1, c2 = st.columns([5,1])
                q = c1.text_input("Buscar", value=st.session_state.last_search_query, placeholder="Ej: presupuesto...")
                if c2.form_submit_button("🔎"):
                    st.session_state.last_search_query = q
                    st.session_state.search_results = search_in_segments(
                        q, st.session_state.transcript_segments, 
                        st.session_state.corrected_segments, # Pasamos los segmentos corregidos
                        context_n, thresh if fuzzy else 1.0
                    )
                    st.rerun()

            if st.session_state.last_search_query and st.session_state.search_results:
                st.success(f"✅ Encontrados {len(st.session_state.search_results)} resultados para '{st.session_state.last_search_query}'")
                for r in st.session_state.search_results:
                    with st.container():
                        b_col, t_col = st.columns([1, 8])
                        if b_col.button(f"▶️ {r['formatted']}", key=f"btn_{r['start']}"):
                            st.session_state.audio_start_time = max(0, r['start'] - 1) # Buffer de 1s
                            st.rerun()
                        
                        t_col.markdown(f"""
                        <div class='search-result'>
                            <span class='confidence-badge confidence-{r['confidence']}'>{r['confidence'].upper()}</span><br>
                            <span class='context-text'>{r['prev']}</span> 
                            <span class='match-text'>{r['match']}</span> 
                            <span class='context-text'>{r['next']}</span>
                        </div>""", unsafe_allow_html=True)
            elif st.session_state.last_search_query:
                st.warning("⚠️ No se encontraron resultados")

            st.divider()
            st.markdown("### 📄 Texto Completo")
            st.text_area("", value=st.session_state.transcript_text, height=400, label_visibility="collapsed")

        with tab2:
            st.markdown("### 💬 Chat con tu Audio")
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
            
            if prompt := st.chat_input("Pregunta algo..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"): 
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    full_res = ""
                    holder = st.empty()
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"Contexto:\n{st.session_state.transcript_text[:20000]}"},
                                {"role": "user", "content": prompt}
                            ], 
                            stream=True
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full_res += chunk.choices[0].delta.content
                                holder.markdown(full_res + "▌")
                        holder.markdown(full_res)
                        st.session_state.chat_history.append({"role": "assistant", "content": full_res})
                    except Exception as e: 
                        st.error(str(e))

        with tab3:
            st.markdown("### 📥 Exportar Transcripción")
            st.download_button(
                label="📄 Descargar Texto (.txt)", 
                data=st.session_state.transcript_text, 
                file_name="transcripcion.txt",
                mime="text/plain",
                use_container_width=True
            )

if __name__ == "__main__":
    if check_password(): 
        main_app()
