import streamlit as st
import os
import tempfile
import math
from groq import Groq
from moviepy.editor import AudioFileClip

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro + Búsqueda",
    page_icon="🔍",
    layout="wide"
)

# --- INICIALIZACIÓN DEL ESTADO ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "transcript_text" not in st.session_state:
    st.session_state.transcript_text = None  # Texto corregido por Llama
if "transcript_segments" not in st.session_state:
    st.session_state.transcript_segments = None # Segmentos con tiempo de Whisper
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "audio_start_time" not in st.session_state:
    st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- UTILIDADES ---
def format_timestamp(seconds):
    """Convierte segundos a formato MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

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

# --- MÓDULO 2: TRANSCRIPCIÓN CON TIMESTAMPS ---
def transcribe_audio_verbose(client, file_path):
    """Usa whisper-large-v3 y devuelve texto Y segmentos de tiempo."""
    try:
        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3",
                response_format="verbose_json", # CLAVE: Pedimos JSON detallado
                language="es",
                temperature=0.0
            )
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"Error API Transcripción: {e}")
        return None, None

# --- MÓDULO 3: CORRECCIÓN ---
def correct_text_with_llama(client, raw_text):
    system_prompt = (
        "Eres un editor experto. Corrige tildes, ortografía y palabras cortadas. "
        "NO resumas. NO cambies estilo. Mantén el contenido exacto."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
            temperature=0.1
        )
        return completion.choices[0].message.content
    except:
        return raw_text

# --- MÓDULO 4: BÚSQUEDA ---
def search_in_segments(query, segments):
    """Busca la query en los segmentos y devuelve contexto."""
    results = []
    if not query or not segments:
        return results
    
    for i, seg in enumerate(segments):
        if query.lower() in seg['text'].lower():
            # Obtener contexto
            prev_text = segments[i-1]['text'] if i > 0 else ""
            next_text = segments[i+1]['text'] if i < len(segments)-1 else ""
            
            results.append({
                "start": seg['start'],
                "formatted_time": format_timestamp(seg['start']),
                "match": seg['text'],
                "context_prev": prev_text,
                "context_next": next_text
            })
    return results

# --- MÓDULO 5: CHAT ---
def chat_interface(client):
    st.header("💬 Chat con el Audio")
    if not st.session_state.transcript_text:
        st.info("Carga un audio primero.")
        return

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Pregunta algo..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            full_response = ""
            resp_container = st.empty()
            try:
                stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": f"Responde solo basado en esto:\n{st.session_state.transcript_text}"},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        resp_container.markdown(full_response + "▌")
                resp_container.markdown(full_response)
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"Error: {e}")

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    st.title("🎙️ Transcriptor Pro: Búsqueda y Audio")
    
    # Sidebar para logout
    with st.sidebar:
        st.success("Conectado")
        if st.button("Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    # Carga de archivo
    uploaded_file = st.file_uploader("Subir audio/video", type=["mp3", "mp4", "m4a", "wav"])

    if uploaded_file:
        # Procesamiento inicial (solo si no se ha procesado este archivo o es uno nuevo)
        # Nota simple: Aquí procesamos al hacer click en el botón
        if st.button("🚀 Procesar Audio", type="primary"):
            with st.status("Analizando...", expanded=True) as status:
                st.write("📥 Convirtiendo...")
                # Guardamos el path en session state para que el reproductor persista
                temp_path = convert_mp4_to_mp3(uploaded_file)
                st.session_state.audio_path = temp_path
                
                if temp_path:
                    st.write("🎧 Transcribiendo (obteniendo tiempos)...")
                    # Obtenemos TEXTO y SEGMENTOS
                    raw_text, segments = transcribe_audio_verbose(client, temp_path)
                    
                    if raw_text and segments:
                        st.write("✨ Corrigiendo gramática...")
                        corrected = correct_text_with_llama(client, raw_text)
                        
                        st.session_state.transcript_text = corrected
                        st.session_state.transcript_segments = segments
                        st.session_state.audio_start_time = 0 # Reset start time
                        status.update(label="¡Completado!", state="complete", expanded=False)
                    else:
                        status.update(label="Error en transcripción", state="error")

    # --- ZONA DE REPRODUCTOR DE AUDIO ---
    # Si hay un archivo procesado, mostramos el reproductor arriba
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.markdown("### 🎧 Reproductor")
        # st.audio permite start_time. Al cambiar el estado, esto se recarga en el punto exacto.
        st.audio(st.session_state.audio_path, format="audio/mp3", start_time=st.session_state.audio_start_time)

    # --- PESTAÑAS ---
    if st.session_state.transcript_text:
        tab1, tab2, tab3 = st.tabs(["📝 Texto Completo", "🔍 Búsqueda Inteligente", "💬 Chat"])

        # PESTAÑA 1: TEXTO CORREGIDO
        with tab1:
            st.subheader("Transcripción Corregida")
            st.text_area("Texto", value=st.session_state.transcript_text, height=500)
            st.download_button("Descargar TXT", st.session_state.transcript_text, "transcripcion.txt")

        # PESTAÑA 2: BÚSQUEDA POR TIMESTAMPS
        with tab2:
            st.subheader("Búsqueda por Palabras Clave")
            search_query = st.text_input("Escribe una palabra o frase para buscar en el audio:", placeholder="Ej: contrato, reunión, precio...")

            if search_query:
                results = search_in_segments(search_query, st.session_state.transcript_segments)
                
                if results:
                    st.success(f"Se encontraron {len(results)} coincidencias.")
                    for idx, res in enumerate(results):
                        with st.container():
                            # Diseño de cada resultado
                            c1, c2 = st.columns([1, 5])
                            
                            with c1:
                                st.markdown(f"**⏱️ {res['formatted_time']}**")
                                # El botón actualiza el estado y recarga la página (st.rerun)
                                if st.button("▶️ Escuchar", key=f"play_{idx}"):
                                    st.session_state.audio_start_time = int(res['start'])
                                    st.rerun()
                            
                            with c2:
                                # Mostrar contexto con Markdown para resaltar
                                # Usamos los segmentos originales de Whisper para coincidir con el audio exacto
                                st.markdown(
                                    f"<span style='color:grey'>{res['context_prev']}</span> "
                                    f"<strong style='background-color:#fffdc9; color:black; padding:2px'>{res['match']}</strong> "
                                    f"<span style='color:grey'>{res['context_next']}</span>",
                                    unsafe_allow_html=True
                                )
                            st.divider()
                else:
                    st.warning("No se encontraron coincidencias exactas.")
            else:
                st.info("Ingresa una palabra arriba para ver en qué minuto se dijo.")

        # PESTAÑA 3: CHAT
        with tab3:
            chat_interface(client)

def main():
    if check_password():
        main_app()

if __name__ == "__main__":
    main()
