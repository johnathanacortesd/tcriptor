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

# --- ESTILOS CSS PARA RESULTADOS DE BÚSQUEDA ---
st.markdown("""
<style>
    .search-result {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 4px solid #ff4b4b;
    }
    .highlight {
        background-color: #ffffcc;
        font-weight: bold;
        padding: 2px 4px;
        border-radius: 3px;
        color: #333;
    }
    .time-badge {
        font-weight: bold;
        color: #ff4b4b;
        margin-right: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN DEL ESTADO ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state:
    st.session_state.transcript_segments = None
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "audio_start_time" not in st.session_state:
    st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
# Estado para el input de búsqueda para poder limpiarlo
if "search_query_val" not in st.session_state:
    st.session_state.search_query_val = ""

# --- UTILIDADES ---
def format_timestamp(seconds):
    """Convierte segundos a MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def clear_search():
    """Callback para limpiar la búsqueda"""
    st.session_state.search_query_val = ""

# --- MÓDULO 0: SEGURIDAD ---
def check_password():
    if st.session_state.authenticated:
        return True

    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password_input = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            try:
                if password_input == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("⛔ Contraseña incorrecta.")
            except:
                st.error("Error leyendo secrets.toml")
    return False

def get_groq_client():
    try:
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except:
        st.error("❌ Falta 'groq_api_key' en secrets.toml")
        return None

# --- MÓDULO 1: AUDIO ---
def convert_mp4_to_mp3(uploaded_file):
    try:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_input:
            tmp_input.write(uploaded_file.read())
            tmp_input_path = tmp_input.name

        output_path = tmp_input_path.replace(suffix, ".mp3")

        if suffix.lower() == ".mp4":
            with st.spinner("Extrayendo audio..."):
                video = AudioFileClip(tmp_input_path)
                video.write_audiofile(output_path, logger=None)
                video.close()
            os.remove(tmp_input_path)
            return output_path
        
        return tmp_input_path
    except Exception as e:
        st.error(f"Error procesando audio: {e}")
        return None

# --- MÓDULO 2: TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name):
    """
    Usa el modelo seleccionado (whisper-large-v3 o turbo).
    Devuelve texto y segmentos.
    """
    try:
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
        st.error(f"Error API Transcripción: {e}")
        return None, None

# --- MÓDULO 3: CORRECCIÓN (ESTRICTA) ---
def correct_text_with_llama(client, raw_text):
    """
    Corrige ortografía sin intros ni saludos.
    """
    system_prompt = (
        "Eres una máquina de corrección de texto. "
        "Tu ÚNICA función es recibir texto y devolverlo con ortografía y tildes corregidas. "
        "REGLAS ABSOLUTAS:\n"
        "1. NO agregues saludos, ni 'Aquí está', ni 'Texto corregido:'. NADA.\n"
        "2. Devuelve SOLO el contenido corregido.\n"
        "3. NO resumas.\n"
        "4. Si el texto está bien, devuélvelo idéntico."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
            temperature=0.0 # Temperatura 0 para máxima determinismo
        )
        result = completion.choices[0].message.content
        
        # Limpieza de seguridad por si la IA desobedece levemente
        prefixes_to_remove = ["Aquí está", "Claro,", "Por supuesto", "El texto corregido:"]
        for prefix in prefixes_to_remove:
            if result.startswith(prefix):
                result = result.split(":", 1)[-1].strip()
                
        return result.strip()
    except:
        return raw_text

# --- MÓDULO 4: BÚSQUEDA CON CONTEXTO AMPLIADO ---
def search_in_segments(query, segments):
    results = []
    if not query or not segments:
        return results
    
    query_lower = query.lower()
    
    for i, seg in enumerate(segments):
        if query_lower in seg['text'].lower():
            # Obtener contexto ampliado (2 segmentos atrás, 2 adelante)
            start_idx = max(0, i - 2)
            end_idx = min(len(segments), i + 3)
            
            # Construir bloques
            context_prev = " ".join([s['text'] for s in segments[start_idx:i]])
            match_text = seg['text']
            context_next = " ".join([s['text'] for s in segments[i+1:end_idx]])
            
            results.append({
                "start": seg['start'],
                "formatted_time": format_timestamp(seg['start']),
                "match": match_text,
                "context_prev": context_prev,
                "context_next": context_next
            })
    return results

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("⚙️ Configuración")
        
        # Selector de Modelo Whisper
        model_choice = st.selectbox(
            "Modelo de Transcripción",
            options=["whisper-large-v3", "whisper-large-v3-turbo"],
            index=0,
            help="Large v3 es más preciso. Turbo es más rápido y barato."
        )
        
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ Transcriptor Pro")

    # --- CARGA Y PROCESAMIENTO ---
    uploaded_file = st.file_uploader("Subir audio/video (MP3, MP4, WAV)", type=["mp3", "mp4", "wav", "m4a"])

    if uploaded_file:
        if st.button("🚀 Procesar Audio", type="primary"):
            with st.status("Procesando...", expanded=True) as status:
                st.write("📥 Preparando audio...")
                temp_path = convert_mp4_to_mp3(uploaded_file)
                st.session_state.audio_path = temp_path
                
                if temp_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    raw_text, segments = transcribe_audio_verbose(client, temp_path, model_choice)
                    
                    if raw_text and segments:
                        st.write("✨ Limpiando y corrigiendo texto...")
                        corrected = correct_text_with_llama(client, raw_text)
                        
                        st.session_state.transcript_text = corrected
                        st.session_state.transcript_segments = segments
                        st.session_state.audio_start_time = 0
                        status.update(label="¡Listo!", state="complete", expanded=False)
                    else:
                        status.update(label="Error", state="error")

    # --- REPRODUCTOR (PERSISTENTE) ---
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path, format="audio/mp3", start_time=st.session_state.audio_start_time)

    # --- PESTAÑAS ---
    if st.session_state.transcript_text:
        tab_text, tab_chat = st.tabs(["📝 Transcripción y Búsqueda", "💬 Chat"])

        # --- PESTAÑA 1: BÚSQUEDA Y TEXTO ---
        with tab_text:
            
            # BARRA DE BÚSQUEDA
            st.markdown("### 🔍 Buscar en el audio")
            c_search, c_clear = st.columns([5, 1])
            with c_search:
                query = st.text_input("Palabra clave:", key="search_query_val", placeholder="Ej: precio, acuerdo, fecha...")
            with c_clear:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True) # Ajuste visual
                st.button("Limpiar", on_click=clear_search)

            # RESULTADOS DE BÚSQUEDA
            if query:
                results = search_in_segments(query, st.session_state.transcript_segments)
                if results:
                    st.info(f"Se encontraron {len(results)} coincidencias.")
                    for i, res in enumerate(results):
                        # Contenedor visual del resultado
                        with st.container():
                            col_play, col_ctx = st.columns([1, 6])
                            
                            with col_play:
                                if st.button(f"▶ {res['formatted_time']}", key=f"jump_{i}", help="Ir a este momento"):
                                    st.session_state.audio_start_time = int(res['start'])
                                    st.rerun()
                            
                            with col_ctx:
                                # HTML seguro para resaltar la palabra y dar contexto gris
                                html_content = f"""
                                <div class="search-result">
                                    <span style="color:#666;">...{res['context_prev']}</span> 
                                    <span class="highlight">{res['match']}</span> 
                                    <span style="color:#666;">{res['context_next']}...</span>
                                </div>
                                """
                                st.markdown(html_content, unsafe_allow_html=True)
                else:
                    st.warning("No se encontraron resultados.")
                
                st.divider() # Separador visual entre búsqueda y texto completo

            # TEXTO COMPLETO
            st.subheader("📜 Texto Completo")
            st.text_area("Contenido", value=st.session_state.transcript_text, height=600, label_visibility="collapsed")
            st.download_button("💾 Descargar Transcripción", st.session_state.transcript_text, "transcripcion.txt")

        # --- PESTAÑA 2: CHAT ---
        with tab_chat:
            st.header("💬 Chat con el contenido")
            
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Haz una pregunta sobre el audio..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    full_res = ""
                    holder = st.empty()
                    try:
                        # Contexto limitado para el chat para ahorrar tokens y mejorar foco
                        stream = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": f"Responde basándote ÚNICAMENTE en:\n{st.session_state.transcript_text}"},
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
                        st.error(f"Error: {e}")

def main():
    if check_password():
        main_app()

if __name__ == "__main__":
    main()
