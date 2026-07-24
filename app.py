import streamlit as st
import streamlit.components.v1 as components
import os
import tempfile
import unicodedata
import shutil
import subprocess
import re
import time
import json
from datetime import datetime
from difflib import SequenceMatcher
from groq import Groq

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="Monitor de Noticias — Transcriptor IA",
    page_icon="🟧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — Tema Claro Premium + Naranja y Carbón
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --bg: #f8fafc;
        --surface: #ffffff;
        --surface-alt: #f1f5f9;
        --surface-border: #e2e8f0;
        --border-strong: #cbd5e1;
        --text-primary: #0f172a;
        --text-secondary: #475569;
        --text-muted: #94a3b8;
        
        /* Naranja + Carbón */
        --accent: #ea580c;
        --accent-bright: #f97316;
        --accent-dark: #c2410c;
        --accent-soft: rgba(249, 115, 22, 0.12);
        --accent-border: rgba(249, 115, 22, 0.35);
        
        --black: #0f172a;
        --amber: #d97706;
        --amber-soft: #fef3c7;
        
        --radius: 12px;
        --radius-sm: 8px;
        --shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.08);
        --shadow-md: 0 4px 12px -2px rgba(15, 23, 42, 0.1);
        --mono: 'JetBrains Mono', monospace;
        --sans: 'IBM Plex Sans', -apple-system, sans-serif;
    }

    .main > div:first-child { padding-top: 0 !important; }
    .block-container { padding-top: 0.5rem !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text-primary) !important; }

    body, p, div, h1, h2, h3, h4, h5, h6, li, td, th,
    .stMarkdown, .stText, [data-testid="stMarkdownContainer"],
    .stButton > button, .stSelectbox, .stTextInput input, .stTextArea textarea {
        font-family: var(--sans) !important;
        color: var(--text-primary) !important;
    }
    code, pre, .mono, [data-testid="stCode"] {
        font-family: var(--mono) !important;
    }

    .main .block-container {
        padding: 0.8rem 1.8rem 1.5rem 1.8rem;
        max-width: 1650px;
    }

    /* Inputs y Selectores */
    .stTextInput > div > div, .stSelectbox > div > div, textarea {
        background-color: var(--surface) !important;
        border: 1px solid var(--surface-border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    .stTextInput input { font-size: 0.9rem !important; color: var(--text-primary) !important; }
    .stTextInput > div > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-soft) !important;
    }

    /* Reproductor de Audio */
    audio {
        border-radius: var(--radius-sm);
        width: 100%;
        margin: 4px 0;
    }

    /* ---------- LOGIN ---------- */
    .login-shell {
        border: 1px solid var(--surface-border); border-top: 4px solid var(--accent);
        border-radius: var(--radius); background: var(--surface);
        padding: 36px; box-shadow: var(--shadow-md);
    }
    .login-badge {
        font-family: var(--mono); font-size: 0.75rem; color: var(--accent);
        letter-spacing: 0.08em; font-weight: 700; text-transform: uppercase;
        margin-bottom: 8px;
    }
    .login-title { font-size: 1.5rem; font-weight: 700; color: var(--black); margin: 0 0 6px 0; }
    .login-subtitle { font-size: 0.88rem; color: var(--text-secondary); margin: 0 0 22px 0; }

    /* ---------- HEADER EN TEMA CLARO ---------- */
    .news-header {
        display: flex; align-items: center; justify-content: space-between;
        background: var(--surface); border: 1px solid var(--surface-border);
        border-top: 4px solid var(--accent-bright);
        border-radius: var(--radius) var(--radius) 0 0;
        padding: 14px 22px; box-shadow: var(--shadow-sm);
    }
    .news-title-tag {
        display: inline-flex; align-items: center; gap: 12px;
        font-family: var(--sans); font-weight: 700; font-size: 1.05rem; color: var(--text-primary);
    }
    .news-tag {
        font-family: var(--mono); font-size: 0.72rem; font-weight: 700;
        color: var(--accent-dark); background: var(--accent-soft);
        border: 1px solid var(--accent-border); border-radius: 4px; padding: 3px 10px;
    }
    .creator-badge {
        font-family: var(--sans); font-size: 0.82rem; font-weight: 700;
        color: var(--black); background: var(--surface-alt); padding: 5px 14px; border-radius: 20px;
        border: 1px solid var(--surface-border);
    }

    .news-body {
        border: 1px solid var(--surface-border); border-top: none;
        background: var(--surface); border-radius: 0 0 var(--radius) var(--radius);
        padding: 22px; margin-bottom: 16px; box-shadow: var(--shadow-sm);
    }

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--surface-border) !important; }
    .side-comment {
        font-family: var(--mono); font-size: 0.72rem; color: var(--accent);
        text-transform: uppercase; margin: 18px 0 8px 0; letter-spacing: 0.06em; font-weight: 700;
    }
    .side-comment.first { margin-top: 4px; }

    /* ---------- STATUS BAR ---------- */
    .status-bar {
        display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0 14px 0;
    }
    .status-item {
        font-family: var(--mono); font-size: 0.75rem; color: var(--text-secondary);
        padding: 8px 12px; border: 1px solid var(--surface-border);
        background: var(--surface-alt); border-radius: var(--radius-sm); white-space: nowrap;
    }
    .status-item strong { color: var(--black); font-weight: 700; }
    .status-item.ok { background: var(--accent-soft); color: var(--accent-dark); border-color: var(--accent-border); }

    /* ---------- HEADERS DE PANEL ---------- */
    .panel-header {
        font-family: var(--sans); font-size: 0.88rem; font-weight: 700;
        letter-spacing: 0.02em; color: var(--black); text-transform: uppercase;
        margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid var(--black);
        display: flex; justify-content: space-between; align-items: center;
    }

    /* ---------- LISTA DE SEGMENTOS INTERACTIVOS (IZQUIERDA) ---------- */
    .code-panel {
        border: 1px solid var(--surface-border); border-radius: var(--radius-sm);
        background: var(--surface); max-height: 560px; overflow-y: auto;
    }
    .code-line {
        display: grid; grid-template-columns: 28px 62px 1fr;
        gap: 8px; align-items: baseline;
        padding: 9px 12px; cursor: pointer;
        border-left: 3px solid transparent;
        transition: all 0.12s ease;
        border-bottom: 1px solid var(--surface-alt);
    }
    .code-line:hover { background: var(--surface-alt); border-left-color: var(--accent-bright); }
    .code-line.active {
        background: var(--accent-soft); border-left: 4px solid var(--accent-bright);
    }
    .code-line .line-no {
        font-family: var(--mono); font-size: 0.7rem; color: var(--text-muted); text-align: right; user-select: none;
    }
    .code-line .line-time {
        font-family: var(--mono); font-size: 0.7rem; color: var(--accent-dark);
        background: var(--accent-soft); border: 1px solid var(--accent-border);
        border-radius: 4px; padding: 2px 6px; text-align: center; white-space: nowrap; font-weight: 700;
    }
    .code-line.active .line-time { background: var(--accent-bright); color: #fff; }
    .code-line .line-text {
        font-family: var(--sans); font-size: 0.9rem; line-height: 1.55; color: var(--text-primary);
    }

    /* ---------- LECTOR DE TRANSCRIPCIÓN COMPLETA (DERECHA - TEXTO PURO) ---------- */
    .news-reader-card {
        border: 1px solid var(--surface-border); border-radius: var(--radius-sm);
        background: var(--surface); max-height: 560px; overflow-y: auto;
        padding: 24px 28px; font-family: var(--sans); font-size: 1.02rem;
        line-height: 1.9; color: var(--text-primary);
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.01);
    }
    .full-text-span {
        padding: 2px 4px; border-radius: 4px; transition: background 0.3s ease;
    }
    .full-text-span.active-full-highlight {
        background: var(--accent-soft) !important;
        border-bottom: 2px solid var(--accent-bright);
    }

    /* ---------- RESALTADOS ---------- */
    mark.mk-exact {
        background: #ffedd5; color: #9a3412; padding: 2px 6px; border-radius: 4px;
        font-weight: 700; border-bottom: 2px solid var(--accent-bright);
    }
    mark.mk-similar {
        background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px;
        font-weight: 700; border: 1px dashed var(--amber);
    }

    /* ---------- TARJETAS DE ANÁLISIS ---------- */
    .analysis-card {
        background: var(--surface); border: 1px solid var(--surface-border);
        border-radius: var(--radius); padding: 20px; margin-bottom: 16px;
        box-shadow: var(--shadow-sm);
    }
    .analysis-headline {
        font-size: 1.3rem; font-weight: 700; color: var(--black); margin: 0 0 6px 0;
        line-height: 1.35;
    }
    .analysis-subheadline {
        font-size: 0.92rem; color: var(--text-secondary); font-style: italic; margin-bottom: 16px;
    }
    .bullet-point {
        display: flex; gap: 8px; margin-bottom: 8px; font-size: 0.92rem; color: var(--text-primary);
    }
    .bullet-icon { color: var(--accent-bright); font-weight: bold; }

    /* Badges de Entidades */
    .entity-tag {
        display: inline-block; font-family: var(--sans); font-size: 0.8rem; font-weight: 600;
        padding: 4px 10px; border-radius: 20px; margin: 3px 4px 3px 0;
    }
    .entity-person { background: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }
    .entity-org { background: #f1f5f9; color: #0f172a; border: 1px solid #cbd5e1; }
    .entity-loc { background: #fef3c7; color: #78350f; border: 1px solid #fde68a; }
    .entity-topic { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }

    .soundbite-box {
        background: var(--surface-alt); border-left: 4px solid var(--accent-bright);
        padding: 12px 16px; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
        font-style: italic; margin-bottom: 10px; font-size: 0.92rem; color: var(--black);
    }

    /* Botones Streamlit */
    .stButton > button {
        border-radius: var(--radius-sm) !important; font-weight: 600 !important;
        font-size: 0.85rem !important; border-color: var(--surface-border) !important;
        background-color: var(--surface) !important; color: var(--black) !important;
        box-shadow: var(--shadow-sm) !important;
    }
    .stButton > button:hover {
        border-color: var(--black) !important; background-color: var(--surface-alt) !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent-bright) !important; border: none !important; color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover { background: var(--accent-dark) !important; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# JAVASCRIPT: Auto-Scroll a la mención buscada (Ctrl+F behavior)
# ============================================================
def inject_scroll_and_audio_js():
    components.html("""
    <script>
    window.jumpToSegmentAndScroll = function(seconds, idx) {
        // 1. Jump audio player
        if (seconds !== undefined && seconds !== null) {
            const audios = window.parent.document.querySelectorAll('audio');
            if (audios.length > 0) {
                const audio = audios[0];
                audio.currentTime = seconds;
                if (audio.paused) {
                    audio.play().catch(function(e) { console.log('Autoplay blocked:', e); });
                }
            }
        }
        // 2. Scroll clean text in right panel (news-reader-card)
        if (idx !== undefined && idx !== null) {
            const targetEl = window.parent.document.getElementById('full-seg-' + idx);
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const allSpans = window.parent.document.querySelectorAll('.full-text-span');
                allSpans.forEach(el => el.classList.remove('active-full-highlight'));
                targetEl.classList.add('active-full-highlight');
            }
        }
    };

    window.autoScrollToFirstMatch = function(idx) {
        setTimeout(function() {
            const targetEl = window.parent.document.getElementById('full-seg-' + idx);
            if (targetEl) {
                targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const allSpans = window.parent.document.querySelectorAll('.full-text-span');
                allSpans.forEach(el => el.classList.remove('active-full-highlight'));
                targetEl.classList.add('active-full-highlight');
            }
        }, 200);
    };

    window.parent.document.addEventListener('click', function(e) {
        const btn = e.target.closest('.code-line, .full-text-span');
        if (btn) {
            const seconds = parseFloat(btn.getAttribute('data-time'));
            const idx = btn.getAttribute('data-idx');
            if (!isNaN(seconds) || idx !== null) {
                e.preventDefault(); e.stopPropagation();
                window.jumpToSegmentAndScroll(seconds, idx);
            }
        }
    }, true);
    </script>
    """, height=0)


def trigger_autoscroll_script(idx):
    components.html(f"""
    <script>
    if (window.parent.autoScrollToFirstMatch) {{
        window.parent.autoScrollToFirstMatch({idx});
    }}
    </script>
    """, height=0)


# ============================================================
# SESSION STATE
# ============================================================
DEFAULTS = {
    "authenticated": False,
    "pydub_available": None,
    "transcript_text": None,
    "transcript_segments": None,
    "corrected_segments": None,
    "raw_transcript": None,
    "audio_path": None,
    "audio_start_time": 0,
    "correction_applied": False,
    "uploaded_filename": None,
    "audio_duration_ms": 0,
    "coverage_pct": 100.0,
    "transcript_gaps": [],
    "chunks_used": 1,
    "active_segment_idx": -1,
    "custom_vocabulary": "",
    "search_query": "",
    "only_matches": False,
    "news_analysis": None,
    "ai_qa_history": [],
    "_audio_widget_key": 0,
}

for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

def reset_transcript_state():
    keep = {"authenticated", "pydub_available"}
    for k, v in DEFAULTS.items():
        if k not in keep:
            st.session_state[k] = v


# ============================================================
# PYDUB & UTILIDADES
# ============================================================
def check_pydub_ffmpeg():
    if st.session_state.pydub_available is not None:
        return st.session_state.pydub_available, ""
    try:
        from pydub import AudioSegment
    except ImportError:
        st.session_state.pydub_available = False; return False, "pydub no instalado"
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for c in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(c):
                ffmpeg_bin = c
                os.environ["PATH"] = os.path.dirname(c) + os.pathsep + os.environ.get("PATH", ""); break
    if not ffmpeg_bin:
        st.session_state.pydub_available = False; return False, "ffmpeg no en PATH"
    try:
        from pydub import AudioSegment
        _ = len(AudioSegment.silent(duration=100))
    except Exception as e:
        st.session_state.pydub_available = False; return False, f"pydub falla: {e}"
    st.session_state.pydub_available = True; return True, ""

def fmt_time(seconds):
    s = max(0, int(seconds)); h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def fmt_duration(seconds):
    s = max(0, int(seconds)); h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{sec}s"); return " ".join(parts)

def norm(text):
    if not text: return ""
    t = unicodedata.normalize('NFD', text)
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn').lower().strip()


# ============================================================
# AUTENTICACIÓN
# ============================================================
def check_password():
    if st.session_state.authenticated: return True
    def do_login():
        pwd = st.session_state.get("_pwd_input", "")
        if not pwd: return
        try:
            if pwd == st.secrets["general"]["app_password"]: st.session_state.authenticated = True
            else: st.session_state._login_error = "Contraseña incorrecta"
        except: st.session_state._login_error = "Error de autenticación"

    st.markdown("<div style='height:14vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown(
            '<div class="login-shell">'
            '<div class="login-badge">MONITOR PERIODÍSTICO</div>'
            '<p class="login-title">Plataforma de Noticias IA</p>'
            '<p class="login-subtitle">Ingresa la clave de acceso para continuar</p>'
            '</div>', unsafe_allow_html=True)
        st.write("")
        st.text_input("pwd", type="password", label_visibility="collapsed",
                      placeholder="Contraseña...", key="_pwd_input", on_change=do_login)
        st.button("Ingresar al sistema", use_container_width=True, type="primary", on_click=do_login)
        if st.session_state.get("_login_error"):
            st.error(st.session_state._login_error); st.session_state._login_error = None
    if st.session_state.authenticated: st.rerun()
    return False

def get_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: st.error("API Key no configurada"); return None


# ============================================================
# ANÁLISIS PERIODÍSTICO (GROQ LLM)
# ============================================================
def analyze_news_with_groq(client, full_text):
    system_prompt = """
    Eres un editor periodístico senior especializado en análisis de noticias y boletines informativos en español.
    Analiza la transcripción provista y genera una respuesta únicamente en formato JSON estricto con la siguiente estructura:
    {
      "titular": "Titular periodístico claro, informativo e impactante",
      "bajada": "Bajada o subtítulo explicativo de 1-2 oraciones",
      "resumen_ejecutivo": [
        "Punto clave 1 del reporte",
        "Punto clave 2 del reporte",
        "Punto clave 3 del reporte"
      ],
      "tono_editorial": "Informativo / Crítico / Urgente / Analítico / Oficial",
      "citas_destacadas": [
        "Cita o declaración textual más importante 1",
        "Cita o declaración textual más importante 2"
      ],
      "entidades": {
        "personas": ["Nombre de figura o vocero 1", "Nombre 2"],
        "organizaciones": ["Institución, empresa o ministerio 1"],
        "lugares": ["Ciudad, región o país 1"],
        "temas_clave": ["Tema o concepto clave 1", "Tema 2"]
      }
    }
    No incluyas código Markdown fuera del JSON.
    """
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TRANSCRIPCIÓN DE LA NOTICIA:\n{full_text[:12000]}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(r.choices[0].message.content)
    except:
        return None

def ask_news_assistant(client, full_text, query):
    system_prompt = """
    Eres un asistente periodístico de precisión. Tienes acceso a la transcripción exacta de un reporte o noticia.
    Responde la pregunta del usuario basándote EXCLUSIVAMENTE en la información mencionada en la transcripción.
    Sé conciso y directo.
    """
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"TRANSCRIPCIÓN:\n{full_text}\n\nPREGUNTA: {query}"}
            ],
            temperature=0.2
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error al procesar la consulta: {e}"


# ============================================================
# TRANSCRIPCIÓN Y AUDIO
# ============================================================
def save_uploaded(f):
    try:
        safe = "".join(c for c in f.name if c.isalnum() or c in "._-") or "audio.mp3"
        path = os.path.join(tempfile.gettempdir(), f"up_{safe}")
        with open(path, "wb") as fp: fp.write(f.getbuffer())
        return path
    except: return None

def convert_to_mp3(input_path, status_writer=None):
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for c in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(c): ffmpeg_bin = c; break
    if not ffmpeg_bin: return input_path, False
    out_path = input_path.rsplit(".", 1)[0] + "_norm.mp3"
    if status_writer: status_writer.write("Normalizando calidad de audio de noticias...")
    cmd = [ffmpeg_bin, "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame",
           "-ac", "1", "-ar", "16000", "-b:a", "128k",
           "-af", "highpass=f=80,lowpass=f=8000,afftdn=nr=10,dynaudnorm,aresample=16000",
           out_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode != 0: return input_path, False
        return out_path, True
    except: return input_path, False

def get_audio_info(path):
    ok, _ = check_pydub_ffmpeg()
    if not ok: return None, None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(path); return len(audio), audio
    except: return None, None

def transcribe_single(client, path, model, prompt=None):
    try:
        with open(path, "rb") as f: file_data = f.read()
        kwargs = {"file": (os.path.basename(path), file_data), "model": model,
                  "response_format": "verbose_json", "language": "es", "temperature": 0.0}
        
        news_context = "Noticias, prensa, boletín informativo, radio, televisión, declaraciones, vocero, fiscalía, ministerio, reporte periodístico."
        kwargs["prompt"] = f"{news_context} {prompt}" if prompt else news_context
        
        t = client.audio.transcriptions.create(**kwargs)
        segments = []
        if t.segments:
            for seg in t.segments:
                s = seg.get("start", 0) if isinstance(seg, dict) else getattr(seg, "start", 0)
                e = seg.get("end", 0) if isinstance(seg, dict) else getattr(seg, "end", 0)
                tx = seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")
                if str(tx).strip(): segments.append({"start": float(s), "end": float(e), "text": str(tx).strip()})
        return t.text or "", segments, None
    except Exception as e:
        return None, None, str(e)

def correct_spanish_news_style(client, raw_text, segments, custom_vocab=""):
    system_prompt = f"""
    Eres un corrector de estilo periodístico experto en español (agencias EFE / AP).
    Tu tarea es corregir la transcripción de una noticia:
    1. Asegurar la ortografía exacta, mayúsculas en instituciones/nombres y acentuación.
    2. Formatear adecuadamente números, porcentajes y divisas (ej: "5 millones de dólares", "12%").
    3. Respetar estrictamente el vocabulario clave provisto: {custom_vocab}
    4. NO agregues explicaciones. Devuelve únicamente el texto corregido.
    """
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text}
            ],
            temperature=0.0
        )
        corrected = r.choices[0].message.content.strip()
        return corrected, realign_segments(corrected, segments)
    except:
        return raw_text, segments

