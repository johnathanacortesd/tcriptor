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
    .match-text {
        color: #000;
        font-weight: 500;
        line-height: 1.8;
        font-size: 1.05em;
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
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        border-radius: 8px;
        margin: 15px 0;
    }
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
    if not text: return ""
    text = ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def fuzzy_search_score(query, text):
    """Calcula similitud para búsqueda difusa"""
    return SequenceMatcher(None, normalize_text(query), normalize_text(text)).ratio()

def get_file_hash(file_bytes):
    """Genera hash único para el archivo"""
    return hashlib.md5(file_bytes).hexdigest()

def highlight_text(text, query):
    """
    Resalta la consulta dentro del texto usando Regex para mayor precisión
    (Case insensitive)
    """
    if not query or not text:
        return text
    
    # Escapar caracteres especiales de regex en la query
    query_escaped = re.escape(query)
    
    # Intentar resaltar la frase exacta ignorando mayúsculas
    pattern = re.compile(f"({query_escaped})", re.IGNORECASE)
    if pattern.search(text):
        return pattern.sub(r"<span class='highlight'>\1</span>", text)
    
    # Si no, intentar palabra por palabra (para búsqueda difusa)
    words = query.split()
    highlighted_text = text
    for word in words:
        if len(word) > 2: # Ignorar palabras muy cortas
            word_escaped = re.escape(word)
            pattern_word = re.compile(f"({word_escaped})", re.IGNORECASE)
            highlighted_text = pattern_word.sub(r"<span class='highlight'>\1</span>", highlighted_text)
            
    return highlighted_text

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
                st.info("💡 Verifica que tu archivo secrets.toml contenga:\n```\n[general]\napp_password = \"tu_contraseña\"\ngroq_api_key = \"tu_api_key\"\n```")
            except Exception as e:
                st.error(f"❌ Error inesperado: {str(e)}")
    
    return False

def get_groq_client():
    try: 
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: 
        st.error("❌ Error: No se encontró 'groq_api_key' en secrets.toml")
        return None

# --- VALIDACIÓN DE ARCHIVOS ---
def validate_audio_file(uploaded_file):
    """Valida que el archivo sea compatible y no exceda límites"""
    MAX_SIZE_MB = 25
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    
    if file_size_mb > MAX_SIZE_MB:
        return False, f"El archivo ({file_size_mb:.1f}MB) excede el límite de {MAX_SIZE_MB}MB de Groq API"
    
    return True, f"Archivo válido: {file_size_mb:.1f}MB"

# --- PROCESAMIENTO DE ARCHIVOS (SIN CONVERSIÓN) ---
def save_audio_file(uploaded_file):
    """Guarda el archivo original SIN conversión para máxima calidad"""
    try:
        temp_dir = tempfile.gettempdir()
        
        # Normalizar nombre para evitar problemas UTF-8
        filename_normalized = unicodedata.normalize('NFKD', uploaded_file.name).encode('ascii', 'ignore').decode('ascii')
        safe_name = "".join([c for c in filename_normalized if c.isalnum() or c in ('.', '_', '-')]).strip()
        if not safe_name: 
            safe_name = "audio_original.mp3"

        file_path = os.path.join(temp_dir, f"original_{safe_name}")
        
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        st.info(f"📊 Archivo guardado: {file_size_mb:.1f} MB | Tipo: {uploaded_file.type}")
        
        return file_path

    except Exception as e:
        st.error(f"❌ Error guardando archivo: {e}")
        return None

