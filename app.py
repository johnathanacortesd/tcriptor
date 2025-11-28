import streamlit as st
import os
import tempfile
import unicodedata
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
    /* --- ESTILO MODIFICADO: FONDO NEGRO LETRA BLANCA --- */
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
    """
    Normaliza texto eliminando tildes y diacríticos para búsqueda robusta.
    Ejemplo: 'Popayán' -> 'popayan'
    """
    if not isinstance(text, str):
        return ""
    # Descomponer caracteres unicode y eliminar marcas (tildes, diéresis)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text.lower().strip()

def fuzzy_search_score(query, text):
    """Calcula similitud basándose en texto normalizado"""
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

# --- PROCESAMIENTO DE ARCHIVOS OPTIMIZADO ---
def process_audio_file(uploaded_file):
    """
    Procesamiento optimizado para máxima compresión compatible con Whisper.
    Reduce tamaño de archivos grandes >25MB convirtiendo a mono y bajo bitrate.
    """
    try:
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"input_{safe_name}")
        output_path = os.path.join(temp_dir, f"processed_{os.path.splitext(safe_name)[0]}.mp3")

        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv', '.avi', '.flv'))
        
        st.info(f"📊 Archivo original: {file_size_mb:.1f} MB | Tipo: {'Video' if is_video else 'Audio'}")
        
        # Convertimos si es video O si el audio es muy pesado (>24MB para dejar margen)
        if is_video or file_size_mb > 24.0:
            status_text = f"🔄 Optimizando archivo de {file_size_mb:.1f} MB para transcripción..."
            with st.spinner(status_text):
                try:
                    clip = AudioFileClip(input_path)
                    
                    # Configuración agresiva pero segura para Whisper:
                    # - 32k bitrate (suficiente para voz)
                    # - Mono (1 canal)
                    # - 16000 Hz (frecuencia nativa de Whisper)
                    clip.write_audiofile(
                        output_path, 
                        bitrate="32k",    # Bitrate bajo para reducir peso
                        nbytes=2, 
                        codec='libmp3lame', 
                        ffmpeg_params=["-ac", "1", "-ar", "16000"], # Mono, 16khz
                        logger=None
                    )
                    clip.close()
                    
                    # Eliminar original pesado
                    if os.path.exists(input_path): 
                        os.remove(input_path)
                    
                    new_size = os.path.getsize(output_path) / (1024 * 1024)
                    st.success(f"✅ Comprimido exitosamente: {file_size_mb:.1f} MB → {new_size:.1f} MB")
                    return output_path
                except Exception as e:
                    st.error(f"❌ Error en conversión: {e}")
                    return None
        
        # Si es un audio pequeño, solo lo renombramos si es necesario
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
    """Transcripción usando API de Groq"""
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ El archivo optimizado ({size_mb:.1f}MB) sigue superando el límite de 25MB de Groq. Intenta recortarlo.")
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
        st.error(f"❌ Error API Groq: {e}")
        return None, None

# --- CORRECCIÓN ---
def correct_text_with_llama(client, raw_text):
    """Corrección ortográfica con Llama 3"""
    system_prompt = """Eres un corrector ortográfico experto en español.

TAREA:
- Corrige SOLO ortografía, tildes, puntuación y mayúsculas
- Asegúrate de poner tildes en ciudades y nombres (ej: Popayán, Bogotá, Medellín)
- Mantén el CONTENIDO EXACTO original
- NO modifiques palabras técnicas
- Devuelve ÚNICAMENTE el texto corregido"""

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
        
        # Limpieza de respuestas conversacionales del modelo
        for prefix in ["Aquí está el texto corregido:", "Texto corregido:", "Corrección:"]:
            result = result.replace(prefix, "")
        
        return result.strip()
    except Exception as e:
        st.warning(f"⚠️ Corrección omitida: {e}")
        return raw_text