def realign_segments(corrected_text, original_segments):
    words = corrected_text.split()
    total_orig = sum(len(s["text"].split()) for s in original_segments)
    if total_orig == 0: return original_segments
    aligned, idx = [], 0
    for i, seg in enumerate(original_segments):
        wc = len(seg["text"].split())
        if i == len(original_segments) - 1: chunk = words[idx:]
        else: take = max(1, round((wc / total_orig) * len(words))); chunk = words[idx:idx+take]; idx += len(chunk)
        aligned.append({"start": seg["start"], "end": seg["end"], "text": " ".join(chunk) if chunk else seg["text"]})
    return aligned


# ============================================================
# BÚSQUEDA Y MATCHING (EXACTO Y SIMILAR)
# ============================================================
_ACCENT_MAP = {'a': '[aáàâä]', 'e': '[eéèêë]', 'i': '[iíìîï]', 'o': '[oóòôö]', 'u': '[uúùûü]', 'n': '[nñ]'}

def compile_query_pattern(query):
    query = (query or "").strip()
    if not query: return None
    words = [w for w in re.split(r'\s+', query) if w]
    if not words: return None
    parts = [''.join(_ACCENT_MAP.get(c.lower(), re.escape(c)) for c in w) for w in words]
    try: return re.compile(r'\s+'.join(parts), re.IGNORECASE)
    except: return None

