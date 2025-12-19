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
    Resalta la consulta dentro del texto de forma inteligente
    Busca coincidencias parciales y completas
    """
    if not query or not text:
        return text
    
    # Normalizar para búsqueda
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Intentar coincidencia exacta de la frase completa
    if query_lower in text_lower:
        # Encontrar posición en texto normalizado
        pos = text_lower.find(query_lower)
        before = text[:pos]
        match = text[pos:pos + len(query)]
        after = text[pos + len(query):]
        return f"{before}<span class='highlight'>{match}</span>{after}"
    
    # Si no hay coincidencia exacta, buscar palabras individuales
    query_words = [w for w in query_lower.split() if len(w) > 2]
    
    if not query_words:
        return text
    
    # Buscar la primera palabra significativa que coincida
    for word in query_words:
        if word in text_lower:
            pos = text_lower.find(word)
            before = text[:pos]
            match = text[pos:pos + len(word)]
            after = text[pos + len(word):]
            return f"{before}<span class='highlight'>{match}</span>{after}"
    
    return text

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
    - Sin conversión de audio
    - Temperatura 0 para máxima determinismo
    - Sin prompt para evitar contaminación
    - Respuesta verbosa con segmentos
    """
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        if size_mb > 25:
            st.error(f"❌ Archivo ({size_mb:.1f}MB) supera el límite de 25MB de Groq.")
            return None, None

        with st.spinner(f"🎧 Transcribiendo con {model_name}..."):
            with open(file_path, "rb") as file:
                # Parámetros optimizados para máxima precisión
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
    Corrección ULTRA CONSERVADORA:
    - Solo corrige ortografía, tildes, puntuación
    - NO modifica ni elimina palabras
    - NO cambia el orden
    - Mantiene muletillas y repeticiones
    - Devuelve tanto el texto completo como los segmentos corregidos
    """
    
    # Para textos muy largos, dividir en chunks
    if len(raw_text) > max_chunk_size:
        st.info(f"📄 Texto largo detectado. Procesando en segmentos para mantener precisión...")
        
        # Dividir por párrafos o puntos
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
    for seg in segments:
        # Mantener la estructura original del segmento
        corrected_segments.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text']  # Inicialmente usar el original
        })
    
    # Intentar mapear las correcciones a los segmentos
    # Este es un enfoque simplificado - en producción podrías usar algo más sofisticado
    corrected_sentences = re.split(r'[.!?]+', corrected_text)
    corrected_sentences = [s.strip() for s in corrected_sentences if s.strip()]
    
    # Mapear segmentos corregidos (uno a uno si es posible)
    for i in range(min(len(corrected_segments), len(corrected_sentences))):
        corrected_segments[i]['text'] = corrected_sentences[i]
    
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

4. Devuelve ÚNICAMENTE el texto corregido sin comentarios

EJEMPLO:
Entrada: "entonces eh nosotros fuimos a ver la pelicula y estuvo muy buena"
Salida: "Entonces eh nosotros fuimos a ver la película y estuvo muy buena"
"""

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
        
        # Limpiar respuestas con prefijos innecesarios
        prefixes_to_remove = [
            "Aquí está el texto corregido:",
            "Texto corregido:",
            "Corrección:",
            "He aquí la corrección:",
            "Aquí tienes:"
        ]
        
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result[len(prefix):].strip()
        
        return result
        
    except Exception as e:
        st.warning(f"⚠️ Error en corrección: {e}. Usando texto original.")
        return text_chunk

