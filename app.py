import streamlit as st
import os
import tempfile
from groq import Groq
from moviepy.editor import AudioFileClip

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro Seguro",
    page_icon="🔐",
    layout="wide"
)

# --- INICIALIZACIÓN DEL ESTADO (SESSION STATE) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- MÓDULO 0: SEGURIDAD Y AUTENTICACIÓN ---
def check_password():
    """Retorna True si el usuario está logueado, de lo contrario muestra login."""
    if st.session_state.authenticated:
        return True

    st.title("🔒 Acceso Restringido")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("Por favor, ingrese la contraseña para acceder a la herramienta de transcripción.")
        password_input = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar"):
            try:
                # Verifica contra el secreto guardado en secrets.toml
                if password_input == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()  # Recarga la página para mostrar la app
                else:
                    st.error("⛔ Contraseña incorrecta.")
            except FileNotFoundError:
                st.error("Error: No se encontró el archivo .streamlit/secrets.toml")
            except KeyError:
                st.error("Error: La configuración 'app_password' no existe en secrets.toml")

    return False

def get_groq_client():
    """Obtiene la API Key desde secrets y devuelve el cliente Groq."""
    try:
        api_key = st.secrets["general"]["groq_api_key"]
        return Groq(api_key=api_key)
    except Exception as e:
        st.error("❌ Error de configuración: No se encontró 'groq_api_key' en .streamlit/secrets.toml")
        return None

# --- MÓDULO 1: PROCESAMIENTO DE AUDIO ---
def convert_mp4_to_mp3(uploaded_file):
    """Convierte video a audio o guarda audio temporal."""
    try:
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_input:
            tmp_input.write(uploaded_file.read())
            tmp_input_path = tmp_input.name

        output_path = tmp_input_path.replace(suffix, ".mp3")

        if suffix.lower() == ".mp4":
            with st.spinner("Extrayendo audio del video..."):
                video = AudioFileClip(tmp_input_path)
                video.write_audiofile(output_path, logger=None)
                video.close()
            os.remove(tmp_input_path)
            return output_path
        
        return tmp_input_path

    except Exception as e:
        st.error(f"Error procesando archivo: {e}")
        return None

# --- MÓDULO 2: TRANSCRIPCIÓN (Whisper) ---
def transcribe_audio(client, file_path):
    """Usa whisper-large-v3 para transcribir."""
    try:
        with open(file_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model="whisper-large-v3",
                response_format="json",
                language="es",
                temperature=0.0
            )
        return transcription.text
    except Exception as e:
        st.error(f"Error en la API de transcripción: {e}")
        return None

# --- MÓDULO 3: CORRECCIÓN (Llama) ---
def correct_text_with_llama(client, raw_text):
    """Usa llama-3.1-8b-instant para corregir ortografía."""
    system_prompt = (
        "Eres un editor experto. Tu única tarea es corregir tildes, ortografía "
        "y palabras cortadas fonéticamente en el siguiente texto en español. "
        "REGLAS: NO resumas. NO cambies estilo. NO agregues introducciones ni conclusiones. "
        "Mantén el contenido exacto, solo arregla la forma."
    )

    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.1,
            max_tokens=8000
        )
        return completion.choices[0].message.content
    except Exception as e:
        st.error(f"Error en la corrección: {e}")
        return raw_text

# --- MÓDULO 4: CHAT ---
def chat_tab_interface(client):
    """Interfaz de chat RAG."""
    st.header("💬 Chat con tu Audio")
    
    if not st.session_state.transcript:
        st.info("⚠️ Primero debes cargar y transcribir un audio en la pestaña anterior.")
        return

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Pregunta sobre el audio..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            
            system_prompt_chat = (
                "Eres un asistente útil. Responde basándote ÚNICAMENTE en el siguiente texto. "
                "Si no lo sabes, dilo. Sé conciso.\n\n"
                f"CONTEXTO:\n{st.session_state.transcript}"
            )

            try:
                stream = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_prompt_chat},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response + "▌")
                
                response_placeholder.markdown(full_response)
                st.session_state.chat_history.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"Error en el chat: {e}")

# --- MAIN APPLICATION ---
def main_app():
    """Lógica principal de la aplicación una vez autenticado."""
    st.sidebar.success("✅ Autenticado correctamente")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.rerun()

    st.title("🎙️ Transcriptor AI Seguro")
    st.markdown("Whisper Large v3 + Llama 3.1 (Corrección y Chat)")

    client = get_groq_client()
    if not client:
        st.stop() # Detiene la ejecución si no hay API key configurada

    tab1, tab2 = st.tabs(["📝 Transcripción", "💬 Chat"])

    with tab1:
        uploaded_file = st.file_uploader("Cargar archivo", type=["mp3", "mp4", "wav", "m4a"])

        if uploaded_file and st.button("🚀 Transcribir", type="primary"):
            with st.status("Procesando...", expanded=True) as status:
                st.write("📥 Convirtiendo/Preparando audio...")
                audio_path = convert_mp4_to_mp3(uploaded_file)
                
                if audio_path:
                    st.write("🎧 Transcribiendo...")
                    raw_text = transcribe_audio(client, audio_path)
                    
                    if raw_text:
                        st.write("✨ Corrigiendo texto...")
                        corrected_text = correct_text_with_llama(client, raw_text)
                        
                        st.session_state.transcript = corrected_text
                        status.update(label="¡Listo!", state="complete", expanded=False)
                        os.remove(audio_path)
                    else:
                        status.update(label="Falló transcripción", state="error")
                else:
                    status.update(label="Falló archivo", state="error")

        if st.session_state.transcript:
            st.subheader("Texto:")
            st.text_area("Salida", value=st.session_state.transcript, height=400, label_visibility="collapsed")
            st.download_button("💾 Descargar TXT", st.session_state.transcript, "transcripcion.txt")

    with tab2:
        chat_tab_interface(client)

# --- PUNTO DE ENTRADA ---
def main():
    # Si no pasa el check de password, se detiene aquí y muestra login
    if not check_password():
        return

    # Si pasa, ejecuta la app principal
    main_app()

if __name__ == "__main__":
    main()