def determine_search_mode(query, segments):
    pattern = compile_query_pattern(query)
    if pattern:
        for seg in segments:
            if pattern.search(seg.get("text", "")): return pattern, "exacta"
    return pattern, "similar"

def _fuzzy_highlight(text, q_words, fuzzy_thresh):
    found = False; result = text; seen = set()
    for tok in re.findall(r"\S+", text):
        core = re.sub(r'^\W+|\W+$', '', tok)
        wn = norm(core)
        if not wn or len(wn) < 3 or tok in seen: continue
        best = max((SequenceMatcher(None, qw, wn).ratio() for qw in q_words if len(qw) >= 3), default=0.0)
        if best >= fuzzy_thresh:
            seen.add(tok); found = True
            result = result.replace(tok, f"<mark class='mk-similar'>{tok}</mark>", 1)
    return found, result

def highlight_and_check(text, pattern, q_words, fuzzy_thresh, mode):
    if mode == "exacta":
        if pattern and pattern.search(text):
            return True, pattern.sub(lambda m: f"<mark class='mk-exact'>{m.group()}</mark>", text)
        return False, text
    elif mode == "similar":
        return _fuzzy_highlight(text, q_words, fuzzy_thresh)
    return False, text


# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def process_audio(client, uploaded, model, do_correct, custom_vocab=""):
    reset_transcript_state()
    with st.status("Procesando audio de noticia...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path: st.error("Error al guardar archivo"); return False
        st.session_state.uploaded_filename = uploaded.name
        st.session_state.custom_vocabulary = custom_vocab
        
        converted_path, _ = convert_to_mp3(path, status_writer=status)
        st.session_state.audio_path = path
        
        status.write("Transcribiendo noticia...")
        full_text, segments, err = transcribe_single(client, converted_path, model, prompt=custom_vocab)
        if err or not full_text: st.error("Error en transcripción"); return False
        
        dur_ms, _ = get_audio_info(converted_path)
        
        if do_correct:
            status.write("Aplicando corrección de estilo periodístico...")
            full_text, segments = correct_spanish_news_style(client, full_text, segments, custom_vocab)
            st.session_state.correction_applied = True
            
        status.write("Generando análisis periodístico inteligente...")
        news_analysis = analyze_news_with_groq(client, full_text)
        
        st.session_state.transcript_text = full_text
        st.session_state.corrected_segments = segments
        st.session_state.audio_duration_ms = dur_ms or 0
        st.session_state.news_analysis = news_analysis
        
        status.update(label="Noticia procesada y analizada correctamente", state="complete", expanded=False)
    return True


# ============================================================
# APP PRINCIPAL
# ============================================================
def main_app():
    client = get_client()
    if not client: st.stop()
    pydub_ok, pydub_msg = check_pydub_ffmpeg()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("<div class='side-comment first'>CONFIGURACIÓN PERIODÍSTICA</div>", unsafe_allow_html=True)
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: "Large V3 (Máxima precisión)" if "turbo" not in x else "Large V3 Turbo (Rápido)")
        do_correct = st.toggle("Corrección periodística IA", value=True)

        st.markdown("<div class='side-comment'>VOCABULARIO CLAVE / NOMBRES</div>", unsafe_allow_html=True)
        st.caption("Escribe nombres propios, candidatos o instituciones para garantizar precisión 100%.")
        custom_vocab = st.text_area("Vocabulario", value=st.session_state.get("custom_vocabulary", ""),
            placeholder="Ministerio de Economía\nComfenalco\nEcopetrol", height=100, label_visibility="collapsed")

        st.markdown("<div class='side-comment'>AJUSTES DE BÚSQUEDA</div>", unsafe_allow_html=True)
        fuzzy_t = st.slider("Tolerancia a variaciones/typos", 0.55, 0.95, 0.72, 0.02)

        st.markdown("---")
        if st.session_state.transcript_text:
            if st.button("➕ Subir otro audio", use_container_width=True, type="primary"):
                reset_transcript_state()
                st.rerun()
        if st.button("Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    # ── HEADER SUPERIOR (TEMA CLARO CORREGIDO) ──
    fname_display = st.session_state.uploaded_filename or "Sin archivo"
    st.markdown(f"""
    <div class="news-header">
        <div class="news-title-tag">
            <span>🎙Transcriptor Pro✍</span>
            <span class="news-tag">{fname_display}</span>
        </div>
        <div>
            <span class="creator-badge">Creado por Johnathan Cortés</span>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="news-body">', unsafe_allow_html=True)

    # ── CARGA DE AUDIO NUEVO ──
    if not st.session_state.transcript_text:
        _, col_c, _ = st.columns([1, 2.2, 1])
        with col_c:
            st.markdown(
                '<div style="text-align:center;padding:44px 24px;border:2px dashed var(--border-strong);border-radius:var(--radius);background:var(--surface);">'
                '<div style="font-size:2.8rem;margin-bottom:12px;">🎙️</div>'
                '<div style="font-weight:700;font-size:1.2rem;margin-bottom:6px;color:var(--black);">Subir Noticia o Reporte de Audio</div>'
                '<div style="font-size:0.88rem;color:var(--text-secondary);margin-bottom:24px;">Selecciona tu archivo de audio (MP3, WAV, M4A, OGG) para procesarlo.</div>'
                '</div>', unsafe_allow_html=True)
            st.write("")
            uploaded = st.file_uploader("Subir audio", type=["mp3","wav","m4a","ogg","mp4"], label_visibility="collapsed")
            if uploaded and st.button("▶ Transcribir y Analizar Noticia", type="primary", use_container_width=True):
                if process_audio(client, uploaded, model, do_correct, custom_vocab=custom_vocab): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════════
    # VISTA DE NOTICIA PROCESADA
    # ══════════════════════════════════════════════
    txt = st.session_state.transcript_text or ""
    segs = st.session_state.corrected_segments or []
    n_words = len(txt.split())
    duration = max((float(s.get("end", 0)) for s in segs), default=0)
    wpm = round(n_words / max(duration/60, 1)) if duration > 0 else 0
    analysis = st.session_state.news_analysis

    # ── BARRA PRINCIPAL Y BOTÓN DE NUEVO AUDIO ──
    col_play, col_met, col_new = st.columns([0.4, 0.42, 0.18])
    with col_play:
        if st.session_state.audio_path:
            st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)
        inject_scroll_and_audio_js()

    with col_met:
        st.markdown(
            '<div class="status-bar">'
            f'<span class="status-item">Duración: <strong>{fmt_duration(duration)}</strong></span>'
            f'<span class="status-item">Palabras: <strong>{n_words:,}</strong></span>'
            f'<span class="status-item ok">Prensa EFE/AP</span>'
            '</div>', unsafe_allow_html=True
        )

    with col_new:
        if st.button("➕ Subir otro audio", use_container_width=True, type="primary"):
            reset_transcript_state()
            st.rerun()

    st.write("")

    # ── DOS COLUMNAS DE TRABAJO ──
    left_col, right_col = st.columns([0.45, 0.55], gap="large")

    # ── COLUMNA IZQUIERDA: BUSCADOR Y SEGMENTOS CON TIMESTAMPS ──
    with left_col:
        st.markdown("<div class='panel-header'><span>Buscador y Segmentación de Audio</span></div>", unsafe_allow_html=True)
        
        sb1, sb2 = st.columns([3, 1.2])
        with sb1:
            query = st.text_input("Buscador de términos clave", placeholder="Buscar palabras clave...",
                                  label_visibility="collapsed", value=st.session_state.search_query, key="search_box")
        with sb2:
            only_matches = st.toggle("Solo hallazgos", value=st.session_state.only_matches, key="toggle_only_matches")

        if query != st.session_state.search_query:
            st.session_state.search_query = query
            st.session_state.active_segment_idx = -1

        q_words = [w for w in norm(query).split() if w]
        left_lines_html = []
        
        # Mapeo de texto corrido (SIN TIMESTAMPS) para la derecha
        full_text_spans = []
        first_match_idx = None

        if query:
            pattern, mode = determine_search_mode(query, segs)
            match_count = 0

            for i, seg in enumerate(segs):
                start_sec = float(seg.get("start", 0))
                ts = fmt_time(start_sec)
                text_content = seg.get("text", "")
                
                matched, html_formatted = highlight_and_check(text_content, pattern, q_words, fuzzy_t, mode)
                if matched:
                    match_count += 1
                    if first_match_idx is None:
                        first_match_idx = i
                
                if matched or not only_matches:
                    left_lines_html.append(
                        f"<div class='code-line' data-time='{start_sec}' data-idx='{i}'>"
                        f"<span class='line-no'>{i+1}</span>"
                        f"<span class='line-time'>{ts}</span>"
                        f"<span class='line-text'>{html_formatted if matched else text_content}</span></div>"
                    )
                
                # Panel derecho: SOLO TEXTO PURO (Span con ID para salto tipo Ctrl+F)
                full_text_spans.append(
                    f"<span class='full-text-span' id='full-seg-{i}' data-time='{start_sec}' data-idx='{i}'>"
                    f"{html_formatted if matched else text_content}</span> "
                )

            if mode == "similar":
                st.caption(f"🔍 Mostrando variaciones/términos similares para: **{query}** ({match_count} hallazgos)")
            else:
                st.caption(f"🎯 Busqueda exacta para: **{query}** ({match_count} hallazgos)")
        else:
            for i, seg in enumerate(segs):
                start_sec = float(seg.get("start", 0))
                ts = fmt_time(start_sec)
                text_content = seg.get("text", "")
                
                left_lines_html.append(
                    f"<div class='code-line' data-time='{start_sec}' data-idx='{i}'>"
                    f"<span class='line-no'>{i+1}</span>"
                    f"<span class='line-time'>{ts}</span>"
                    f"<span class='line-text'>{text_content}</span></div>"
                )
                
                # Panel derecho: SOLO TEXTO PURO (Sin botones ni tiempos)
                full_text_spans.append(
                    f"<span class='full-text-span' id='full-seg-{i}' data-time='{start_sec}' data-idx='{i}'>"
                    f"{text_content}</span> "
                )

        if left_lines_html:
            st.markdown(f"<div class='code-panel'>{''.join(left_lines_html)}</div>", unsafe_allow_html=True)
        else:
            st.info(f"Sin hallazgos para '{query}'")

        # Auto-scroll en la transcripción completa a la primera mención
        if first_match_idx is not None:
            trigger_autoscroll_script(first_match_idx)


    # ── COLUMNA DERECHA: TRANSCRIPCIÓN COMPLETA (SOLO TEXTO) + PESTAÑAS ──
    with right_col:
        tab_text, tab_analysis, tab_entities, tab_qa = st.tabs([
            "📰 Transcripción Completa (Texto Limpio)",
            "⚡ Análisis IA Periodístico",
            "🏷️ Entidades Extraídas",
            "💬 Asistente IA"
        ])

        # TAB 1: TRANSCRIPCIÓN COMPLETA (100% TEXTO PURO)
        with tab_text:
            st.markdown(
                f'<div class="news-reader-card">'
                f'{"".join(full_text_spans)}'
                f'</div>', unsafe_allow_html=True
            )
            st.write("")
            st.download_button(
                label="Descargar noticia completa (.txt)",
                data=txt,
                file_name=f"{fname_display}_transcripcion.txt",
                mime="text/plain",
                use_container_width=True
            )

        # TAB 2: ANÁLISIS AUTOMÁTICO
        with tab_analysis:
            if analysis:
                st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="analysis-headline">{analysis.get("titular", "Sin titular")}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="analysis-subheadline">{analysis.get("bajada", "")}</div>', unsafe_allow_html=True)
                
                st.markdown("**📌 Puntos Clave del Reporte:**")
                for bp in analysis.get("resumen_ejecutivo", []):
                    st.markdown(f'<div class="bullet-point"><span class="bullet-icon">•</span><span>{bp}</span></div>', unsafe_allow_html=True)
                
                st.write("")
                st.markdown(f"**Tono Editorial:** `{analysis.get('tono_editorial', 'Informativo')}`")
                st.markdown('</div>', unsafe_allow_html=True)

                if analysis.get("citas_destacadas"):
                    st.markdown("**💬 Declaraciones Textuales Relevantes:**")
                    for cita in analysis.get("citas_destacadas", []):
                        st.markdown(f'<div class="soundbite-box">"{cita}"</div>', unsafe_allow_html=True)
            else:
                st.info("No se pudo generar el análisis automático para esta noticia.")

        # TAB 3: ENTIDADES EXTRAÍDAS
        with tab_entities:
            if analysis and analysis.get("entidades"):
                ents = analysis.get("entidades", {})
                
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    st.markdown("**👤 Personas Mencionadas:**")
                    if ents.get("personas"):
                        for p in ents["personas"]: st.markdown(f'<span class="entity-tag entity-person">{p}</span>', unsafe_allow_html=True)
                    else: st.caption("Ninguna detectada")

                    st.markdown("<br>**🏛️ Organizaciones:**", unsafe_allow_html=True)
                    if ents.get("organizaciones"):
                        for o in ents["organizaciones"]: st.markdown(f'<span class="entity-tag entity-org">{o}</span>', unsafe_allow_html=True)
                    else: st.caption("Ninguna detectada")

                with col_e2:
                    st.markdown("**📍 Lugares / Ubicaciones:**")
                    if ents.get("lugares"):
                        for l in ents["lugares"]: st.markdown(f'<span class="entity-tag entity-loc">{l}</span>', unsafe_allow_html=True)
                    else: st.caption("Ninguno detectado")

                    st.markdown("<br>**🏷️ Temas Clave:**", unsafe_allow_html=True)
                    if ents.get("temas_clave"):
                        for t in ents["temas_clave"]: st.markdown(f'<span class="entity-tag entity-topic">{t}</span>', unsafe_allow_html=True)
                    else: st.caption("Ninguno detectado")

        # TAB 4: ASISTENTE IA DE CONSULTA
        with tab_qa:
            st.caption("Consulta cualquier duda sobre el reporte de noticias:")
            user_q = st.text_input("Tu pregunta sobre la noticia:", placeholder="Ej: ¿Qué se dijo sobre la reforma o las cifras?")
            
            if st.button("Consultar con IA", type="primary") and user_q:
                with st.spinner("Buscando en la transcripción..."):
                    answer = ask_news_assistant(client, txt, user_q)
                    st.markdown(f"**Respuesta:**\n\n{answer}")

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    if check_password():
        main_app()