# --- BÚSQUEDA MEJORADA ---
def search_in_segments(query, segments, corrected_segments, context_size=2, fuzzy_threshold=0.7):
    """
    Búsqueda MEJORADA con contexto correcto
    - Busca en segmentos originales para mayor cobertura
    - Muestra segmentos corregidos con tildes
    - Construye contexto correctamente alrededor del segmento encontrado
    - Resalta el término encontrado
    """
    results = []
    if not query or not segments: 
        return results
    
    query_normalized = normalize_text(query)
    
    for i, seg in enumerate(segments):
        text_normalized = normalize_text(seg['text'])
        
        # Verificar si hay coincidencia
        is_exact_match = query_normalized in text_normalized
        fuzzy_score = fuzzy_search_score(query_normalized, text_normalized)
        is_fuzzy_match = fuzzy_score >= fuzzy_threshold
        
        if is_exact_match or is_fuzzy_match:
            # Usar segmento corregido si está disponible
            if i < len(corrected_segments):
                current_segment = corrected_segments[i]
            else:
                current_segment = seg
            
            # Construir contexto ANTERIOR (segmentos previos)
            prev_context_parts = []
            for j in range(max(0, i - context_size), i):
                if j < len(corrected_segments):
                    prev_context_parts.append(corrected_segments[j]['text'])
                else:
                    prev_context_parts.append(segments[j]['text'])
            prev_context = " ".join(prev_context_parts)
            
            # Construir contexto POSTERIOR (segmentos siguientes)
            next_context_parts = []
            for j in range(i + 1, min(len(segments), i + context_size + 1)):
                if j < len(corrected_segments):
                    next_context_parts.append(corrected_segments[j]['text'])
                else:
                    next_context_parts.append(segments[j]['text'])
            next_context = " ".join(next_context_parts)
            
            # Resaltar el término en el segmento actual
            match_text_highlighted = highlight_text(current_segment['text'], query)
            
            # Determinar tipo de coincidencia y confianza
            match_type = "exact" if is_exact_match else "fuzzy"
            confidence = "high" if is_exact_match else ("medium" if fuzzy_score >= 0.85 else "low")
            
            results.append({
                "start": seg['start'], 
                "end": seg['end'],
                "formatted": format_timestamp(seg['start']),
                "match": match_text_highlighted,
                "match_plain": current_segment['text'],
                "prev": prev_context, 
                "next": next_context,
                "segment_index": i,
                "match_type": match_type,
                "confidence": confidence,
                "score": fuzzy_score if is_fuzzy_match else 1.0
            })
    
    # Ordenar por puntuación de relevancia
    results.sort(key=lambda x: x['score'], reverse=True)
    return results

# --- EXPORTACIÓN ---
def export_with_timestamps(segments):
    """Exporta transcripción con timestamps"""
    output = []
    for seg in segments:
        timestamp = format_timestamp(seg['start'])
        output.append(f"[{timestamp}] {seg['text']}")
    return "\n".join(output)

def export_srt_format(segments):
    """Exporta en formato SRT (subtítulos)"""
    output = []
    for i, seg in enumerate(segments, 1):
        start_time = format_srt_timestamp(seg['start'])
        end_time = format_srt_timestamp(seg['end'])
        output.append(f"{i}\n{start_time} --> {end_time}\n{seg['text']}\n")
    return "\n".join(output)

