import streamlit as st
import streamlit.components.v1 as components
import os
import tempfile
import unicodedata
import shutil
import subprocess
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from groq import Groq

# ============================================================
# CONFIGURACIÓN DE PÁGINA
# ============================================================
st.set_page_config(
    page_title="transcriptor.py",
    page_icon="🟧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — Estética Claude Code (Oscuro, Carbón, Naranja)
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --bg: #121212;
        --surface: #1a1a1a;
        --surface-alt: #242424;
        --surface-sunken: #0d0d0d;
        --border: #2e2e2e;
        --border-strong: #3d3d3d;
        --text: #e6e6e6;
        --text-secondary: #a0a0a0;
        --text-faint: #666666;
        --accent: #f97316;
        --accent-dark: #ea580c;
        --accent-soft: rgba(249, 115, 22, 0.12);
        --accent-border: rgba(249, 115, 22, 0.3);
        --amber: #f59e0b;
        --amber-soft: rgba(245, 158, 11, 0.12);
        --red: #ef4444;
        --red-soft: rgba(239, 68, 68, 0.12);
        --radius: 8px;
        --radius-sm: 6px;
        --radius-xs: 4px;
        --shadow-sm: 0 2px 8px rgba(0,0,0,0.4);
        --mono: 'JetBrains Mono', ui-monospace, monospace;
        --sans: 'IBM Plex Sans', -apple-system, sans-serif;
    }

    /* Reset global Streamlit */
    .main > div:first-child { padding-top: 0 !important; }
    .block-container { padding-top: 0.4rem !important; }
    [data-testid="stAppViewContainer"] > section > div:first-child { padding-top: 0 !important; }
    div[data-testid="stVerticalBlock"] > div:first-child { margin-top: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text) !important; }

    body, p, div, h1, h2, h3, h4, h5, h6, li, td, th,
    .stMarkdown, .stText, [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"], [data-testid="stText"],
    .stButton > button, .stSelectbox, .stTextInput input,
    .stRadio label, .stCheckbox label, .stSlider {
        font-family: var(--sans) !important;
        color: var(--text) !important;
    }
    code, pre, .mono, [data-testid="stCode"] {
        font-family: var(--mono) !important;
    }

    .main .block-container {
        padding: 0.6rem 1.6rem 1.2rem 1.6rem;
        max-width: 1550px;
    }

    /* Input overrides */
    .stTextInput > div > div, .stSelectbox > div > div, textarea {
        background-color: var(--surface-alt) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text) !important;
    }
    .stTextInput input {
        color: var(--text) !important;
        font-family: var(--mono) !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div:focus-within {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-soft) !important;
    }

    /* Audio Player adjustment */
    audio {
        filter: invert(0.9) hue-rotate(180deg);
        border-radius: var(--radius-sm);
        width: 100%;
        margin: 4px 0 8px 0;
    }

    /* ---------- LOGIN ---------- */
    .login-shell {
        border: 1px solid var(--border); border-radius: var(--radius);
        background: var(--surface); padding: 32px; box-shadow: var(--shadow-sm);
    }
    .login-badge {
        font-family: var(--mono); font-size: 0.72rem; color: var(--accent);
        letter-spacing: 0.05em; font-weight: 600; text-transform: uppercase;
        margin-bottom: 8px;
    }
    .login-title { font-size: 1.3rem; font-weight: 600; color: #fff; margin: 0 0 6px 0; }
    .login-subtitle { font-size: 0.83rem; color: var(--text-secondary); margin: 0 0 22px 0; font-family: var(--mono); }

    /* ---------- WINDOW CHROME ---------- */
    .win-chrome {
        display: flex; align-items: center; justify-content: space-between;
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius) var(--radius) 0 0;
        padding: 10px 16px; margin-bottom: 0;
    }
    .win-dots { display: flex; gap: 7px; margin-right: 14px; }
    .win-dot { width: 11px; height: 11px; border-radius: 50%; }
    .win-dot.red { background: #ff5f56; }
    .win-dot.yellow { background: #ffbd2e; }
    .win-dot.green { background: #27c93f; }
    .win-tabbar { display: flex; align-items: center; gap: 8px; flex: 1; }
    .win-tab {
        display: inline-flex; align-items: center; gap: 6px;
        font-family: var(--mono); font-size: 0.76rem; color: var(--text-secondary);
        background: var(--surface-alt); border: 1px solid var(--border);
        border-radius: var(--radius-xs); padding: 4px 12px;
    }
    .win-tab.active { color: #fff; border-color: var(--border-strong); background: #2a2a2a; }
    .win-badge {
        font-family: var(--mono); font-size: 0.7rem; font-weight: 600;
        color: var(--accent); background: var(--accent-soft);
        border: 1px solid var(--accent-border); border-radius: 20px; padding: 2px 10px;
        display: inline-flex; align-items: center; gap: 6px;
    }
    .win-badge .pulse-dot {
        width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
    }
    .win-body {
        border: 1px solid var(--border); border-top: none;
        background: var(--surface-sunken); border-radius: 0 0 var(--radius) var(--radius);
        padding: 18px; margin-bottom: 14px;
    }

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
    .side-comment {
        font-family: var(--mono); font-size: 0.7rem; color: var(--accent);
        text-transform: uppercase; margin: 16px 0 8px 0; letter-spacing: 0.05em; font-weight: 600;
    }
    .side-comment.first { margin-top: 4px; }

    /* ---------- STATUS BAR ---------- */
    .status-bar {
        display: flex; flex-wrap: wrap; gap: 0;
        border: 1px solid var(--border); border-radius: var(--radius-sm);
        overflow: hidden; margin: 8px 0;
    }
    .status-item {
        font-family: var(--mono); font-size: 0.72rem; color: var(--text-secondary);
        padding: 7px 11px; border-right: 1px solid var(--border);
        background: var(--surface); flex: 1 1 auto; white-space: nowrap;
    }
    .status-item:last-child { border-right: none; }
    .status-item strong { color: #fff; font-weight: 600; }
    .status-item.ok { background: var(--accent-soft); color: var(--accent); }
    .status-item.warn { background: var(--amber-soft); color: var(--amber); }

    .coverage-bar-container {
        background: var(--surface-alt); border-radius: 6px; height: 16px;
        overflow: hidden; border: 1px solid var(--border); margin: 8px 0;
    }
    .coverage-bar-fill {
        height: 100%; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.65rem; font-weight: 700; color: #fff; font-family: var(--mono);
    }
    .coverage-ok { background: var(--accent-dark); }
    .coverage-warn { background: var(--amber); }
    .coverage-bad { background: var(--red); }

    /* ---------- PANEL HEADERS ---------- */
    .panel-header {
        font-family: var(--mono); font-size: 0.74rem; font-weight: 600;
        letter-spacing: 0.04em; color: var(--text-secondary); text-transform: uppercase;
        margin-bottom: 8px; padding-bottom: 6px;
        border-bottom: 1px solid var(--border);
        display: flex; justify-content: space-between; align-items: center;
    }
    .panel-header .n { color: var(--accent); font-weight: 700; }

    /* ---------- CODE PANEL (SEGMENTOS) ---------- */
    .code-panel {
        border: 1px solid var(--border); border-radius: var(--radius-sm);
        background: var(--surface); max-height: 560px; overflow-y: auto;
    }
    .code-panel::-webkit-scrollbar, .full-text-container::-webkit-scrollbar { width: 6px; }
    .code-panel::-webkit-scrollbar-thumb, .full-text-container::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }
    
    .code-line {
        display: grid; grid-template-columns: 30px 58px 1fr;
        gap: 8px; align-items: baseline;
        padding: 6px 10px; cursor: pointer;
        border-left: 2px solid transparent;
        transition: background 0.12s ease;
        border-bottom: 1px solid rgba(255,255,255,0.02);
    }
    .code-line:hover { background: var(--surface-alt); }
    .code-line.active {
        background: var(--accent-soft); border-left: 2px solid var(--accent);
    }
    .code-line .line-no {
        font-family: var(--mono); font-size: 0.68rem; color: var(--text-faint);
        text-align: right; user-select: none;
    }
    .code-line .line-time {
        font-family: var(--mono); font-size: 0.68rem; color: var(--accent);
        background: var(--accent-soft); border: 1px solid var(--accent-border);
        border-radius: 4px; padding: 1px 5px; text-align: center; white-space: nowrap;
    }
    .code-line.active .line-time { background: var(--accent); color: #fff; }
    .code-line .line-text {
        font-family: var(--sans); font-size: 0.84rem; line-height: 1.5; color: var(--text);
    }

    /* ---------- FULL TEXT CONTAINER (TEXTO COMPLETO) ---------- */
    .full-text-container {
        border: 1px solid var(--border); border-radius: var(--radius-sm);
        background: var(--surface); max-height: 640px; overflow-y: auto;
        padding: 22px 24px; font-family: var(--sans); font-size: 0.95rem;
        line-height: 1.8; color: #ececec; white-space: pre-wrap;
    }

    /* Resaltados */
    mark.mk-exact {
        background: var(--accent); color: #fff; padding: 2px 5px; border-radius: 3px;
        font-weight: 600; box-decoration-break: clone;
    }
    mark.mk-similar {
        background: var(--amber-soft); color: var(--amber); padding: 2px 5px; border-radius: 3px;
        font-weight: 600; border: 1px dashed var(--amber); box-decoration-break: clone;
    }

    .similar-banner {
        font-family: var(--mono); font-size: 0.74rem;
        background: var(--amber-soft); border: 1px solid rgba(245, 158, 11, 0.3); color: var(--amber);
        border-radius: var(--radius-sm); padding: 8px 12px; margin: 8px 0;
    }
    .no-results-box {
        text-align: left; padding: 12px 14px; color: var(--text-secondary);
        background: var(--surface); border-radius: var(--radius-sm);
        border: 1px dashed var(--border-strong); font-family: var(--mono); font-size: 0.78rem;
    }

    .empty-term {
        font-family: var(--mono); border: 1px dashed var(--border-strong);
        border-radius: var(--radius); padding: 48px 24px; text-align: center;
        color: var(--text-secondary); background: var(--surface);
    }
    .empty-term-title { font-family: var(--sans); font-size: 1.1rem; font-weight: 600; color: #fff; margin: 12px 0 4px 0; }
    .empty-term-sub { font-size: 0.82rem; color: var(--text-faint); margin-bottom: 20px; }

    .gap-row {
        font-family: var(--mono); font-size: 0.72rem; color: var(--text-secondary);
        padding: 6px 0; border-bottom: 1px dashed var(--border);
        display: flex; align-items: center; justify-content: space-between;
    }
    .gap-row:last-child { border-bottom: none; }

    /* Streamlit Buttons styling */
    .stButton > button {
        border-radius: var(--radius-xs) !important; font-weight: 500 !important;
        font-size: 0.82rem !important; border-color: var(--border) !important;
        background-color: var(--surface-alt) !important; color: var(--text) !important;
    }
    .stButton > button:hover {
        border-color: var(--border-strong) !important; background-color: #2e2e2e !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--accent) !important; border: none !important; color: #fff !important; font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover { background: var(--accent-dark) !important; }

    .ts-jump-btn {
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--mono); font-size: 0.68rem; font-weight: 600;
        color: var(--accent); background: var(--accent-soft);
        border: 1px solid var(--accent-border); border-radius: 4px; padding: 3px 8px;
        cursor: pointer; transition: all 0.15s ease; text-decoration: none;
    }
    .ts-jump-btn:hover { background: var(--accent); color: #fff; }
</style>
""", unsafe_allow_html=True)


# ============================================================
# JAVASCRIPT (salto de audio)
# ============================================================
def inject_audio_js():
    components.html("""
    <script>
    window.jumpToTime = function(seconds) {
        const audios = window.parent.document.querySelectorAll('audio');
        if (audios.length > 0) {
            const audio = audios[0];
            audio.currentTime = seconds;
            if (audio.paused) {
                audio.play().catch(function(e) { console.log('Autoplay blocked:', e); });
            }
        }
    };
    window.parent.document.addEventListener('click', function(e) {
        const btn = e.target.closest('.ts-jump-btn, .code-line');
        if (btn) {
            const seconds = parseFloat(btn.getAttribute('data-time'));
            if (!isNaN(seconds)) {
                e.preventDefault(); e.stopPropagation();
                window.jumpToTime(seconds);
            }
        }
    }, true);
    </script>
    """, height=0)


def make_ts_button_html(time_seconds, label=None):
    display = label or fmt_time(time_seconds)
    return (f"<button class='ts-jump-btn' data-time='{time_seconds}' "
            f"onclick='window.jumpToTime({time_seconds})' title='Ir a {display}'>▶ {display}</button>")


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
# PYDUB / FFMPEG
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


# ============================================================
# UTILIDADES
# ============================================================
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
# AUTH
# ============================================================
def check_password():
    if st.session_state.authenticated: return True
    def do_login():
        pwd = st.session_state.get("_pwd_input", "")
        if not pwd: return
        try:
            if pwd == st.secrets["general"]["app_password"]: st.session_state.authenticated = True
            else: st.session_state._login_error = "Contraseña incorrecta"
        except: st.session_state._login_error = "Error de configuración"

    st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown(
            '<div class="login-shell">'
            '<div class="login-badge">SISTEMA DE TRANSCRIPCIÓN</div>'
            '<p class="login-title">Transcriptor Pro</p>'
            '<p class="login-subtitle">Ingresa tu clave de acceso para ingresar</p>'
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
    except: st.error("API key no configurada"); return None


# ============================================================
# PROCESAMIENTO DE AUDIO
# ============================================================
def save_uploaded(f):
    try:
        safe = "".join(c for c in f.name if c.isalnum() or c in "._-") or "audio.mp3"
        path = os.path.join(tempfile.gettempdir(), f"up_{safe}")
        with open(path, "wb") as fp: fp.write(f.getbuffer())
        return path
    except: return None

def convert_to_mp3(input_path, status_writer=None):
    size_mb = os.path.getsize(input_path) / (1024 * 1024)
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for c in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(c): ffmpeg_bin = c; break
    if not ffmpeg_bin: return input_path, False
    out_path = input_path.rsplit(".", 1)[0] + "_norm.mp3"
    if status_writer: status_writer.write(f"Normalizando audio ({size_mb:.0f} MB)...")
    cmd = [ffmpeg_bin, "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame",
           "-ac", "1", "-ar", "16000", "-b:a", "128k",
           "-af", "highpass=f=80,lowpass=f=8000,afftdn=nr=10,dynaudnorm,aresample=16000",
           out_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode != 0:
            cmd2 = [ffmpeg_bin, "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame",
                    "-ac", "1", "-ar", "16000", "-b:a", "128k", "-af", "aresample=16000,volume=1.5", out_path]
            r2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if r2.returncode != 0: return input_path, False
        return out_path, True
    except:
        return input_path, False

def get_audio_info(path):
    ok, _ = check_pydub_ffmpeg()
    if not ok: return None, None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(path); return len(audio), audio
    except Exception as e: st.warning(f"⚠️ {e}"); return None, None

def split_audio_chunks(audio_segment, chunk_duration_ms=480_000, overlap_ms=35_000):
    total_ms = len(audio_segment); chunks = []
    if total_ms <= chunk_duration_ms:
        p = os.path.join(tempfile.gettempdir(), "chunk_0.mp3")
        audio_segment.export(p, format="mp3", bitrate="128k")
        return [{"path": p, "start_ms": 0, "end_ms": total_ms, "index": 0}]
    start, idx = 0, 0
    while start < total_ms:
        end = min(start + chunk_duration_ms, total_ms)
        chunk = audio_segment[start:end]
        p = os.path.join(tempfile.gettempdir(), f"chunk_{idx}.mp3")
        chunk.export(p, format="mp3", bitrate="128k")
        if os.path.getsize(p) / (1024*1024) > 24: chunk.export(p, format="mp3", bitrate="64k")
        chunks.append({"path": p, "start_ms": start, "end_ms": end, "index": idx})
        if end >= total_ms: break
        start = end - overlap_ms; idx += 1
    return chunks

def build_prompt_vocabulary(custom_vocab):
    if not custom_vocab or not custom_vocab.strip(): return None
    terms = [t.strip() for line in custom_vocab.replace(",", "\n").split("\n") for t in [line.strip()] if t and len(t) > 1]
    return ". ".join(terms) + "." if terms else None

def transcribe_single(client, path, model, prompt=None, max_retries=3):
    for attempt in range(max_retries):
        try:
            with open(path, "rb") as f: file_data = f.read()
            kwargs = {"file": (os.path.basename(path), file_data), "model": model,
                      "response_format": "verbose_json", "language": "es", "temperature": 0.0}
            if prompt: kwargs["prompt"] = prompt
            t = client.audio.transcriptions.create(**kwargs)
            segments = []
            if t.segments:
                for seg in t.segments:
                    if isinstance(seg, dict): s, e, tx = seg.get("start", 0), seg.get("end", 0), seg.get("text", "")
                    else: s, e, tx = getattr(seg, "start", 0), getattr(seg, "end", 0), getattr(seg, "text", "")
                    text = str(tx).strip()
                    if text: segments.append({"start": float(s), "end": float(e), "text": text})
            return t.text or "", segments, None
        except Exception as e:
            err_str = str(e)
            if any(kw in err_str.lower() for kw in ["invalid_api_key", "413", "too large"]): return None, None, err_str
            if attempt < max_retries - 1: time.sleep(2 ** attempt)
            else: return None, None, err_str
    return None, None, "Max retries"

def merge_chunk_segments(all_chunk_results, overlap_ms=35_000):
    if not all_chunk_results: return [], ""
    if len(all_chunk_results) == 1: return all_chunk_results[0]["segments"], all_chunk_results[0]["text"]
    merged = []
    for ci, cr in enumerate(all_chunk_results):
        offset = cr["start_ms"] / 1000.0
        adjusted = [{"start": s["start"]+offset, "end": s["end"]+offset, "text": s["text"]} for s in cr["segments"]]
        if ci == 0: merged.extend(adjusted); continue
        if not merged: merged.extend(adjusted); continue
        oe = (cr["start_ms"]/1000.0) + (overlap_ms/1000.0)
        for seg in adjusted:
            if seg["end"] <= oe:
                sn = norm(seg["text"])
                if any(SequenceMatcher(None, sn, norm(e["text"])).ratio() > 0.65 or
                       (len(sn) > 5 and (sn in norm(e["text"]) or norm(e["text"]) in sn)) or
                       (abs(seg["start"]-e["start"]) < 2.0 and SequenceMatcher(None, sn, norm(e["text"])).ratio() > 0.5)
                       for e in merged[-15:]): continue
            merged.append(seg)
    merged.sort(key=lambda x: x["start"])
    return merged, " ".join(s["text"] for s in merged)

def find_coverage_gaps(segments, total_sec, threshold=5.0):
    if not segments: return [{"start": 0, "end": total_sec, "duration": total_sec}]
    gaps = []; ss = sorted(segments, key=lambda x: x["start"])
    if ss[0]["start"] > threshold: gaps.append({"start": 0, "end": ss[0]["start"], "duration": ss[0]["start"]})
    for i in range(len(ss)-1):
        g = ss[i+1]["start"] - ss[i]["end"]
        if g > threshold: gaps.append({"start": ss[i]["end"], "end": ss[i+1]["start"], "duration": g})
    if ss and total_sec - ss[-1]["end"] > threshold:
        gaps.append({"start": ss[-1]["end"], "end": total_sec, "duration": total_sec - ss[-1]["end"]})
    return gaps

def calculate_coverage(segments, total_sec):
    if not segments or total_sec <= 0: return 0.0
    intervals = sorted([(s["start"], s["end"]) for s in segments])
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], e)
        else: merged.append([s, e])
    return min(100.0, (sum(e-s for s, e in merged) / total_sec) * 100)

def retranscribe_gaps(client, audio_seg, gaps, model, prompt=None, sw=None):
    recovered = []
    for gi, gap in enumerate(gaps):
        if sw: sw.write(f"Procesando hueco {gi+1}/{len(gaps)}: {fmt_time(gap['start'])} → {fmt_time(gap['end'])}")
        margin = 5000
        s_ms = max(0, int(gap["start"]*1000)-margin)
        e_ms = min(len(audio_seg), int(gap["end"]*1000)+margin)
        ga = audio_seg[s_ms:e_ms]
        gp = os.path.join(tempfile.gettempdir(), f"gap_{gi}.mp3")
        ga.export(gp, format="mp3", bitrate="128k")
        _, best, _ = transcribe_single(client, gp, model, prompt=prompt, max_retries=3)
        if not best:
            try:
                gal = ga + 6; gpl = os.path.join(tempfile.gettempdir(), f"gap_{gi}_l.mp3")
                gal.export(gpl, format="mp3", bitrate="128k")
                _, best, _ = transcribe_single(client, gpl, model, prompt=prompt, max_retries=2)
                try: os.remove(gpl)
                except: pass
            except: pass
        if not best:
            alt = "whisper-large-v3-turbo" if "turbo" not in model else "whisper-large-v3"
            _, best, _ = transcribe_single(client, gp, alt, prompt=None, max_retries=2)
        if best:
            off = s_ms / 1000.0
            for seg in best: seg["start"] += off; seg["end"] += off; seg["recovered"] = True
            recovered.extend(best)
        try: os.remove(gp)
        except: pass
    return recovered

def transcribe_complete(client, path, model, prompt=None, ps=None):
    if ps: ps.write("Analizando archivo de audio...")
    dur_ms, audio_seg = get_audio_info(path)
    if dur_ms is None or audio_seg is None:
        if ps: ps.write("Modo de transcripción directa")
        text, segs, err = transcribe_single(client, path, model, prompt=prompt)
        if err or not segs: return None, None, 0, 0, [], 1
        ds = max(s["end"] for s in segs) if segs else 0
        return text, segs, int(ds*1000), calculate_coverage(segs, ds), [], 1
    ds = dur_ms / 1000.0
    if ps: ps.write(f"Duración total: {fmt_duration(ds)}")
    chunks = split_audio_chunks(audio_seg, overlap_ms=35_000)
    nc = len(chunks)
    if ps: ps.write(f"Audio dividido en {nc} bloque{'s' if nc > 1 else ''}")
    all_res = []
    for ci, ch in enumerate(chunks):
        if ps: ps.write(f"Transcribiendo bloque {ci+1}/{nc}...")
        text, segs, err = transcribe_single(client, ch["path"], model, prompt=prompt)
        if segs: all_res.append({"text": text, "segments": segs, "start_ms": ch["start_ms"], "end_ms": ch["end_ms"]})
        elif ps:
            alt = "whisper-large-v3-turbo" if "turbo" not in model else "whisper-large-v3"
            t2, s2, _ = transcribe_single(client, ch["path"], alt, prompt=prompt)
            if s2: all_res.append({"text": t2, "segments": s2, "start_ms": ch["start_ms"], "end_ms": ch["end_ms"]})
        try: os.remove(ch["path"])
        except: pass
    if not all_res: return None, None, dur_ms, 0, [], nc
    merged, ft = merge_chunk_segments(all_res, overlap_ms=35_000)

    merged = filter_hallucinations(merged)
    ft = " ".join(s["text"] for s in merged if not s.get("hallucination_suspect"))

    cov = calculate_coverage(merged, ds); gaps = find_coverage_gaps(merged, ds)
    for pn in range(3):
        if cov >= 99.5: break
        th = [3.0, 2.0, 1.5][min(pn, 2)]
        sg = [g for g in gaps if g["duration"] >= th]
        if not sg: break
        rec = retranscribe_gaps(client, audio_seg, sg, model, prompt=prompt, sw=ps)
        if rec:
            merged.extend(rec); merged.sort(key=lambda x: x["start"])
            dd = []
            for seg in merged:
                if not any(abs(seg["start"]-e["start"]) < 1.5 and SequenceMatcher(None, norm(seg["text"]), norm(e["text"])).ratio() > 0.6 for e in dd[-10:]):
                    dd.append(seg)
            merged = dd; ft = " ".join(s["text"] for s in merged)
            cov = calculate_coverage(merged, ds); gaps = find_coverage_gaps(merged, ds, threshold=th)
        else: break
    if ps: ps.write(f"Cobertura final alcanzada: {cov:.1f}%")
    return ft, merged, dur_ms, cov, gaps, nc


def filter_hallucinations(segments, min_unique_ratio=0.4, max_repeat_ratio=0.7):
    if not segments: return segments
    cleaned = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text: continue
        words = text.lower().split()
        n_words = len(words)
        if n_words < 2:
            cleaned.append(seg); continue
        unique_ratio = len(set(words)) / n_words
        if unique_ratio < min_unique_ratio and n_words > 4:
            seg = dict(seg)
            seg["hallucination_suspect"] = True
            seg["text"] = f"[segmento no claro: {text[:60]}]"
            cleaned.append(seg); continue
        if cleaned:
            prev_text = norm(cleaned[-1].get("text", ""))
            curr_text = norm(text)
            if SequenceMatcher(None, prev_text, curr_text).ratio() > max_repeat_ratio: continue

        PHANTOM_PHRASES = ["suscríbete", "subscríbete", "subscribe", "gracias por ver", "thanks for watching", "like y suscríbete"]
        if any(p in text.lower() for p in PHANTOM_PHRASES) and n_words < 8: continue
        cleaned.append(seg)
    return cleaned


# ============================================================
# POST-PROCESAMIENTO: VOCABULARIO Y CORRECCIÓN
# ============================================================
def post_correct_with_vocabulary(client, text, segments, custom_vocab):
    if not custom_vocab or not custom_vocab.strip(): return text, segments
    vocab_terms = [t.strip() for line in custom_vocab.replace(",", "\n").split("\n") for t in [line.strip()] if t and len(t) > 1]
    if not vocab_terms: return text, segments
    vocab_list = ", ".join(vocab_terms)
    system = (
        "Eres un corrector de transcripciones de audio. "
        "El audio puede contener palabras en español, inglés y otros idiomas.\n\n"
        f"VOCABULARIO CORRECTO:\n{vocab_list}\n\n"
        "INSTRUCCIONES:\n"
        "1. Corrige SOLO palabras que sean claramente transcripción errónea del vocabulario.\n"
        "2. NO cambies palabras no relacionadas. NO agregues ni elimines contenido.\n"
        "3. Devuelve ÚNICAMENTE el texto corregido, sin explicaciones."
    )
    MAX = 5000
    try:
        if len(text) <= MAX:
            r = client.chat.completions.create(model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
                temperature=0.0, max_tokens=4096)
            corrected = r.choices[0].message.content.strip()
            for p in ["Aquí", "Texto corregido", "Corrección"]:
                if corrected.startswith(p) and ":" in corrected[:30]: corrected = corrected.split(":", 1)[1].strip(); break
            return corrected, realign_segments(corrected, segments)
        else:
            sentences = text.split(". "); chunks_t, cur = [], ""
            for s in sentences:
                if len(cur) + len(s) < MAX: cur += s + ". "
                else: chunks_t.append(cur.strip()); cur = s + ". "
            if cur.strip(): chunks_t.append(cur.strip())
            parts = []
            for c in chunks_t:
                try:
                    r = client.chat.completions.create(model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": system}, {"role": "user", "content": c}],
                        temperature=0.0, max_tokens=4096)
                    parts.append(r.choices[0].message.content.strip())
                except: parts.append(c)
            return " ".join(parts), realign_segments(" ".join(parts), segments)
    except: return text, segments

def _correct_chunk(client, text):
    try:
        r = client.chat.completions.create(model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Eres un corrector ortográfico. SOLO corrige tildes, mayúsculas y puntuación. NO cambies, elimines ni agregues palabras. Devuelve únicamente el texto corregido."},
                      {"role": "user", "content": text}], temperature=0.0)
        out = r.choices[0].message.content.strip()
        for p in ["Aquí", "Texto corregido", "Corrección"]:
            if out.startswith(p) and ":" in out[:30]: out = out.split(":", 1)[1].strip(); break
        return out
    except: return text

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

def correct_and_align(client, raw_text, segments):
    MAX = 5000
    if len(raw_text) <= MAX: corrected = _correct_chunk(client, raw_text)
    else:
        sentences = raw_text.split(". "); chunks, cur = [], ""
        for s in sentences:
            if len(cur) + len(s) < MAX: cur += s + ". "
            else: chunks.append(cur.strip()); cur = s + ". "
        if cur.strip(): chunks.append(cur.strip())
        parts = []; bar = st.progress(0, text="Corrigiendo ortografía con IA...")
        for i, c in enumerate(chunks):
            parts.append(_correct_chunk(client, c))
            bar.progress((i+1)/len(chunks), text=f"Procesando parte {i+1}/{len(chunks)}")
        bar.empty(); corrected = " ".join(parts)
    return corrected, realign_segments(corrected, segments)


# ============================================================
# BÚSQUEDA AVANZADA
# ============================================================
_ACCENT_MAP = {
    'a': '[aáàâä]', 'e': '[eéèêë]', 'i': '[iíìîï]', 'o': '[oóòôö]',
    'u': '[uúùûü]', 'n': '[nñ]', 'c': '[cç]',
}

def _build_accent_pattern(word):
    out = []
    for ch in word:
        low = ch.lower()
        out.append(_ACCENT_MAP.get(low, re.escape(ch)))
    return ''.join(out)

def compile_query_pattern(query):
    query = (query or "").strip()
    if not query: return None
    words = [w for w in re.split(r'\s+', query) if w]
    if not words: return None
    parts = [_build_accent_pattern(w) for w in words]
    try: return re.compile(r'\s+'.join(parts), re.IGNORECASE)
    except re.error: return None

def determine_search_mode(query, segments):
    pattern = compile_query_pattern(query)
    if pattern:
        for seg in segments:
            if pattern.search(seg.get("text", "")):
                return pattern, "exacta"
    return pattern, "similar"

def _fuzzy_highlight(text, q_words, fuzzy_thresh):
    found = False; result = text; seen = set()
    for tok in re.findall(r"\S+", text):
        core = re.sub(r'^\W+|\W+$', '', tok)
        wn = norm(core)
        if not wn or len(wn) < 3 or tok in seen: continue
        best = 0.0
        for qw in q_words:
            if len(qw) < 3: continue
            ratio = SequenceMatcher(None, qw, wn).ratio()
            if ratio > best: best = ratio
        if best >= fuzzy_thresh:
            seen.add(tok); found = True
            result = result.replace(tok, f"<mark class='mk-similar'>{tok}</mark>", 1)
    return found, result

def highlight_and_check(text, pattern, q_words, fuzzy_thresh, mode):
    if mode == "exacta":
        if pattern and pattern.search(text):
            html = pattern.sub(lambda m: f"<mark class='mk-exact'>{m.group()}</mark>", text)
            return True, html
        return False, text
    elif mode == "similar":
        return _fuzzy_highlight(text, q_words, fuzzy_thresh)
    return False, text


# ============================================================
# PROCESO PRINCIPAL
# ============================================================
def process_audio(client, uploaded, model, do_correct, custom_vocab=""):
    reset_transcript_state()
    with st.status("Procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path: st.error("Error al guardar archivo"); return False
        size_mb = os.path.getsize(path) / (1024*1024)
        st.write(f"Archivo recibido: {uploaded.name} — {size_mb:.1f} MB")
        st.session_state.uploaded_filename = uploaded.name
        st.session_state.custom_vocabulary = custom_vocab
        converted_path, was_converted = convert_to_mp3(path, status_writer=status)
        st.session_state.audio_path = path
        whisper_prompt = build_prompt_vocabulary(custom_vocab)
        full_text, segments, duration_ms, coverage, gaps, chunks_used = transcribe_complete(
            client, converted_path, model, prompt=whisper_prompt, ps=status)
        if was_converted and converted_path != path:
            try: os.remove(converted_path)
            except: pass
        if not full_text or not segments: st.error("Error en el proceso de transcripción"); return False
        st.session_state.raw_transcript = full_text
        st.session_state.transcript_segments = segments
        st.session_state.audio_duration_ms = duration_ms
        st.session_state.coverage_pct = coverage
        st.session_state.transcript_gaps = gaps
        st.session_state.chunks_used = chunks_used
        if custom_vocab and custom_vocab.strip():
            st.write("Aplicando vocabulario específico...")
            full_text, segments = post_correct_with_vocabulary(client, full_text, segments, custom_vocab)
        if do_correct:
            st.write("Corrigiendo ortografía...")
            txt, csegs = correct_and_align(client, full_text, segments)
            st.session_state.transcript_text = txt
            st.session_state.corrected_segments = csegs
            st.session_state.correction_applied = True
        else:
            st.session_state.transcript_text = full_text
            st.session_state.corrected_segments = segments
            st.session_state.correction_applied = False
        st.session_state.audio_start_time = 0; st.session_state._audio_widget_key = 0
        wc = len(full_text.split())
        status.update(label=f"Transcripción completada — {wc:,} palabras · {coverage:.0f}% cobertura", state="complete", expanded=False)
    return True


# ============================================================
# RENDER DE COMPONENTES
# ============================================================
def render_code_line(idx, seg, html_text, active=False):
    start_sec = float(seg.get("start", 0))
    ts = fmt_time(start_sec)
    active_cls = " active" if active else ""
    return (f"<div class='code-line{active_cls}' data-time='{start_sec}'>"
            f"<span class='line-no'>{idx + 1}</span>"
            f"<span class='line-time'>{ts}</span>"
            f"<span class='line-text'>{html_text}</span></div>")


# ============================================================
# APP PRINCIPAL
# ============================================================
def main_app():
    client = get_client()
    if not client: st.stop()
    pydub_ok, pydub_msg = check_pydub_ffmpeg()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("<div class='side-comment first'>CONFIGURACIÓN</div>", unsafe_allow_html=True)
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: "Large V3 — Alta precisión" if "turbo" not in x else "Large V3 Turbo — Rápido",
                             label_visibility="collapsed")
        do_correct = st.toggle("Corrección ortográfica (IA)", value=True)

        st.markdown("<div class='side-comment'>VOCABULARIO CLAVE</div>", unsafe_allow_html=True)
        st.caption("Nombres propios, marcas o acrónimos que deben respetarse.")
        custom_vocab = st.text_area("Vocabulario", value=st.session_state.get("custom_vocabulary", ""),
            placeholder="Comfenalco\nUniversidad Tecnológica\nCEO", height=100,
            label_visibility="collapsed", key="sidebar_vocab")

        st.markdown("<div class='side-comment'>AJUSTES DE BÚSQUEDA</div>", unsafe_allow_html=True)
        fuzzy_t = st.slider("Sensibilidad a variaciones", 0.55, 0.95, 0.72, 0.02,
                            help="Valores más bajos permiten encontrar errores leves de pronunciación.")

        st.markdown("<div class='side-comment'>ESTADO DEL SISTEMA</div>", unsafe_allow_html=True)
        if pydub_ok:
            st.markdown("<div style='font-family:var(--mono);font-size:0.72rem;color:var(--accent);background:var(--accent-soft);padding:6px 10px;border-radius:6px;border:1px solid var(--accent-border)'>Motor de audio: OK</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-family:var(--mono);font-size:0.72rem;color:var(--amber);background:var(--amber-soft);padding:6px 10px;border-radius:6px;border:1px solid rgba(245, 158, 11, 0.3)'>Advertencia: {pydub_msg}</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state.transcript_text:
            if st.button("Subir otro audio", use_container_width=True):
                reset_transcript_state()
                st.rerun()
        if st.button("Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    # ── WINDOW CHROME ──
    fname_display = st.session_state.uploaded_filename or "Sin archivo"
    tab_name = f"{fname_display}" if st.session_state.transcript_text else "Nuevo audio"
    badge = "<span class='win-badge'><span class='pulse-dot'></span>Procesado</span>" if st.session_state.transcript_text else "<span class='win-badge' style='background:var(--surface-alt);color:var(--text-faint);border-color:var(--border)'>En espera</span>"
    st.markdown(f"""
    <div class="win-chrome">
        <div class="win-dots">
            <span class="win-dot red"></span><span class="win-dot yellow"></span><span class="win-dot green"></span>
        </div>
        <div class="win-tabbar">
            <span class="win-tab active">transcriptor.py</span>
            <span class="win-tab">🎧 {tab_name}</span>
        </div>
        {badge}
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="win-body">', unsafe_allow_html=True)

    # ── SIN TRANSCRIPCIÓN ──
    if not st.session_state.transcript_text:
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            st.markdown(
                '<div class="empty-term">'
                '<div style="color:var(--accent);font-weight:600;margin-bottom:8px;">ESPERANDO ARCHIVO DE AUDIO</div>'
                '<div class="empty-term-title">Selecciona un archivo para procesar</div>'
                '<div class="empty-term-sub">Soporta formatos MP3, WAV, M4A, OGG y MP4</div>'
                '</div>', unsafe_allow_html=True)
            st.write("")
            uploaded = st.file_uploader("x", type=["mp3","wav","m4a","ogg","mp4"], label_visibility="collapsed", key="upload_initial")
            if uploaded and st.button("Iniciar transcripción", type="primary", use_container_width=True):
                if process_audio(client, uploaded, model, do_correct, custom_vocab=custom_vocab): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════════
    # CON TRANSCRIPCIÓN
    # ══════════════════════════════════════════════
    txt = st.session_state.transcript_text or ""
    segs = st.session_state.corrected_segments or []
    n_words = len(txt.split())
    duration = max((float(s.get("end", 0)) for s in segs), default=0)
    coverage = st.session_state.coverage_pct
    gaps = st.session_state.transcript_gaps
    chunks_used = st.session_state.chunks_used
    wpm = round(n_words / max(duration/60, 1)) if duration > 0 else 0

    # Layout de 2 columnas principales:
    # Izquierda: Reproductor, Métricas, Búsqueda, Lista de Segmentos interactivos
    # Derecha: Transcripción completa continua
    left_col, right_col = st.columns([0.42, 0.58], gap="large")

    # ── PANEL IZQUIERDO: REPRODUCTOR, BUSCADOR Y SEGMENTOS ──
    with left_col:
        st.markdown("<div class='panel-header'>REproductor y Control</div>", unsafe_allow_html=True)
        if st.session_state.audio_path:
            st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

        inject_audio_js()

        cov_status_cls = "ok" if coverage >= 95 else "warn" if coverage >= 80 else ""
        corr_status_cls = "ok" if st.session_state.correction_applied else ""

        st.markdown(
            '<div class="status-bar">'
            f'<span class="status-item">Duración: <strong>{fmt_duration(duration)}</strong></span>'
            f'<span class="status-item">Total: <strong>{n_words:,}</strong> palabras</span>'
            f'<span class="status-item">Velocidad: <strong>{wpm}</strong> ppm</span>'
            f'<span class="status-item {cov_status_cls}">Cobertura: <strong>{coverage:.0f}%</strong></span>'
            '</div>'
            '<div class="status-bar">'
            f'<span class="status-item {corr_status_cls}"><strong>{"IA Corregido" if st.session_state.correction_applied else "Original"}</strong></span>'
            + (f'<span class="status-item">{chunks_used} bloques</span>' if chunks_used > 1 else '')
            + (f'<span class="status-item warn">{len(gaps)} vacíos</span>' if gaps else '')
            + '</div>',
            unsafe_allow_html=True
        )

        if gaps:
            with st.expander(f"Se detectaron {len(gaps)} intervalos sin voz", expanded=False):
                for gap in gaps:
                    ts_btn = make_ts_button_html(max(0, gap["start"] - 1))
                    st.markdown(
                        f"<div class='gap-row'><span>{ts_btn}</span> <span>{fmt_time(gap['start'])} → {fmt_time(gap['end'])} ({gap['duration']:.1f}s)</span></div>",
                        unsafe_allow_html=True
                    )

        st.write("")
        st.markdown("<div class='panel-header'>Búsqueda en los segmentos</div>", unsafe_allow_html=True)
        
        sb1, sb2 = st.columns([3, 1.5])
        with sb1:
            query = st.text_input("Buscador", placeholder="Palabra o frase...",
                                  label_visibility="collapsed", value=st.session_state.search_query, key="search_box")
        with sb2:
            only_matches = st.toggle("Filtrar", value=st.session_state.only_matches, key="toggle_only_matches")
            st.session_state.only_matches = only_matches

        if query != st.session_state.search_query:
            st.session_state.search_query = query
            st.session_state.active_segment_idx = -1

        q_norm = norm(query)
        q_words = [w for w in q_norm.split() if w]

        lines_html = []
        highlighted_full_text = txt  # Para usar en el panel derecho si hay búsqueda

        if query:
            pattern, mode = determine_search_mode(query, segs)
            match_count = 0
            
            # Resaltado para texto completo si aplica
            if mode == "exacta" and pattern:
                highlighted_full_text = pattern.sub(lambda m: f"<mark class='mk-exact'>{m.group()}</mark>", txt)
            elif mode == "similar":
                _, highlighted_full_text = _fuzzy_highlight(txt, q_words, fuzzy_t)

            for i, seg in enumerate(segs):
                text = seg.get("text", "")
                matched, html = highlight_and_check(text, pattern, q_words, fuzzy_t, mode)
                if matched: match_count += 1
                if matched or not only_matches:
                    lines_html.append(render_code_line(i, seg, html if matched else text,
                                                        active=(i == st.session_state.active_segment_idx)))

            if mode == "similar":
                st.markdown(
                    f"<div class='similar-banner'>Mostrando variaciones o términos similares para <strong>{query}</strong></div>",
                    unsafe_allow_html=True
                )

            if match_count == 0:
                st.markdown(
                    f"<div class='no-results-box'>Sin coincidencias para '{query}'</div>",
                    unsafe_allow_html=True
                )
        else:
            for i, seg in enumerate(segs):
                lines_html.append(render_code_line(i, seg, seg.get("text", ""),
                                                    active=(i == st.session_state.active_segment_idx)))

        if lines_html:
            st.markdown(f"<div class='code-panel'>{''.join(lines_html)}</div>", unsafe_allow_html=True)


    # ── PANEL DERECHO: TRANSCRIPCIÓN COMPLETA CONTINUA ──
    with right_col:
        st.markdown(
            f'<div class="panel-header">'
            f'<span>Transcripción Completa (Texto Limpio)</span>'
            f'</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="full-text-container">{highlighted_full_text}</div>', unsafe_allow_html=True)

        st.write("")
        st.download_button(
            label="Descargar transcripción completa (.txt)",
            data=txt,
            file_name=f"{fname_display}_transcripcion.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    if check_password():
        main_app()
