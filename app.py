import streamlit as st
import os
import tempfile
from groq import Groq
from moviepy.editor import AudioFileClip
import html  # ← IMPORTANTE: Para escapar caracteres especiales en HTML

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
    .timestamp-button {
        background-color: #ff4b4b;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .timestamp-button:hover {
        background-color: #ff3333;
        transform: scale(1.05);
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
    .stForm { border: none; padding: 0; }
    
    /* Mejoras visuales generales */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
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
if "search_trigger" not in st.session_state: st.session_state.search_trigger = 0

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
        if st.button("Ingresar", use_container_width=True):
            try:
                if pwd == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("⛔ Contraseña incorrecta")
            except: st.error("❌ Error en configuración secrets.toml")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: return None

# --- PROCESAMIENTO DE ARCHIVOS (ROBUSTO) ---
def process_audio_file(uploaded_file):
    """
    Maneja la conversión y compresión. Usa rutas temporales manuales
    para evitar errores con archivos grandes (>100MB).
    """
    try:
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"input_{safe_name}")
        output_path = os.path.join(temp_dir, f"processed_{os.path.splitext(safe_name)[0]}.mp3")

        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv'))
        
        if is_video or file_size_mb > 24.0:
            status_text = f"🔄 Comprimiendo archivo de {file_size_mb:.1f} MB (esto puede tardar)..."
            with st.spinner(status_text):
                try:
                    clip = AudioFileClip(input_path)
                    clip.write_audiofile(
                        output_path, 
                        bitrate="32k", 
                        nbytes=2, 
                        codec='libmp3lame', 
                        ffmpeg_params=["-ac", "1"], 
                        logger=None
                    )
                    clip.close()
                    if os.path.exists(input_path): os.remove(input_path)
                    return output_path
                except Exception as e:
                    st.error(f"❌ Error interno en conversión: {e}")
                    return None
        
        if input_path != output_path:
            if os.path.exists(output_path): os.remove(output_path)
            os.rename(input_path, output_path)
        return output_path

    except Exception as e:
        st.error(f"❌ Error gestionando archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name):
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ El archivo comprimido ({size_mb:.1f}MB) sigue superando el límite de 25MB de Groq.")
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
        st.error(f"❌ Error API Groq: {e}")
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

# --- BÚSQUEDA MEJORADA CON MÁS CONTEXTO ---
def search_in_segments(query, segments, context_size=3):
    """
    Busca en segmentos con contexto configurable.
    context_size: número de segmentos antes y después para mostrar como contexto
    """
    results = []
    if not query or not segments: return results
    
    q = query.lower()
    for i, seg in enumerate(segments):
        if q in seg['text'].lower():
            # Contexto previo (más amplio)
            s_idx = max(0, i - context_size)
            prev = " ".join([s['text'] for s in segments[s_idx:i]])
            
            # Contexto posterior (más amplio)
            e_idx = min(len(segments), i + context_size + 1)
            nxt = " ".join([s['text'] for s in segments[i+1:e_idx]])
            
            results.append({
                "start": seg['start'], 
                "formatted": format_timestamp(seg['start']),
                "match": seg['text'], 
                "prev": prev, 
                "next": nxt,
                "segment_index": i
            })
    return results

# --- APLICACIÓN PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    # --- BARRA LATERAL ---
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        model_choice = st.selectbox(
            "🎯 Modelo de Transcripción", 
            options=["whisper-large-v3-turbo", "whisper-large-v3"],
            help="Turbo es más rápido. V3 es más preciso."
        )
        
        st.divider()
        
        # Control de contexto en búsqueda
        st.markdown("#### 🔍 Configuración de Búsqueda")
        context_size = st.slider(
            "Oraciones de contexto",
            min_value=1,
            max_value=8,
            value=st.session_state.context_sentences,
            help="Cantidad de oraciones antes y después de la coincidencia"
        )
        if context_size != st.session_state.context_sentences:
            st.session_state.context_sentences = context_size
            # Si hay búsqueda activa, recalcular resultados
            if st.session_state.last_search_query:
                st.session_state.search_results = search_in_segments(
                    st.session_state.last_search_query,
                    st.session_state.transcript_segments,
                    context_size
                )
        
        st.divider()
        
        large_mode = st.checkbox(
            "📂 Modo Archivo Grande / Largo", 
            help="Actívalo si el audio dura >40 min o pesa >25MB. Omite corrección y trunca contexto de chat."
        )
        
        st.divider()
        
        # Estadísticas
        if st.session_state.transcript_text:
            st.markdown("#### 📊 Estadísticas")
            word_count = len(st.session_state.transcript_text.split())
            char_count = len(st.session_state.transcript_text)
            segment_count = len(st.session_state.transcript_segments) if st.session_state.transcript_segments else 0
            
            st.markdown(f"""
            <div class='stats-card'>
                <div style='font-size: 24px; font-weight: bold;'>{word_count:,}</div>
                <div>Palabras</div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"**Caracteres:** {char_count:,}")
            st.markdown(f"**Segmentos:** {segment_count}")
        
        st.divider()
        
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- HEADER PRINCIPAL ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎙️ Transcriptor Pro")
        st.caption("Transcribe, busca y chatea con tus audios")
    with col2:
        if st.session_state.transcript_text:
            st.success("✅ Audio procesado")

    uploaded_file = st.file_uploader(
        "📁 Subir archivo de audio o video", 
        type=["mp3", "mp4", "wav", "m4a", "mov", "mkv"],
        help="Formatos soportados: MP3, MP4, WAV, M4A, MOV, MKV"
    )

    if uploaded_file:
        if st.button("🚀 Procesar Audio", type="primary", use_container_width=True):
            with st.status("⚙️ Procesando archivo...", expanded=True) as status:
                st.write("🔍 Analizando y optimizando archivo...")
                
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    raw, segs = transcribe_audio_verbose(client, final_path, model_choice)
                    
                    if raw and segs:
                        if large_mode:
                            st.info("ℹ️ Modo Archivo Grande: Se omite corrección ortográfica.")
                            st.session_state.transcript_text = raw
                        else:
                            st.write("✨ Corrigiendo ortografía con IA...")
                            st.session_state.transcript_text = correct_text_with_llama(client, raw)
                        
                        st.session_state.transcript_segments = segs
                        st.session_state.audio_start_time = 0
                        st.session_state.search_results = None
                        st.session_state.chat_history = []
                        st.session_state.last_search_query = ""
                        
                        status.update(label="✅ ¡Procesamiento completado!", state="complete", expanded=False)
                    else: 
                        status.update(label="❌ Error en transcripción", state="error")
                else: 
                    status.update(label="❌ Error procesando archivo", state="error")

    # --- REPRODUCTOR PERSISTENTE ---
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.markdown("### 🎵 Reproductor de Audio")
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)
        st.caption("💡 Tip: Usa el buscador sin detener la reproducción. Los timestamps sí saltan al momento exacto.")

    # --- CONTENIDO PRINCIPAL ---
    if st.session_state.transcript_text:
        tab_txt, tab_chat = st.tabs(["📝 Transcripción y Búsqueda", "💬 Chat Inteligente"])

        # PESTAÑA 1: TEXTO Y BÚSQUEDA MEJORADA
        with tab_txt:
            st.markdown("### 🔍 Búsqueda Avanzada en Transcripción")
            
            # Búsqueda SIN formulario para evitar rerun
            col_search, col_btn, col_clear = st.columns([4, 1, 1])
            with col_search: 
                search_query = st.text_input(
                    "Palabra o frase clave", 
                    value=st.session_state.last_search_query,
                    placeholder="Ejemplo: 'innovación', 'proyecto importante'...",
                    label_visibility="collapsed",
                    key="search_input"
                )
            with col_btn:
                st.markdown("<div style='margin-top: 0px;'></div>", unsafe_allow_html=True)
                if st.button("🔎 Buscar", use_container_width=True, key="search_btn"):
                    st.session_state.search_trigger += 1
            with col_clear:
                st.markdown("<div style='margin-top: 0px;'></div>", unsafe_allow_html=True)
                if st.button("🗑️ Limpiar", use_container_width=True, key="clear_search_btn"):
                    st.session_state.last_search_query = ""
                    st.session_state.search_results = None
                    st.rerun()
            
            # Ejecutar búsqueda cuando cambia el query o se presiona el botón
            if search_query != st.session_state.last_search_query or st.session_state.search_trigger > 0:
                if search_query.strip():  # ← Solo buscar si hay contenido real
                    st.session_state.last_search_query = search_query
                    st.session_state.search_results = search_in_segments(
                        search_query, 
                        st.session_state.transcript_segments,
                        st.session_state.context_sentences
                    )
                else:
                    # Limpiar búsqueda si el campo está vacío
                    st.session_state.last_search_query = ""
                    st.session_state.search_results = None
                
                st.session_state.search_trigger = 0

            # Mostrar resultados o mensaje de "sin resultados"
            if st.session_state.last_search_query:
                if st.session_state.search_results:
                    st.success(f"✅ Se encontraron **{len(st.session_state.search_results)}** coincidencias para '{st.session_state.last_search_query}'")
                    
                    for i, r in enumerate(st.session_state.search_results):
                        with st.container():
                            b_col, t_col = st.columns([1, 8])
                            with b_col:
                                # Botón que actualiza el timestamp y recarga solo el reproductor
                                if st.button(f"▶️ {r['formatted']}", key=f"jump_{i}", use_container_width=True):
                                    st.session_state.audio_start_time = int(r['start'])
                                    st.rerun()
                            
                            with t_col:
                                # ← AQUÍ ESTÁ LA CORRECCIÓN CLAVE: usar html.escape()
                                prev_escaped = html.escape(r['prev'])
                                match_escaped = html.escape(r['match'])
                                next_escaped = html.escape(r['next'])
                                
                                st.markdown(
                                    f"""<div class='search-result'>
                                        <span class='context-text'>...{prev_escaped}</span> 
                                        <span class='highlight'>{match_escaped}</span> 
                                        <span class='context-text'>{next_escaped}...</span>
                                    </div>""", 
                                    unsafe_allow_html=True
                                )
                    
                    if st.button("🗑️ Limpiar resultados de búsqueda"):
                        st.session_state.search_results = None
                        st.session_state.last_search_query = ""
                        st.rerun()
                
                else:
                    # ← CORRECCIÓN: escapar el query en el mensaje de "sin resultados"
                    query_escaped = html.escape(st.session_state.last_search_query)
                    st.markdown(f"""
                    <div class='no-results'>
                        <strong>⚠️ Sin resultados</strong><br>
                        No se encontraron coincidencias para "<em>{query_escaped}</em>".<br>
                        <small>💡 Intenta con términos diferentes o verifica la ortografía.</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🔄 Nueva búsqueda"):
                        st.session_state.last_search_query = ""
                        st.session_state.search_results = None
                        st.rerun()
            
            st.divider()
            
            # Texto completo - ← st.text_area maneja UTF-8 correctamente
            st.markdown("### 📄 Texto Completo de la Transcripción")
            st.text_area(
                "Transcripción", 
                value=st.session_state.transcript_text, 
                height=500,
                label_visibility="collapsed"
            )
            
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.download_button(
                    "📥 Descargar como TXT", 
                    st.session_state.transcript_text.encode('utf-8'),  # ← Asegurar UTF-8 en descarga
                    "transcripcion.txt",
                    use_container_width=True
                )
            with col_d2:
                st.download_button(
                    "📥 Descargar como MD", 
                    st.session_state.transcript_text.encode('utf-8'),  # ← Asegurar UTF-8 en descarga
                    "transcripcion.md",
                    mime="text/markdown",
                    use_container_width=True
                )

        # PESTAÑA 2: CHAT
        with tab_chat:
            st.markdown("### 💬 Chatea con tu Transcripción")
            st.caption("Haz preguntas sobre el contenido del audio y obtén respuestas inteligentes")
            
            # Mostrar historial de chat
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
            
            # Input de chat
            if p := st.chat_input("💭 Escribe tu pregunta aquí..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): 
                    st.markdown(p)
                
                # Preparar contexto
                full_text = st.session_state.transcript_text
                
                if large_mode:
                    chat_context = full_text[:15000] + "\n\n...(texto truncado para evitar límites de contexto)..."
                else:
                    chat_context = full_text

                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": f"Eres un asistente experto en analizar transcripciones. Responde de forma clara y precisa basándote en el siguiente contexto:\n\n{chat_context}"},
                                {"role": "user", "content": p}
                            ], 
                            stream=True,
                            temperature=0.3
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: 
                        st.error(f"❌ Error en el chat: {e}")
            
            # Botón para limpiar chat
            if st.session_state.chat_history:
                if st.button("🗑️ Limpiar historial de chat"):
                    st.session_state.chat_history = []
                    st.rerun()

if __name__ == "__main__":
    if check_password(): main_app()