def format_srt_timestamp(seconds):
    """Formato timestamp para SRT"""
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
            help="• V3: MÁXIMA precisión (recomendado)\n• Turbo: Más rápido",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("#### ✏️ Corrección Ortográfica")
        enable_correction = st.checkbox(
            "Aplicar corrección de tildes/puntuación", 
            value=True,
            help="Solo corrige ortografía SIN modificar palabras"
        )
        
        if enable_correction:
            st.info("✅ La corrección mantiene TODAS las palabras originales")
        
        st.divider()
        
        st.markdown("#### 🔍 Configuración de Búsqueda")
        st.session_state.context_sentences = st.slider(
            "Segmentos de contexto",
            min_value=1,
            max_value=5,
            value=2,
            help="Cantidad de segmentos antes y después del resultado"
        )
        
        enable_fuzzy = st.checkbox(
            "🎯 Búsqueda inteligente (fuzzy)",
            value=True,
            help="Encuentra coincidencias aproximadas"
        )
        
        if enable_fuzzy:
            fuzzy_threshold = st.slider(
                "Sensibilidad de búsqueda",
                min_value=0.5,
                max_value=1.0,
                value=0.7,
                step=0.05,
                help="0.5 = muy permisivo | 1.0 = solo exactas"
            )
        else:
            fuzzy_threshold = 1.0
        
        st.divider()
        
        if st.session_state.transcript_text:
            st.markdown("#### 📊 Estadísticas")
            words = st.session_state.transcript_text.split()
            word_count = len(words)
            char_count = len(st.session_state.transcript_text)
            segment_count = len(st.session_state.transcript_segments) if st.session_state.transcript_segments else 0
            
            if st.session_state.transcript_segments:
                duration_secs = st.session_state.transcript_segments[-1]['end']
                duration_formatted = format_timestamp(duration_secs)
            else:
                duration_formatted = "N/A"
            
            st.markdown(f"""
            <div class='stats-card'>
                <div style='font-size: 28px; font-weight: bold;'>{word_count:,}</div>
                <div>Palabras</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.metric("Caracteres", f"{char_count:,}")
            st.metric("Segmentos", segment_count)
            st.metric("Duración", duration_formatted)
            
            if st.session_state.correction_applied:
                st.success("✅ Corrección aplicada")
            else:
                st.info("📝 Transcripción original")
        
        st.divider()
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- HEADER PRINCIPAL ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎙️ Transcriptor Pro")
        st.caption("Transcripción de máxima precisión | Búsqueda inteligente | Chat contextual")
    with col2:
        if st.session_state.transcript_text:
            st.success("✅ Listo")

    # --- INFORMACIÓN IMPORTANTE ---
    with st.expander("ℹ️ Información Importante sobre Precisión"):
        st.markdown("""
        ### 🎯 Optimizaciones de Precisión
        
        **Esta versión incluye:**
        - ✅ **Sin conversión de audio**: El archivo se envía tal cual para evitar pérdida de calidad
        - ✅ **Temperatura 0**: Máxima determinismo en la transcripción
        - ✅ **Modelo V3**: Mejor precisión disponible
        - ✅ **Corrección conservadora**: Solo tildes y puntuación, NO modifica palabras
        - ✅ **Búsqueda mejorada**: Muestra contexto correcto y resalta exactamente la palabra encontrada
        
        **Límites de Groq API:**
        - Tamaño máximo: 25MB
        - Si tu archivo es mayor, divídelo en partes más pequeñas
        
        **Recomendaciones:**
        - Usa archivos de audio claros y sin ruido excesivo
        - Prefiere MP3 o WAV de buena calidad
        - Para audios largos (>1 hora), considera dividirlos
        """)

    # --- UPLOAD ---
    uploaded_file = st.file_uploader(
        "📁 Subir archivo de audio o video", 
        type=["mp3", "mp4", "wav", "m4a", "mov", "mkv", "avi", "flv", "ogg", "webm", "aac", "flac"],
        help="Formatos compatibles | Máximo 25MB"
    )

    if uploaded_file:
        # Validar archivo
        is_valid, message = validate_audio_file(uploaded_file)
        
        if not is_valid:
            st.error(f"❌ {message}")
            st.info("💡 Reduce el tamaño del archivo o divídelo en partes más pequeñas")
        else:
            st.success(f"✅ {message}")
            
            if st.button("🚀 Iniciar Transcripción", type="primary", use_container_width=True):
                # LIMPIAR BÚSQUEDA Y ESTADO ANTERIOR
                st.session_state.search_results = None
                st.session_state.last_search_query = ""
                st.session_state.correction_applied = False
                
                with st.status("⚙️ Procesando...", expanded=True) as status:
                    st.write("💾 Guardando archivo original (sin conversión)...")
                    
                    final_path = save_audio_file(uploaded_file)
                    st.session_state.audio_path = final_path
                    
                    if final_path:
                        st.write(f"🎧 Transcribiendo con {model_choice}...")
                        st.info("⏱️ Esto puede tomar varios minutos dependiendo de la duración del audio")
                        
                        raw, segs = transcribe_audio_precision(
                            client, 
                            final_path, 
                            model_choice
                        )
                        
                        if raw and segs:
                            # Guardar transcripción cruda
                            st.session_state.raw_transcript = raw
                            st.session_state.transcript_segments = segs
                            
                            # Aplicar corrección si está habilitada
                            if enable_correction:
                                st.write("✨ Aplicando corrección ortográfica conservadora...")
                                corrected_text, corrected_segs = correct_orthography_only(client, raw, segs)
                                st.session_state.transcript_text = corrected_text
                                st.session_state.corrected_segments = corrected_segs
                                st.session_state.correction_applied = True
                            else:
                                st.session_state.transcript_text = raw
                                st.session_state.corrected_segments = segs
                                st.session_state.correction_applied = False
                            
                            st.session_state.audio_start_time = 0
                            st.session_state.chat_history = []
                            
                            status.update(label="✅ ¡Completado!", state="complete", expanded=False)
                            st.balloons()
                        else: 
                            status.update(label="❌ Error en transcripción", state="error")
                    else: 
                        status.update(label="❌ Error procesando archivo", state="error")

    # --- REPRODUCTOR ---
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.markdown("### 🎵 Reproductor")
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    # --- TABS PRINCIPALES ---
    if st.session_state.transcript_text:
        tab_txt, tab_compare, tab_chat, tab_export = st.tabs([
            "📝 Transcripción & Búsqueda", 
            "🔄 Comparar Versiones",
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
                        "Buscar en transcripción", 
                        value=st.session_state.last_search_query,
                        placeholder="Ej: 'innovación tecnológica', 'resultados financieros'...",
                        label_visibility="collapsed",
                        key="search_input_widget"
                    )
                with col_b:
                    submit_search = st.form_submit_button("🔎", use_container_width=True)

            if submit_search:
                if search_query:
                    st.session_state.last_search_query = search_query
                    # Usar los segmentos corregidos para mostrar resultados con tildes
                    st.session_state.search_results = search_in_segments(
                        search_query, 
                        st.session_state.transcript_segments,
                        st.session_state.corrected_segments,
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
                                confidence_class = f"confidence-{r['confidence']}"
                                confidence_text = {"high": "Exacto", "medium": "Probable", "low": "Similar"}[r['confidence']]
                                
                                st.markdown(
                                    f"""<div class='search-result'>
                                        <span class='confidence-badge {confidence_class}'>{confidence_text}</span>
                                        <br><br>
                                        <span class='context-text'>{r['prev']}</span>
                                        <span class='match-text'> {r['match']} </span>
                                        <span class='context-text'>{r['next']}</span>
                                    </div>""", 
                                    unsafe_allow_html=True
                                )
                    
                    if st.button("🗑️ Limpiar búsqueda", key="clear_search"):
                        st.session_state.search_results = None
                        st.session_state.last_search_query = ""
                        st.rerun()
                else:
                    st.markdown(f"""
                    <div class='no-results'>
                        <strong>⚠️ Sin resultados</strong><br>
                        No se encontró "<em>{st.session_state.last_search_query}</em>"<br>
                        <small>💡 Tip: {'La búsqueda inteligente está activa' if enable_fuzzy else 'Activa búsqueda inteligente en el menú'}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🔄 Nueva búsqueda", key="new_search"):
                        st.session_state.last_search_query = ""
                        st.session_state.search_results = None
                        st.rerun()
            
            st.divider()
            st.markdown("### 📄 Texto Completo")
            
            # Mostrar si hay corrección aplicada
            if st.session_state.correction_applied:
                st.info("✅ Mostrando versión con corrección ortográfica")
            else:
                st.info("📝 Mostrando transcripción original sin corrección")
            
            st.text_area(
                "Transcripción", 
                value=st.session_state.transcript_text, 
                height=400,
                label_visibility="collapsed"
            )

        # TAB 2: COMPARAR VERSIONES
        with tab_compare:
            st.markdown("### 🔄 Comparar Transcripciones")
            st.caption("Compara la transcripción original vs. la versión corregida")
            
            if st.session_state.raw_transcript and st.session_state.correction_applied:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📝 Original (Whisper)")
                    st.text_area(
                        "Original",
                        value=st.session_state.raw_transcript,
                        height=500,
                        label_visibility="collapsed",
                        key="original_text"
                    )
                    
                    words_original = len(st.session_state.raw_transcript.split())
                    st.metric("Palabras", words_original)
                
                with col2:
                    st.markdown("#### ✏️ Corregida (Llama)")
                    st.text_area(
                        "Corregida",
                        value=st.session_state.transcript_text,
                        height=500,
                        label_visibility="collapsed",
                        key="corrected_text"
                    )
                    
                    words_corrected = len(st.session_state.transcript_text.split())
                    st.metric("Palabras", words_corrected)
                
                # Análisis de diferencias
                st.divider()
                st.markdown("#### 📊 Análisis de Cambios")
                
                if words_original == words_corrected:
                    st.success(f"✅ Número de palabras conservado: {words_original}")
                else:
                    diff = words_corrected - words_original
                    if abs(diff) <= 5:
                        st.warning(f"⚠️ Diferencia mínima: {diff:+d} palabras (aceptable)")
                    else:
                        st.error(f"❌ Diferencia significativa: {diff:+d} palabras (revisar)")
                
                # Mostrar algunas diferencias
                from difflib import unified_diff
                
                original_lines = st.session_state.raw_transcript.split('. ')[:10]
                corrected_lines = st.session_state.transcript_text.split('. ')[:10]
                
                with st.expander("🔍 Ver primeras diferencias (primeras 10 oraciones)"):
                    for i, (orig, corr) in enumerate(zip(original_lines, corrected_lines), 1):
                        if orig.strip() != corr.strip():
                            st.markdown(f"**Oración {i}:**")
                            st.markdown(f"- ❌ Original: `{orig}`")
                            st.markdown(f"- ✅ Corregida: `{corr}`")
                            st.divider()
            
            elif not st.session_state.correction_applied:
                st.info("ℹ️ No se aplicó corrección ortográfica. Actívala en la configuración para ver comparaciones.")
            else:
                st.warning("⚠️ No hay transcripción original disponible para comparar.")

        # TAB 3: CHAT IA
        with tab_chat:
            st.markdown("### 💬 Asistente IA")
            st.caption("Haz preguntas inteligentes sobre el contenido transcrito")
            
            # Selector de versión para el chat
            if st.session_state.correction_applied:
                col1, col2 = st.columns([3, 1])
                with col1:
                    chat_version = st.radio(
                        "Usar versión:",
                        options=["Corregida", "Original"],
                        horizontal=True,
                        help="Selecciona qué versión usar para las respuestas del chat"
                    )
                with col2:
                    if st.button("🗑️ Limpiar chat"):
                        st.session_state.chat_history = []
                        st.rerun()
            else:
                chat_version = "Original"
            
            # Mostrar historial
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
            
            # Input de chat
            if p := st.chat_input("💭 Haz una pregunta sobre la transcripción..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): 
                    st.markdown(p)
                
                # Seleccionar contexto según versión elegida
                if chat_version == "Original" and st.session_state.raw_transcript:
                    chat_context = st.session_state.raw_transcript
                else:
                    chat_context = st.session_state.transcript_text

                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"""Eres un asistente experto en análisis de transcripciones de audio.

CONTEXTO DE LA TRANSCRIPCIÓN:
{chat_context[:15000]}

INSTRUCCIONES:
- Responde basándote ÚNICAMENTE en el contenido de la transcripción
- Si la información no está en la transcripción, dilo claramente
- Cita fragmentos específicos cuando sea relevante (usa comillas)
- Sé preciso y conciso
- Usa formato markdown para claridad (negritas, listas, etc.)
- Si detectas términos técnicos o nombres propios, respétalos exactamente

IMPORTANTE: Esta transcripción puede contener muletillas o repeticiones naturales del habla."""},
                                {"role": "user", "content": p}
                            ], 
                            stream=True,
                            temperature=0.3,
                            max_tokens=2000
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: 
                        st.error(f"❌ Error en chat: {e}")

        # TAB 4: EXPORTACIÓN
        with tab_export:
            st.markdown("### 📥 Exportar Transcripción")
            
            # Selector de versión
            if st.session_state.correction_applied:
                export_version = st.radio(
                    "Versión a exportar:",
                    options=["Corregida (recomendado)", "Original"],
                    horizontal=True
                )
                
                if export_version == "Original":
                    text_to_export = st.session_state.raw_transcript
                    st.info("📝 Exportando versión original de Whisper")
                else:
                    text_to_export = st.session_state.transcript_text
                    st.info("✅ Exportando versión con corrección ortográfica")
            else:
                text_to_export = st.session_state.transcript_text
            
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📄 Formato Simple")
                st.download_button(
                    "📝 Texto plano (.txt)", 
                    text_to_export, 
                    "transcripcion.txt",
                    use_container_width=True
                )
                st.download_button(
                    "📘 Markdown (.md)", 
                    text_to_export, 
                    "transcripcion.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                st.markdown("#### ⏱️ Con Timestamps")
                timestamped = export_with_timestamps(st.session_state.transcript_segments)
                st.download_button(
                    "🕐 Texto con marcas (.txt)", 
                    timestamped, 
                    "transcripcion_timestamps.txt",
                    use_container_width=True
                )
                
                srt_content = export_srt_format(st.session_state.transcript_segments)
                st.download_button(
                    "🎬 Subtítulos SRT (.srt)", 
                    srt_content, 
                    "subtitulos.srt",
                    use_container_width=True,
                    help="Compatible con editores de video"
                )
            
            st.divider()
            
            # JSON export con metadata
            st.markdown("#### 🔧 Exportación Avanzada")
            
            json_data = {
                "metadata": {
                    "model": model_choice,
                    "correction_applied": st.session_state.correction_applied,
                    "total_segments": len(st.session_state.transcript_segments),
                    "duration": st.session_state.transcript_segments[-1]['end'] if st.session_state.transcript_segments else 0
                },
                "transcript": text_to_export,
                "segments": st.session_state.transcript_segments
            }
            
            st.download_button(
                "📊 JSON completo (con segmentos)",
                json.dumps(json_data, ensure_ascii=False, indent=2),
                "transcripcion_completa.json",
                mime="application/json",
                use_container_width=True,
                help="Incluye metadata y segmentos con timestamps"
            )
            
            st.divider()
            st.markdown("#### 👁️ Vista Previa con Timestamps")
            preview_text = timestamped[:2000] + "..." if len(timestamped) > 2000 else timestamped
            st.code(preview_text, language="text")

if __name__ == "__main__":
    if check_password(): 
        main_app()