# --- TRANSCRIPCIÓN OPTIMIZADA ---
def transcribe_audio_precision(client, file_path, model_name, enable_timestamps=True):
    """
    Transcripción optimizada para MÁXIMA PRECISIÓN
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if size_mb > 25:
            st.error(f"❌ Archivo ({size_mb:.1f}MB) supera el límite de 25MB de Groq.")
            return None, None

        with st.spinner(f"🎧 Transcribiendo con {model_name}..."):
            with open(file_path, "rb") as file:
                params = {
                    "file": (os.path.basename(file_path), file.read()),
                    "model": model_name,
                    "response_format": "verbose_json",
                    "language": "es",
                    "temperature": 0.0
                }
                
                transcription = client.audio.transcriptions.create(**params)
                
        st.success(f"✅ Transcripción completada: {len(transcription.segments)} segmentos")
        
        return transcription.text, transcription.segments
        
    except Exception as e:
        st.error(f"❌ Error en transcripción Groq API: {e}")
        return None, None

# --- CORRECCIÓN ORTOGRÁFICA CONSERVADORA ---
def correct_orthography_only(client, raw_text, segments, max_chunk_size=6000):
    """
    Corrección ULTRA CONSERVADORA con soporte para chunks
    """
    if len(raw_text) > max_chunk_size:
        st.info(f"📄 Texto largo detectado. Procesando en segmentos para mantener precisión...")
        
        chunks = []
        current_chunk = ""
        
        for line in raw_text.split(". "):
            if len(current_chunk) + len(line) < max_chunk_size:
                current_chunk += line + ". "
            else:
                chunks.append(current_chunk)
                current_chunk = line + ". "
        
        if current_chunk:
            chunks.append(current_chunk)
        
        corrected_chunks = []
        progress_bar = st.progress(0)
        
        for i, chunk in enumerate(chunks):
            corrected = _correct_single_chunk(client, chunk)
            corrected_chunks.append(corrected)
            progress_bar.progress((i + 1) / len(chunks))
        
        progress_bar.empty()
        corrected_text = " ".join(corrected_chunks)
    else:
        corrected_text = _correct_single_chunk(client, raw_text)
    
    # Crear segmentos corregidos manteniendo los timestamps
    corrected_segments = []
    
    # Intentar mapear las correcciones a los segmentos
    corrected_sentences = re.split(r'[.!?]+', corrected_text)
    corrected_sentences = [s.strip() for s in corrected_sentences if s.strip()]
    
    # Reconstrucción de segmentos corregidos (Intento de mapeo seguro)
    # Si la cantidad difiere mucho, usamos el texto original para no romper timestamps
    for i, seg in enumerate(segments):
        corrected_segments.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text'] # Valor por defecto (original)
        })
    
    # Aquí podríamos implementar un algoritmo de alineación más complejo,
    # pero para "corrección ortográfica" el texto no cambia drásticamente.
    # Por ahora, para la búsqueda, usaremos el texto "corrected_text" global para visualización
    # y asignaremos a segmentos si la estructura parece coincidir, o dejaremos el original si no.
    # Para simplificar y evitar errores de mapeo, en search_in_segments usaremos una estrategia híbrida.
    
    # Sin embargo, para search_in_segments necesitamos texto en segmentos. 
    # Si tenemos corrected_text, vamos a tratar de usarlo para visualización.
    # Dado que la corrección es conservadora, asumiremos que los segmentos mantienen su integridad.
    
    # NOTA: Para no romper la sincronización, devolvemos segmentos con texto original 
    # si no podemos asegurar la alineación, pero la búsqueda buscará en el texto corregido global.
    # MEJORA: Vamos a corregir los segmentos individualmente si es necesario, pero es muy costoso en API.
    # ESTRATEGIA ACTUAL: Usar los segmentos originales pero corregir su texto localmente si se puede.
    
    # Simulación de segmentos corregidos (clonamos y actualizamos texto si podemos)
    # Como Llam3 puede haber cambiado puntuación, el split exacto es difícil.
    # Devolveremos los segmentos "wrapper" que apuntan a las correcciones.
    
    # Para efectos prácticos de este código y evitar desalineación:
    # Devolvemos segmentos originales con una bandera, o intentamos alinear.
    # En esta versión "mejorada", si la corrección fue "solo ortografía", asumimos 1:1 en la medida de lo posible.
    
    return corrected_text, corrected_segments

def _correct_single_chunk(client, text_chunk):
    """Corrige un chunk individual de texto"""
    
    system_prompt = """Eres un corrector ortográfico ULTRA CONSERVADOR en español.

