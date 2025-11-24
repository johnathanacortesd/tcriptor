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

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .search-result { background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 10px; border-left: 4px solid #ff4b4b; }
    .highlight { background-color: #ffffcc; font-weight: bold; padding: 2px 4px; border-radius: 3px; color: #333; }
</style>
""", unsafe_allow_html=True)

# --- ESTADO ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "transcript_text" not in st.session_state: st.session_state.transcript_text = None
if "transcript_segments" not in st.session_state: st.session_state.transcript_segments = None
if "audio_path" not in st.session_state: st.session_state.audio_path = None
if "audio_start_time" not in st.session_state: st.session_state.audio_start_time = 0
if "chat_history" not in st.session_state: st.session_state.chat_history = []
if "search_query_val" not in st.session_state: st.session_state.search_query_val = ""

# --- UTILIDADES ---
def format_timestamp(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def clear_search():
    st.session_state.search_query_val = ""

# --- SEGURIDAD ---
def check_password():
    if st.session_state.authenticated: return True
    st.title("🔒 Acceso Restringido")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            try:
                if pwd == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else: st.error("⛔ Incorrecta")
            except: st.error("Error en secrets.toml")
    return False

def get_groq_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: return None

# --- PROCESAMIENTO DE AUDIO INTELIGENTE ---
def process_audio_file(uploaded_file):
    """
    Maneja la lógica de tamaño y formato.
    1. Guarda el archivo original.
    2. Verifica si es video O si pesa > 25MB.
    3. Si cumple condición, convierte/comprime a MP3 32k (mono).
    """
    try:
        # 1. Guardar archivo crudo temporalmente
        suffix = os.path.splitext(uploaded_file.name)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_input:
            tmp_input.write(uploaded_file.read())
            tmp_input_path = tmp_input.name

        # Obtener tamaño en MB
        file_size_mb = os.path.getsize(tmp_input_path) / (1024 * 1024)
        is_video = suffix.lower() in [".mp4", ".m4v", ".mov"]
        
        # 2. Decidir si convertir
        # Groq limite es 25MB. Convertimos si es video O si es audio pesado.
        if is_video or file_size_mb > 24.0:
            output_path = tmp_input_path.replace(suffix, ".mp3")
            
            with st.spinner(f"Optimizando archivo ({file_size_mb:.1f} MB) para ajustarse al límite de 25MB..."):
                try:
                    # Cargamos clip
                    clip = AudioFileClip(tmp_input_path)
                    
                    # Escribimos a MP3 con bitrate bajo (32k) y mono (1 canal)
                    # Esto reduce drásticamente el peso sin afectar mucho a Whisper (voz)
                    clip.write_audiofile(output_path, bitrate="32k", nbytes=2, codec='libmp3lame', logger=None)
                    clip.close()
                    
                    # Limpiamos el original pesado
                    os.remove(tmp_input_path)
                    
                    # Verificamos nuevo tamaño
                    new_size = os.path.getsize(output_path) / (1024 * 1024)
                    if new_size > 25.0:
                        st.warning(f"⚠️ El archivo comprimido aún pesa {new_size:.1f}MB. Podría fallar si supera 25MB.")
                    
                    return output_path
                    
                except Exception as e:
                    st.error(f"Error en conversión: {e}")
                    return None
        
        # Si es audio pequeño (<25MB), lo devolvemos tal cual
        return tmp_input_path

    except Exception as e:
        st.error(f"Error general en archivo: {e}")
        return None

# --- TRANSCRIPCIÓN ---
def transcribe_audio_verbose(client, file_path, model_name):
    try:
        # Verificación final de tamaño antes de enviar
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"❌ El archivo ({size_mb:.1f}MB) supera el límite de 25MB de la API. Intenta cortar el audio.")
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
        st.error(f"Error API: {e}")
        return None, None

# --- CORRECCIÓN LIMPIA ---
def correct_text_with_llama(client, raw_text):
    system_prompt = (
        "Corrige ortografía y tildes. "
        "REGLAS: NO saludos. NO intros. NO resúmenes. "
        "Devuelve SOLO el texto corregido idéntico en contenido."
    )
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_text}],
            temperature=0.0
        )
        res = completion.choices[0].message.content
        # Limpieza extra de seguridad
        clean_res = res.replace("Aquí está el texto corregido:", "").replace("Texto corregido:", "").strip()
        return clean_res
    except:
        return raw_text

# --- BÚSQUEDA ---
def search_in_segments(query, segments):
    results = []
    if not query or not segments: return results
    q = query.lower()
    for i, seg in enumerate(segments):
        if q in seg['text'].lower():
            s_idx = max(0, i - 2)
            e_idx = min(len(segments), i + 3)
            prev = " ".join([s['text'] for s in segments[s_idx:i]])
            nxt = " ".join([s['text'] for s in segments[i+1:e_idx]])
            results.append({
                "start": seg['start'],
                "formatted": format_timestamp(seg['start']),
                "match": seg['text'],
                "prev": prev,
                "next": nxt
            })
    return results

# --- MAIN ---
def main_app():
    client = get_groq_client()
    if not client: st.stop()

    with st.sidebar:
        st.title("⚙️ Configuración")
        # OPCIÓN POR DEFECTO: TURBO (Primero en la lista)
        model_choice = st.selectbox(
            "Modelo", 
            options=["whisper-large-v3-turbo", "whisper-large-v3"],
            help="Turbo es más rápido. V3 es más preciso."
        )
        st.divider()
        if st.button("Salir"):
            st.session_state.clear()
            st.rerun()

    st.title("🎙️ Transcriptor Pro")

    uploaded_file = st.file_uploader("Subir archivo", type=["mp3", "mp4", "wav", "m4a"])

    if uploaded_file:
        if st.button("🚀 Procesar", type="primary"):
            with st.status("Procesando...", expanded=True) as status:
                st.write("🔍 Analizando y optimizando archivo...")
                
                # LLAMADA A LA NUEVA FUNCIÓN DE PROCESAMIENTO
                final_path = process_audio_file(uploaded_file)
                st.session_state.audio_path = final_path
                
                if final_path:
                    st.write(f"🎧 Transcribiendo con {model_choice}...")
                    raw, segs = transcribe_audio_verbose(client, final_path, model_choice)
                    
                    if raw and segs:
                        st.write("✨ Limpiando texto...")
                        fixed = correct_text_with_llama(client, raw)
                        st.session_state.transcript_text = fixed
                        st.session_state.transcript_segments = segs
                        st.session_state.audio_start_time = 0
                        status.update(label="¡Listo!", state="complete", expanded=False)
                    else: status.update(label="Error Transcripción", state="error")
                else: status.update(label="Error Archivo", state="error")

    # Reproductor persistente
    if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
        st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

    if st.session_state.transcript_text:
        tab_txt, tab_chat = st.tabs(["📝 Transcripción", "💬 Chat"])

        with tab_txt:
            st.markdown("### 🔍 Búsqueda")
            c1, c2 = st.columns([5,1])
            with c1: q = st.text_input("Buscar:", key="search_query_val")
            with c2: 
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                st.button("Limpiar", on_click=clear_search)

            if q:
                res = search_in_segments(q, st.session_state.transcript_segments)
                if res:
                    st.success(f"{len(res)} coincidencias")
                    for i, r in enumerate(res):
                        with st.container():
                            b_col, t_col = st.columns([1, 8])
                            with b_col:
                                if st.button(f"▶ {r['formatted']}", key=f"j_{i}"):
                                    st.session_state.audio_start_time = int(r['start'])
                                    st.rerun()
                            with t_col:
                                st.markdown(
                                    f"<div class='search-result'><span style='color:#888'>...{r['prev']}</span> "
                                    f"<span class='highlight'>{r['match']}</span> "
                                    f"<span style='color:#888'>{r['next']}...</span></div>", 
                                    unsafe_allow_html=True
                                )
                else: st.warning("Sin resultados")
                st.divider()

            st.text_area("Texto", value=st.session_state.transcript_text, height=500)
            st.download_button("Descargar", st.session_state.transcript_text, "transcripcion.txt")

        with tab_chat:
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.markdown(m["content"])
            
            if p := st.chat_input("Pregunta..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.markdown(p)
                with st.chat_message("assistant"):
                    holder = st.empty()
                    full = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[
                                {"role": "system", "content": f"Responde SOLO basado en:\n{st.session_state.transcript_text}"},
                                {"role": "user", "content": p}
                            ], stream=True
                        )
                        for chunk in stream:
                            if chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                holder.markdown(full + "▌")
                        holder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e: st.error(str(e))

if __name__ == "__main__":
    if check_password(): main_app()
