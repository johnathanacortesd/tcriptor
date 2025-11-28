import streamlit as st
import os
import tempfile
import textwrap
from groq import Groq
from moviepy.editor import AudioFileClip
import math

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Transcriptor Pro V2",
    page_icon="🎙️",
    layout="wide"
)

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .search-result { 
        background-color: #f0f2f6;
        padding: 15px; 
        border-radius: 8px; 
        margin-bottom: 10px; 
        border-left: 5px solid #ff4b4b;
    }
    .highlight { background-color: #ffeb3b; font-weight: bold; padding: 2px 5px; border-radius: 4px; }
    .timestamp-btn { text-align: left; margin: 0; }
    /* Ajuste para formularios */
    [data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# --- ESTADO ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "transcript_text" not in st.session_state: st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state: st.session_state.transcript_segments = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "search_results" not in st.session_state: st.session_state.search_results = None

# --- UTILIDADES ---
def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def generate_srt(segments):
    """Genera contenido en formato SRT para subtítulos"""
    srt_content = ""
    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        
        # Formato SRT: 00:00:00,000
        def to_srt_time(sec):
            hrs = int(sec // 3600)
            mins = int((sec % 3600) // 60)
            secs = int(sec % 60)
            millis = int((sec - int(sec)) * 1000)
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"
            
        srt_content += f"{i+1}\n"
        srt_content += f"{to_srt_time(start)} --> {to_srt_time(end)}\n"
        srt_content += f"{seg['text'].strip()}\n\n"
    return srt_content

# --- SEGURIDAD MEJORADA ---
def check_password():
    if st.session_state.authenticated: return True
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("🔒 Por favor, inicia sesión para continuar.")
        with st.form("login_form"):
            pwd = st.text_input("Contraseña", type="password")
            if st.form_submit_button("Ingresar", use_container_width=True):
                # Manejo seguro si no existe secrets
                correct_pwd = st.secrets.get("general", {}).get("app_password", "admin")
                if pwd == correct_pwd:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("⛔ Contraseña incorrecta")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: 
        st.error("❌ Falta la API Key de Groq en secrets.toml")
        return None

# --- PROCESAMIENTO ---
def process_audio_file(uploaded_file):
    try:
        temp_dir = tempfile.gettempdir()
        safe_name = "".join([c for c in uploaded_file.name if c.isalnum() or c in ('.','_')]).strip()
        input_path = os.path.join(temp_dir, f"raw_{safe_name}")
        output_path = os.path.join(temp_dir, f"ready_{os.path.splitext(safe_name)[0]}.mp3")

        with open(input_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
        is_video = input_path.lower().endswith(('.mp4', '.m4v', '.mov', '.mkv'))
        
        # Comprimir si es video o si es audio > 24MB
        if is_video or file_size_mb > 24.0:
            with st.spinner(f"🔄 Optimizando archivo de {file_size_mb:.1f} MB..."):
                clip = AudioFileClip(input_path)
                # Bitrate 32k es suficiente para voz (speech-to-text) y reduce drásticamente el peso
                clip.write_audiofile(output_path, bitrate="32k", codec='libmp3lame', logger=None)
                clip.close()
                if os.path.exists(input_path): os.remove(input_path)
                return output_path
        
        # Si ya es audio pequeño, solo renombrar/mover
        if input_path != output_path:
            if os.path.exists(output_path): os.remove(output_path)
            os.rename(input_path, output_path)
        return output_path

    except Exception as e:
        st.error(f"Error procesando: {e}")
        return None

# --- TRANSCRIPCIÓN CON CONTEXTO ---
def transcribe_audio_verbose(client, file_path, model_name, prompt_context=""):
    try:
        with open(file_path, "rb") as file:
            # El parámetro 'prompt' ayuda a Whisper con nombres propios o terminología
            transcription = client.audio.transcriptions.create(
                file=(file_path, file.read()),
                model=model_name,
                prompt=prompt_context, 
                response_format="verbose_json",
                language="es",
                temperature=0.0
            )
        return transcription.text, transcription.segments
    except Exception as e:
        st.error(f"Error API Groq: {e}")
        return None, None

# --- CORRECCIÓN POR CHUNKS (MEJORA DE PRECISIÓN) ---
def correct_text_with_llama_chunked(client, raw_text):
    """
    Divide el texto en trozos para asegurar que el LLM no pierda contexto
    o resuma el contenido por falta de tokens.
    """
    # Dividir en chunks de aprox 3000 caracteres (seguro para contexto de 8k/128k)
    chunks = textwrap.wrap(raw_text, 3000, break_long_words=False, replace_whitespace=False)
    corrected_chunks = []
    
    progress_bar = st.progress(0)
    total_chunks = len(chunks)
    
    system_prompt = (
        "Eres un editor experto. Tu ÚNICA tarea es corregir la puntuación, ortografía y gramática "
        "del siguiente texto transcrito. NO resumas. NO elimines información. "
        "NO agregues introducciones ni conclusiones. Mantén el texto completo."
    )

    for i, chunk in enumerate(chunks):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt}, 
                    {"role": "user", "content": chunk}
                ],
                temperature=0.1
            )
            res = completion.choices[0].message.content.strip()
            # Limpieza básica por si el modelo es "charlatán"
            if res.startswith("Aquí está") or res.startswith("Texto corregido:"):
                res = res.split(":", 1)[1].strip()
            corrected_chunks.append(res)
        except Exception as e:
            corrected_chunks.append(chunk) # Fallback al original si falla
        
        progress_bar.progress((i + 1) / total_chunks)
    
    progress_bar.empty()
    return " ".join(corrected_chunks)

# --- APP PRINCIPAL ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    with st.sidebar:
        st.title("⚙️ Panel de Control")
        model_choice = st.selectbox("Modelo", ["whisper-large-v3-turbo", "whisper-large-v3"])
        
        st.divider()
        st.markdown("### 🧠 Contexto para IA")
        glossary = st.text_area(
            "Glosario / Vocabulario", 
            placeholder="Nombres propios, empresas, siglas técnicas... (ayuda a la precisión)",
            height=100
        )
        
        enable_correction = st.toggle("Corrección Gramatical con IA", value=True)
        
        st.divider()
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ Transcriptor Pro V2")
    st.caption("Sistema de transcripción de alta fidelidad con corrección contextual")

    uploaded_file = st.file_uploader("Arrastra tu audio/video aquí", type=["mp3","mp4","wav","m4a","mov"])

    if uploaded_file:
        if st.button("🚀 Iniciar Transcripción", type="primary", use_container_width=True):
            with st.status("Procesando...", expanded=True) as status:
                st.write("🔧 Preparando audio...")
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    # Pasamos el glosario como prompt_context
                    raw, segs = transcribe_audio_verbose(client, final_path, model_choice, glossary)
                    
                    if raw and segs:
                        if enable_correction:
                            st.write("✨ Aplicando corrección gramatical (Chunking)...")
                            st.session_state.transcript_text = correct_text_with_llama_chunked(client, raw)
                        else:
                            st.session_state.transcript_text = raw
                        
                        st.session_state.transcript_segments = segs
                        st.session_state.search_results = None
                        status.update(label="✅ ¡Completado!", state="complete", expanded=False)
                    else:
                        status.update(label="❌ Error API", state="error")

    # --- INTERFAZ DE RESULTADOS ---
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    if st.session_state.transcript_text:
        tab1, tab2, tab3 = st.tabs(["📄 Texto", "🔎 Búsqueda", "💬 Chat IA"])
        
        with tab1:
            st.text_area("Resultado", st.session_state.transcript_text, height=400)
            c1, c2, c3 = st.columns(3)
            c1.download_button("📥 TXT", st.session_state.transcript_text, "transcripcion.txt")
            # Nueva función de exportar SRT
            if st.session_state.transcript_segments:
                srt_data = generate_srt(st.session_state.transcript_segments)
                c2.download_button("🎬 Subtítulos (SRT)", srt_data, "subtitulos.srt")
        
        with tab2:
            with st.form("search"):
                query = st.text_input("Buscar frase")
                if st.form_submit_button("Buscar"):
                    if query and st.session_state.transcript_segments:
                        res = []
                        for s in st.session_state.transcript_segments:
                            if query.lower() in s['text'].lower():
                                res.append(s)
                        st.session_state.search_results = res
            
            if st.session_state.search_results:
                st.success(f"{len(st.session_state.search_results)} coincidencias")
                for item in st.session_state.search_results:
                    col_play, col_txt = st.columns([1, 6])
                    with col_play:
                        if st.button(f"⏱️ {format_timestamp(item['start'])}", key=item['start']):
                            st.session_state.audio_start_time = int(item['start'])
                            st.rerun()
                    with col_txt:
                        st.markdown(f"...{item['text'].replace(query, f'**{query}**')}...")
        
        with tab3:
            # Chat simple implementado anteriormente
            for msg in st.session_state.chat_history:
                st.chat_message(msg["role"]).write(msg["content"])
                
            if prompt := st.chat_input("Pregunta sobre el audio"):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                st.chat_message("user").write(prompt)
                
                # Contexto limitado para el chat
                context = st.session_state.transcript_text[:20000] # Limite para no romper el chat
                
                try:
                    completion = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": f"Contexto del audio:\n{context}"},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    response = completion.choices[0].message.content
                    st.session_state.chat_history.append({"role": "assistant", "content": response})
                    st.chat_message("assistant").write(response)
                except Exception as e:
                    st.error(f"Error chat: {e}")

if __name__ == "__main__":
    if check_password():
        main_app()