# --- BÚSQUEDA MEJORADA (SOLUCIÓN A TILDES) ---
def search_in_segments(query, segments, context_size=3, fuzzy_threshold=0.7):
    """
    Búsqueda que ignora tildes en la comparación pero respeta el texto original.
    """
    results = []
    if not query or not segments: 
        return results
    
    # 1. Normalizar la consulta (ej: "Popayán" -> "popayan")
    query_normalized = normalize_text(query)
    
    for i, seg in enumerate(segments):
        # 2. Normalizar el segmento del texto (ej: "...en Popayán..." -> "...en popayan...")
        text_original = seg['text']
        text_normalized = normalize_text(text_original)
        
        # 3. Comparar las versiones normalizadas
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
                "match": text_original,  # Mostramos el texto original con tildes
                "prev": prev, 
                "next": nxt,
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
            options=["whisper-large-v3-turbo", "whisper-large-v3"],
            help="• Turbo: Más rápido, buena precisión\n• V3: Máxima precisión, más lento",
            label_visibility="collapsed"
        )
        
        st.divider()
        
        st.markdown("#### 🔧 Opciones Avanzadas")
        st.session_state.enable_punctuation = st.checkbox(
            "✏️ Mejorar puntuación automática", 
            value=True,
            help="Usa AI prompt para mejorar puntuación durante transcripción"
        )
        
        st.divider()
        
        st.markdown("#### 🔍 Configuración de Búsqueda")
        st.session_state.context_sentences = st.slider(
            "Oraciones de contexto",
            min_value=1,
            max_value=10,
            value=3,
            help="Cantidad de oraciones antes y después"
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
        
        large_mode = st.checkbox(
            "📂 Modo Archivo Grande", 
            help="Recomendado si el audio dura más de 1 hora"
        )
        
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
        
        st.divider()
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- HEADER PRINCIPAL ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎙️ Transcriptor Pro")
        st.caption("Transcripción avanzada con IA | Búsqueda inteligente | Chat contextual")
    with col2:
        if st.session_state.transcript_text:
            st.success("✅ Listo")

    # --- UPLOAD ---
    uploaded_file = st.file_uploader(
        "📁 Subir archivo de audio o video", 
        type=["mp3", "mp4", "wav", "m4a", "mov", "mkv", "avi", "flv", "ogg", "webm"],
        help="Formatos: MP3, MP4, WAV, M4A, MOV, MKV, AVI, FLV, OGG, WebM"
    )

    if uploaded_file:
        if st.button("🚀 Iniciar Transcripción", type="primary", use_container_width=True):
            st.session_state.search_results = None
            st.session_state.last_search_query = ""
            
            with st.status("⚙️ Procesando...", expanded=True) as status:
                st.write("🔍 Analizando archivo...")
                
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    raw, segs = transcribe_audio_verbose(
                        client, 
                        final_path, 
                        model_choice,
                        st.session_state.enable_punctuation
                    )
                    
                    if raw and segs:
                        if large_mode:
                            st.info("ℹ️ Modo Grande: Corrección ortográfica omitida para ahorrar tiempo")
                            st.session_state.transcript_text = raw
                        else:
                            st.write("✨ Mejorando ortografía con IA...")
                            st.session_state.transcript_text = correct_text_with_llama(client, raw)
                        
                        st.session_state.transcript_segments = segs
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
        tab_txt, tab_chat, tab_export = st.tabs([
            "📝 Transcripción & Búsqueda", 
            "💬 Chat IA", 
            "📥 Exportar"
        ])

        # TAB 1: BÚSQUEDA MEJORADA
        with tab_txt:
            st.markdown("### 🔍 Búsqueda Inteligente")
            
            # Usamos st.form para habilitar la tecla ENTER al buscar
            with st.form(key="search_form", clear_on_submit=False):
                col_s, col_b = st.columns([5, 1])
                with col_s: 
                    search_query = st.text_input(
                        "Buscar en transcripción", 
                        value=st.session_state.last_search_query,
                        placeholder="Ej: 'popayan', 'tecnología'...",
                        label_visibility="collapsed",
                        key="search_input_widget"
                    )
                with col_b:
                    submit_search = st.form_submit_button("🔎", use_container_width=True)

            if submit_search:
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
                                confidence_class = f"confidence-{r['confidence']}"
                                confidence_text = {"high": "Exacto", "medium": "Probable", "low": "Similar"}[r['confidence']]
                                
                                st.markdown(
                                    f"""<div class='search-result'>
                                        <span class='confidence-badge {confidence_class}'>{confidence_text}</span>
                                        <br><br>
                                        <span class='context-text'>...{r['prev']}</span> 
                                        <span class='highlight'>{r['match']}</span> 
                                        <span class='context-text'>{r['next']}...</span>
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
                        <small>💡 Tip: {'La búsqueda inteligente está activa (ignorando tildes)' if enable_fuzzy else 'Activa búsqueda inteligente en el menú'}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🔄 Nueva búsqueda", key="new_search"):
                        st.session_state.last_search_query = ""
                        st.session_state.search_results = None
                        st.rerun()
            
            st.divider()
            st.markdown("### 📄 Texto Completo")
            st.text_area(
                "Transcripción", 
                value=st.session_state.transcript_text, 
                height=400,
                label_visibility="collapsed"
            )

        # TAB 2: CHAT
        with tab_chat:
            st.markdown("### 💬 Asistente IA")
            st.caption("Haz preguntas inteligentes sobre el contenido")
            
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
            
            if p := st.chat_input("💭 Tu pregunta..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): 
                    st.markdown(p)
                
                chat_context = st.session_state.transcript_text[:20000] if large_mode else st.session_state.transcript_text

                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system", "content": f"""Eres un asistente experto en análisis de transcripciones.

CONTEXTO DE LA TRANSCRIPCIÓN:
{chat_context}

INSTRUCCIONES:
- Responde basándote ÚNICAMENTE en el contenido de la transcripción
- Si no encuentras información, dilo claramente
- Sé conciso pero completo"""},
                                {"role": "user", "content": p}
                            ], 
                            stream=True,
                            temperature=0.2,
                            max_tokens=2000
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: 
                        st.error(f"❌ Error: {e}")
            
            if st.session_state.chat_history:
                if st.button("🗑️ Limpiar chat"):
                    st.session_state.chat_history = []
                    st.rerun()

        # TAB 3: EXPORTACIÓN
        with tab_export:
            st.markdown("### 📥 Exportar Transcripción")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Formato Simple")
                st.download_button(
                    "📄 Texto plano (.txt)", 
                    st.session_state.transcript_text, 
                    "transcripcion.txt",
                    use_container_width=True
                )
                st.download_button(
                    "📝 Markdown (.md)", 
                    st.session_state.transcript_text, 
                    "transcripcion.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col2:
                st.markdown("#### Con Timestamps")
                timestamped = export_with_timestamps(st.session_state.transcript_segments)
                st.download_button(
                    "⏱️ Con marcas de tiempo (.txt)", 
                    timestamped, 
                    "transcripcion_timestamps.txt",
                    use_container_width=True
                )
            
            st.divider()
            st.markdown("#### Vista Previa con Timestamps")
            st.code(timestamped[:1000] + "..." if len(timestamped) > 1000 else timestamped, language="text")

if __name__ == "__main__":
    if check_password(): 
        main_app()