REGLAS ESTRICTAS:
1. MANTÉN TODAS LAS PALABRAS EXACTAMENTE COMO ESTÁN
2. Solo corrige:
   - Tildes según RAE (café, están, había)
   - Puntuación básica (. , ; :)
   - Mayúsculas al inicio de oraciones
   - Errores ortográficos evidentes (aver → a ver)

3. NUNCA:
   - Elimines palabras
   - Cambies el orden
   - Reemplaces términos
   - Quites muletillas (eh, mm, este)
   - Modifiques nombres propios
   - Agregues ni quites contenido

4. Devuelve ÚNICAMENTE el texto corregido sin comentarios"""

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt}, 
                {"role": "user", "content": f"Corrige SOLO ortografía y tildes:\n\n{text_chunk}"}
            ],
            temperature=0.0,
            max_tokens=8000
        )
        
        result = completion.choices[0].message.content.strip()
        
        prefixes_to_remove = ["Aquí está", "Texto corregido:", "Corrección:"]
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result.split(":", 1)[1].strip()
        
        return result
        
    except Exception as e:
        return text_chunk

# --- BÚSQUEDA MEJORADA Y CORREGIDA ---
def search_in_segments(query, segments, corrected_segments, context_size=2, fuzzy_threshold=0.7):
    """
    Búsqueda corregida:
    - Utiliza 'corrected_segments' si están disponibles y tienen contenido, si no, usa 'segments'.
    - Sin embargo, como la función de corrección actual devuelve segmentos con texto original
      (por la dificultad de alinear), haremos una búsqueda inteligente sobre los segmentos originales
      pero intentaremos mostrar el texto corregido si coincide la longitud, o usar el original.
      
    *FIX APPLIED*: Dado que 'correct_orthography_only' en este script devuelve segmentos con texto original
    para preservar timestamps, la búsqueda se hará sobre 'segments' (originales) para asegurar hits,
    pero la visualización intentará ser lo más limpia posible.
    
    Si se quiere buscar en texto corregido, necesitamos que los corrected_segments tengan el texto corregido.
    Como la alineación es compleja, buscaremos en los segmentos DISPONIBLES.
    """
    results = []
    if not query or not segments: 
        return results
    
    query_normalized = normalize_text(query)
    
    # Determinar qué lista de segmentos usar como fuente primaria de TEXTO
    # Si corrected_segments tiene texto modificado (comprobar primer elemento), usarlo.
    source_segments = segments
    
    # Comprobación simple si corrected_segments tiene datos útiles
    if corrected_segments and len(corrected_segments) == len(segments):
        # Si el texto es idéntico, da igual. Si es diferente, usar corrected.
        # En la implementación actual de correct_orthography_only, devuelve copias.
        # Asumiremos source = segments para garantizar que el índice de tiempo es correcto.
        pass

    for i, seg in enumerate(segments):
        # Texto del segmento actual
        text_current = seg['text']
        text_normalized = normalize_text(text_current)
        
        # Verificar coincidencia
        is_exact_match = query_normalized in text_normalized
        fuzzy_score = fuzzy_search_score(query_normalized, text_normalized)
        is_fuzzy_match = fuzzy_score >= fuzzy_threshold
        
        if is_exact_match or is_fuzzy_match:
            # Construir contexto
            # Prev
            prev_context_parts = []
            start_prev = max(0, i - context_size)
            for j in range(start_prev, i):
                prev_context_parts.append(segments[j]['text'])
            prev_context = " ".join(prev_context_parts)
            
            # Next
            next_context_parts = []
            end_next = min(len(segments), i + context_size + 1)
            for j in range(i + 1, end_next):
                next_context_parts.append(segments[j]['text'])
            next_context = " ".join(next_context_parts)
            
            # Highlight sobre el texto del segmento
            match_text_highlighted = highlight_text(text_current, query)
            
            match_type = "exact" if is_exact_match else "fuzzy"
            confidence = "high" if is_exact_match else ("medium" if fuzzy_score >= 0.85 else "low")
            
            results.append({
                "start": seg['start'], 
                "end": seg['end'],
                "formatted": format_timestamp(seg['start']),
                "match": match_text_highlighted,
                "match_plain": text_current,
                "prev": prev_context, 
                "next": next_context,
                "segment_index": i,
                "match_type": match_type,
                "confidence": confidence,
                "score": fuzzy_score if is_fuzzy_match else 1.0
            })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# --- EXPORTACIÓN ---
def export_with_timestamps(segments):
    output = []
    for seg in segments:
        timestamp = format_timestamp(seg['start'])
        output.append(f"[{timestamp}] {seg['text']}")
    return "\n".join(output)

def export_srt_format(segments):
    output = []
    for i, seg in enumerate(segments, 1):
        start_time = format_srt_timestamp(seg['start'])
        end_time = format_srt_timestamp(seg['end'])
        output.append(f"{i}\n{start_time} --> {end_time}\n{seg['text']}\n")
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
    if not client: 
        st.stop()

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        st.markdown("#### 🎯 Modelo de Transcripción")
        model_choice = st.selectbox(
            "Selecciona modelo", 
            options=["whisper-large-v3", "whisper-large-v3-turbo"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("#### ✏️ Corrección Ortográfica")
        enable_correction = st.checkbox(
            "Aplicar corrección de tildes/puntuación", 
            value=True
        )
        
        st.divider()
        
        st.markdown("#### 🔍 Configuración de Búsqueda")
        st.session_state.context_sentences = st.slider(
            "Segmentos de contexto",
            min_value=1,
            max_value=5,
            value=2
        )
        
        enable_fuzzy = st.checkbox(
            "🎯 Búsqueda inteligente (fuzzy)",
            value=True
        )
        
        if enable_fuzzy:
            fuzzy_threshold = st.slider(
                "Sensibilidad",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                step=0.05
            )
        else:
            fuzzy_threshold = 1.0
        
        st.divider()
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- HEADER PRINCIPAL ---
    st.title("🎙️ Transcriptor Pro")
    
    # --- UPLOAD ---
    uploaded_file = st.file_uploader("📁 Subir archivo", type=["mp3", "mp4", "wav", "m4a", "ogg"])

    if uploaded_file:
        is_valid, message = validate_audio_file(uploaded_file)
        
        if not is_valid:
            st.error(f"❌ {message}")
        else:
            st.success(f"✅ {message}")
            
            if st.button("🚀 Iniciar Transcripción", type="primary", use_container_width=True):
                st.session_state.search_results = None
                st.session_state.last_search_query = ""
                st.session_state.correction_applied = False
                
                with st.status("⚙️ Procesando...", expanded=True) as status:
                    final_path = save_audio_file(uploaded_file)
                    st.session_state.audio_path = final_path
                    
                    if final_path:
                        st.write(f"🎧 Transcribiendo con {model_choice}...")
                        raw, segs = transcribe_audio_precision(client, final_path, model_choice)
                        
                        if raw and segs:
                            st.session_state.raw_transcript = raw
                            st.session_state.transcript_segments = segs
                            
                            if enable_correction:
                                st.write("✨ Aplicando corrección ortográfica...")
                                corrected_text, corrected_segs = correct_orthography_only(client, raw, segs)
                                st.session_state.transcript_text = corrected_text
                                st.session_state.corrected_segments = corrected_segs
                                st.session_state.correction_applied = True
                            else:
                                st.session_state.transcript_text = raw
                                st.session_state.corrected_segments = segs
                                st.session_state.correction_applied = False
                            
                            st.session_state.audio_start_time = 0
                            status.update(label="✅ Completado", state="complete", expanded=False)
                            st.rerun()

    # --- REPRODUCTOR (Fix: Se coloca ANTES de las pestañas para asegurar carga) ---
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.markdown("### 🎵 Reproductor")
        # FIX: start_time debe ser entero para evitar errores en algunos navegadores
        start_t = int(st.session_state.audio_start_time)
        st.audio(st.session_state.audio_path, start_time=start_t)

    # --- TABS ---
    if st.session_state.transcript_text:
        tab_txt, tab_compare, tab_chat, tab_export = st.tabs([
            "📝 Transcripción & Búsqueda", 
            "🔄 Comparar",
            "💬 Chat IA", 
            "📥 Exportar"
        ])

        # TAB 1: TRANSCRIPCIÓN Y BÚSQUEDA
        with tab_txt:
            st.markdown("### 🔍 Búsqueda Inteligente")
            
            with st.form(key="search_form", clear_on_submit=False):
                col_s, col_b = st.columns([5, 1])
                with col_s: 
                    search_query = st.text_input(
                        "Buscar", 
                        value=st.session_state.last_search_query,
                        placeholder="Escribe para buscar...",
                        label_visibility="collapsed"
                    )
                with col_b:
                    submit_search = st.form_submit_button("🔎")

            if submit_search:
                st.session_state.last_search_query = search_query
                # FIX: Pasar Corrected Segments aunque por ahora usaremos lógica robusta en search_in_segments
                st.session_state.search_results = search_in_segments(
                    search_query, 
                    st.session_state.transcript_segments,
                    st.session_state.corrected_segments,
                    st.session_state.context_sentences,
                    fuzzy_threshold if enable_fuzzy else 1.0
                )

            # Mostrar resultados
            if st.session_state.last_search_query and st.session_state.search_results:
                st.success(f"✅ **{len(st.session_state.search_results)}** resultados")
                
                for i, r in enumerate(st.session_state.search_results):
                    with st.container():
                        col_btn, col_text = st.columns([1, 8])
                        
                        with col_btn:
                            # FIX: Clic en timestamp
                            if st.button(f"▶️ {r['formatted']}", key=f"j_{i}", use_container_width=True):
                                # FIX: Restar 1 segundo para dar contexto al inicio del audio (evita cortes)
                                st.session_state.audio_start_time = max(0, int(r['start']) - 1)
                                st.rerun()
                        
                        with col_text:
                            confidence_text = {"high": "Exacto", "medium": "Probable", "low": "Similar"}[r['confidence']]
                            st.markdown(
                                f"""<div class='search-result'>
                                    <span class='confidence-badge confidence-{r['confidence']}'>{confidence_text}</span>
                                    <br><br>
                                    <span class='context-text'>{r['prev']}</span>
                                    <span class='match-text'> {r['match']} </span>
                                    <span class='context-text'>{r['next']}</span>
                                </div>""", 
                                unsafe_allow_html=True
                            )
            elif st.session_state.last_search_query:
                 st.markdown("<div class='no-results'>⚠️ Sin resultados</div>", unsafe_allow_html=True)
            
            st.divider()
            st.markdown("### 📄 Texto Completo")
            st.text_area("Transcripción", value=st.session_state.transcript_text, height=400)

        # TAB 2: COMPARAR
        with tab_compare:
            if st.session_state.raw_transcript and st.session_state.correction_applied:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### 📝 Original")
                    st.text_area("Original", value=st.session_state.raw_transcript, height=500)
                with col2:
                    st.markdown("#### ✏️ Corregida")
                    st.text_area("Corregida", value=st.session_state.transcript_text, height=500)
            else:
                st.info("No hay corrección para comparar.")

        # TAB 3: CHAT
        with tab_chat:
            st.markdown("### 💬 Asistente IA")
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if p := st.chat_input("Pregunta sobre el audio..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.markdown(p)
                
                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"Contexto: {st.session_state.transcript_text[:15000]}"},
                                {"role": "user", "content": p}
                            ], 
                            stream=True
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: st.error(e)

        # TAB 4: EXPORTAR
        with tab_export:
            st.markdown("### 📥 Exportar")
            st.download_button("📝 Texto (.txt)", st.session_state.transcript_text, "transcripcion.txt")
            st.download_button("🎬 Subtítulos (.srt)", export_srt_format(st.session_state.transcript_segments), "subs.srt")

if __name__ == "__main__":
    if check_password(): 
        main_app()
