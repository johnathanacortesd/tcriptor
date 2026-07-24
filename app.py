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
    page_icon="▍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS — estética tipo editor de código, tema claro
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght=400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;500;600;700&display=swap');

    :root {
        --bg: #f6f6f4;
        --surface: #ffffff;
        --surface-alt: #f0f0ee;
        --surface-sunken: #ececeA;
        --border: #e2e2de;
        --border-strong: #d2d2cd;
        --text: #22241f;
        --text-secondary: #5b5d56;
        --text-faint: #9a9c94;
        --accent: #2f6f4e;
        --accent-dark: #1f4d36;
        --accent-soft: #e3f0e9;
        --amber: #8a6d00;
        --amber-soft: #fff6d6;
        --red: #b3261e;
        --red-soft: #fbeae9;
        --radius: 10px;
        --radius-sm: 7px;
        --radius-xs: 5px;
        --shadow-sm: 0 1px 2px rgba(20,20,15,0.05), 0 1px 1px rgba(20,20,15,0.04);
        --shadow-md: 0 6px 16px rgba(20,20,15,0.08);
        --mono: 'JetBrains Mono', ui-monospace, monospace;
        --sans: 'IBM Plex Sans', -apple-system, sans-serif;
    }

    .main > div:first-child { padding-top: 0 !important; }
    .block-container { padding-top: 0.4rem !important; }
    [data-testid="stAppViewContainer"] > section > div:first-child { padding-top: 0 !important; }
    div[data-testid="stVerticalBlock"] > div:first-child { margin-top: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    [data-testid="stAppViewContainer"] { background: var(--bg); }

    body, p, div, h1, h2, h3, h4, h5, h6, li, td, th,
    .stMarkdown, .stText, [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"], [data-testid="stText"],
    .stButton > button, .stSelectbox, .stTextInput input,
    .stRadio label, .stCheckbox label, .stSlider {
        font-family: var(--sans) !important;
    }
    code, pre, .mono, [data-testid="stCode"] {
        font-family: var(--mono) !important;
    }

    .main .block-container {
        padding: 0.6rem 1.6rem 1.2rem 1.6rem;
        max-width: 1440px;
    }

    .stFileUploader > label,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > span,
    .uploadedFileName { font-size: 0.78rem !important; }

    /* ---------- LOGIN ---------- */
    .login-shell {
        border: 1px solid var(--border); border-radius: var(--radius);
        background: var(--surface); padding: 28px 30px; box-shadow: var(--shadow-sm);
    }
    .login-prompt {
        font-family: var(--mono); font-size: 0.78rem; color: var(--accent);
        margin-bottom: 6px;
    }
    .login-title { font-size: 1.15rem; font-weight: 600; color: var(--text); margin: 0 0 4px 0; }
    .login-subtitle { font-size: 0.83rem; color: var(--text-secondary); margin: 0 0 20px 0; font-family: var(--mono); }

    /* ---------- WINDOW CHROME (barra tipo editor) ---------- */
    .win-chrome {
        display: flex; align-items: center; justify-content: space-between;
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius) var(--radius) 0 0;
        padding: 9px 14px; margin-bottom: 0;
    }
    .win-dots { display: flex; gap: 6px; margin-right: 14px; }
    .win-dot { width: 10px; height: 10px; border-radius: 50%; }
    .win-dot.red { background: #ec6a5e; }
    .win-dot.yellow { background: #f4bf4f; }
    .win-dot.green { background: #61c454; }
    .win-tabbar { display: flex; align-items: center; gap: 8px; flex: 1; }
    .win-tab {
        display: inline-flex; align-items: center; gap: 6px;
        font-family: var(--mono); font-size: 0.74rem; color: var(--text-secondary);
        background: var(--surface-alt); border: 1px solid var(--border);
        border-radius: var(--radius-xs); padding: 3px 10px 3px 8px;
    }
    .win-badge {
        font-family: var(--mono); font-size: 0.68rem; font-weight: 600;
        color: var(--accent-dark); background: var(--accent-soft);
        border: 1px solid #cfe6da; border-radius: 20px; padding: 2px 9px;
        display: inline-flex; align-items: center; gap: 5px;
    }
    .win-badge .pulse-dot {
        width: 6px; height: 6px; border-radius: 50%; background: var(--accent);
    }
    .win-body {
        border: 1px solid var(--border); border-top: none;
        background: var(--surface); border-radius: 0 0 var(--radius) var(--radius);
        padding: 16px 16px 6px 16px; margin-bottom: 14px;
    }

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }
    .side-comment {
        font-family: var(--mono); font-size: 0.68rem; color: var(--text-faint);
        text-transform: none; margin: 14px 0 6px 0; letter-spacing: 0.01em;
    }
    .side-comment.first { margin-top: 2px; }

    /* ---------- STATUS BAR (stats) ---------- */
    .status-bar {
        display: flex; flex-wrap: wrap; gap: 0;
        border: 1px solid var(--border); border-radius: var(--radius-sm);
        overflow: hidden; margin: 8px 0;
    }
    .status-item {
        font-family: var(--mono); font-size: 0.7rem; color: var(--text-secondary);
        padding: 7px 11px; border-right: 1px solid var(--border);
        background: var(--surface-alt); flex: 1 1 auto; white-space: nowrap;
    }
    .status-item:last-child { border-right: none; }
    .status-item strong { color: var(--text); font-weight: 600; }
    .status-item.ok { background: var(--accent-soft); color: var(--accent-dark); }
    .status-item.warn { background: var(--amber-soft); color: var(--amber); }

    .coverage-bar-container {
        background: var(--surface-sunken); border-radius: 6px; height: 18px;
        overflow: hidden; border: 1px solid var(--border); margin: 8px 0;
    }
    .coverage-bar-fill {
        height: 100%; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.65rem; font-weight: 700; color: white; font-family: var(--mono);
    }
    .coverage-ok { background: var(--accent); }
    .coverage-warn { background: #c98f1a; }
    .coverage-bad { background: var(--red); }

    /* ---------- SEARCH BAR ---------- */
    .search-label {
        font-family: var(--mono); font-size: 0.76rem; color: var(--text-faint);
        margin-bottom: 4px;
    }
    .stTextInput > div > div {
        border-radius: var(--radius-sm) !important;
    }
    .stTextInput > div > div > input {
        border-radius: var(--radius-sm) !important; border-color: var(--border) !important;
        font-size: 0.86rem !important; font-family: var(--mono) !important;
        background: var(--surface-alt) !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--accent) !important; box-shadow: 0 0 0 3px var(--accent-soft) !important;
        background: var(--surface) !important;
    }

    .similar-banner {
        font-family: var(--mono); font-size: 0.76rem;
        background: var(--amber-soft); border: 1px solid #f0dd93; color: var(--amber);
        border-radius: var(--radius-sm); padding: 8px 12px; margin: 8px 0;
    }
    .no-results-box {
        text-align: left; padding: 14px 16px; color: var(--text-secondary);
        background: var(--surface-alt); border-radius: var(--radius-sm);
        border: 1px dashed var(--border-strong); font-family: var(--mono); font-size: 0.8rem;
    }
    .results-caption {
        font-family: var(--mono); font-size: 0.74rem; color: var(--text-faint); margin: 4px 0 8px 0;
    }

    /* ---------- CODE PANEL (transcripción tipo editor) ---------- */
    .code-panel {
        border: 1px solid var(--border); border-radius: var(--radius-sm);
        background: var(--surface); max-height: 640px; overflow-y: auto;
    }
    .code-panel::-webkit-scrollbar { width: 6px; }
    .code-panel::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 3px; }
    .code-line {
        display: grid; grid-template-columns: 34px 62px 1fr;
        gap: 10px; align-items: baseline;
        padding: 5px 12px 5px 8px; cursor: pointer;
        border-left: 2px solid transparent;
        transition: background 0.12s ease;
    }
    .code-line:hover { background: var(--surface-alt); }
    .code-line.active {
        background: var(--accent-soft); border-left: 2px solid var(--accent);
    }
    .code-line .line-no {
        font-family: var(--mono); font-size: 0.68rem; color: var(--text-faint);
        text-align: right; user-select: none; padding-top: 2px;
    }
    .code-line .line-time {
        font-family: var(--mono); font-size: 0.68rem; color: var(--accent-dark);
        background: var(--accent-soft); border-radius: 4px; padding: 2px 6px;
        text-align: center; height: fit-content; white-space: nowrap;
    }
    .code-line.active .line-time { background: var(--accent); color: #fff; }
    .code-line .line-text {
        font-family: var(--sans); font-size: 0.85rem; line-height: 1.65; color: var(--text);
    }
    .code-line .line-text.dim { color: var(--text-faint); font-style: italic; }

    mark.mk-exact {
        background: var(--accent); color: #fff; padding: 1px 3px; border-radius: 3px;
        font-weight: 600; box-decoration-break: clone;
    }
    mark.mk-similar {
        background: var(--amber-soft); color: var(--amber); padding: 1px 3px; border-radius: 3px;
        font-weight: 600; border-bottom: 2px dashed var(--amber); box-decoration-break: clone;
    }

    .panel-header {
        font-family: var(--mono); font-size: 0.72rem; font-weight: 500;
        letter-spacing: 0.01em; color: var(--text-faint);
        margin-bottom: 6px; padding-bottom: 4px;
        border-bottom: 1px solid var(--border);
    }
    .panel-header .n { color: var(--accent-dark); font-weight: 600; }

    .empty-term {
        font-family: var(--mono); border: 1px dashed var(--border-strong);
        border-radius: var(--radius); padding: 40px 24px; text-align: center;
        color: var(--text-secondary); background: var(--surface);
    }
    .empty-term .prompt { color: var(--accent); }
    .empty-term-title { font-family: var(--sans); font-size: 1rem; font-weight: 600; color: var(--text); margin: 10px 0 4px 0; }
    .empty-term-sub { font-size: 0.8rem; color: var(--text-faint); margin-bottom: 18px; }

    .gap-row {
        font-family: var(--mono); font-size: 0.74rem; color: var(--text-secondary);
        padding: 5px 0; border-bottom: 1px dashed var(--border);
    }
    .gap-row:last-child { border-bottom: none; }

    .stButton > button {
        border-radius: var(--radius-xs) !important; font-weight: 500 !important;
        font-size: 0.81rem !important; border-color: var(--border) !important;
    }
    .stButton > button[kind="primary"] { background: var(--accent) !important; border: none !important; color: #fff !important; }
    .stButton > button[kind="primary"]:hover { background: var(--accent-dark) !important; }

    .stAudio { margin: 3px 0 6px 0; }
    hr { border-color: var(--border) !important; margin: 8px 0 !important; }

    .ts-jump-btn {
        display: inline-flex; align-items: center; gap: 4px;
        font-family: var(--mono); font-size: 0.68rem; font-weight: 600;
        color: var(--accent-dark); background: var(--accent-soft);
        border: 1px solid #cfe6da; border-radius: 6px; padding: 4px 10px;
        cursor: pointer; transition: all 0.15s ease; text-decoration: none;
    }
    .ts-jump-btn:hover { background: var(--accent); color: #fff; border-color: var(--accent); }
    .ts-jump-btn:active { transform: scale(0.97); }

    .stToggle label, .stCheckbox label { font-size: 0.8rem !important; }
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

def build_timestamped_transcript(segments):
    return "\n".join(f"[{fmt_time(float(seg.get('start', 0)))}] {seg.get('text', '').strip()}"
                     for seg in segments if seg.get("text", "").strip())

def jump_to_time(seconds, segment_idx=-1):
    st.session_state._audio_widget_key = st.session_state.get("_audio_widget_key", 0) + 1
    st.session_state.audio_start_time = max(0, int(seconds))
    if segment_idx >= 0: st.session_state.active_segment_idx = segment_idx


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

    st.markdown("<div style='height:9vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown(
            '<div class="login-shell">'
            '<div class="login-prompt">$ transcriptor --login</div>'
            '<p class="login-title">Transcriptor Pro</p>'
            '<p class="login-subtitle">// ingresa tu contraseña para continuar</p>'
            '</div>', unsafe_allow_html=True)
        st.write("")
        st.text_input("pwd", type="password", label_visibility="collapsed",
                      placeholder="Contraseña...", key="_pwd_input", on_change=do_login)
        st.button("Ingresar", use_container_width=True, type="primary", on_click=do_login)
        if st.session_state.get("_login_error"):
            st.error(st.session_state._login_error); st.session_state._login_error = None
    if st.session_state.authenticated: st.rerun()
    return False

def get_client():
    try: return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except: st.error("API key no configurada"); return None


# ============================================================
# PROCESAMIENTO DE AUDIO (precisión)
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
    if not ffmpeg_bin:
        return input_path, False
    out_path = input_path.rsplit(".", 1)[0] + "_norm.mp3"
    if status_writer: status_writer.write(f"normalizando audio para mayor precisión ({size_mb:.0f} MB)...")
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
            if r2.returncode != 0:
                return input_path, False
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
        if sw: sw.write(f"hueco {gi+1}/{len(gaps)}: {fmt_time(gap['start'])} → {fmt_time(gap['end'])}")
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
    if ps: ps.write("analizando audio...")
    dur_ms, audio_seg = get_audio_info(path)
    if dur_ms is None or audio_seg is None:
        if ps: ps.write("modo directo")
        text, segs, err = transcribe_single(client, path, model, prompt=prompt)
        if err or not segs: return None, None, 0, 0, [], 1
        ds = max(s["end"] for s in segs) if segs else 0
        return text, segs, int(ds*1000), calculate_coverage(segs, ds), [], 1
    ds = dur_ms / 1000.0
    if ps: ps.write(f"duración: {fmt_duration(ds)}")
    chunks = split_audio_chunks(audio_seg, overlap_ms=35_000)
    nc = len(chunks)
    if ps: ps.write(f"dividido en {nc} parte{'s' if nc > 1 else ''}")
    all_res = []
    for ci, ch in enumerate(chunks):
        if ps: ps.write(f"transcribiendo parte {ci+1}/{nc}...")
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
    if ps: ps.write(f"cobertura final: {cov:.1f}%")
    return ft, merged, dur_ms, cov, gaps, nc


# ============================================================
# FILTRO DE ALUCINACIONES (mejora la precisión real del texto)
# ============================================================
def filter_hallucinations(segments, min_unique_ratio=0.4, max_repeat_ratio=0.7):
    if not segments:
        return segments

    cleaned = []
    for seg in segments:
        text = seg.get("text", "").strip()
        if not text:
            continue

        words = text.lower().split()
        n_words = len(words)

        if n_words < 2:
            cleaned.append(seg)
            continue

        unique_ratio = len(set(words)) / n_words
        if unique_ratio < min_unique_ratio and n_words > 4:
            seg = dict(seg)
            seg["hallucination_suspect"] = True
            seg["text"] = f"[segmento dudoso: {text[:60]}]"
            cleaned.append(seg)
            continue

        if cleaned:
            prev_text = norm(cleaned[-1].get("text", ""))
            curr_text = norm(text)
            similarity = SequenceMatcher(None, prev_text, curr_text).ratio()
            if similarity > max_repeat_ratio:
                continue

        PHANTOM_PHRASES = [
            "suscríbete", "subscríbete", "subscribe",
            "gracias por ver", "thanks for watching",
            "no olvides darle like", "like y suscríbete",
            "música", "music", "[música]", "[music]",
            "subtítulos por", "subtitles by",
        ]
        is_phantom = any(p in text.lower() for p in PHANTOM_PHRASES)
        if is_phantom and n_words < 8:
            continue

        cleaned.append(seg)

    return cleaned


# ============================================================
# POST-PROCESAMIENTO: vocabulario + corrección ortográfica
# (usa el mismo modelo Groq de texto que ya se usaba: llama-3.3-70b-versatile)
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
        parts = []; bar = st.progress(0, text="corrigiendo...")
        for i, c in enumerate(chunks):
            parts.append(_correct_chunk(client, c))
            bar.progress((i+1)/len(chunks), text=f"bloque {i+1}/{len(chunks)}")
        bar.empty(); corrected = " ".join(parts)
    return corrected, realign_segments(corrected, segments)


# ============================================================
# BÚSQUEDA AVANZADA
# Exacta (tolerante a acentos y mayúsculas) -> si no hay resultados,
# cae automáticamente a coincidencias similares/variaciones (typos).
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
    try:
        return re.compile(r'\s+'.join(parts), re.IGNORECASE)
    except re.error:
        return None

def determine_search_mode(query, segments):
    """Devuelve (pattern, modo). modo = 'exacta' si hay al menos una coincidencia
    exacta (con variaciones de acentos/mayúsculas) en algún segmento; si no,
    'similar' para activar la búsqueda difusa (typos / variaciones)."""
    pattern = compile_query_pattern(query)
    if pattern:
        for seg in segments:
            if pattern.search(seg.get("text", "")):
                return pattern, "exacta"
    return pattern, "similar"

def _fuzzy_highlight(text, q_words, fuzzy_thresh):
    """Resalta y detecta palabras similares (variaciones/typos) a la consulta."""
    found = False
    result = text
    seen = set()
    for tok in re.findall(r"\S+", text):
        core = re.sub(r'^\W+|\W+$', '', tok)
        wn = norm(core)
        if not wn or len(wn) < 3 or tok in seen:
            continue
        best = 0.0
        for qw in q_words:
            if len(qw) < 3:
                continue
            ratio = SequenceMatcher(None, qw, wn).ratio()
            if ratio > best:
                best = ratio
        if best >= fuzzy_thresh:
            seen.add(tok)
            found = True
            result = result.replace(tok, f"<mark class='mk-similar'>{tok}</mark>", 1)
    return found, result

def highlight_and_check(text, pattern, q_words, fuzzy_thresh, mode):
    """Determina si un segmento coincide con la búsqueda (según el modo) y
    devuelve el texto con el resaltado HTML correspondiente."""
    if mode == "exacta":
        if pattern and pattern.search(text):
            html = pattern.sub(lambda m: f"<mark class='mk-exact'>{m.group()}</mark>", text)
            return True, html
        return False, text
    elif mode == "similar":
        return _fuzzy_highlight(text, q_words, fuzzy_thresh)
    return False, text

def count_exact_occurrences(text, pattern):
    if not pattern or not text: return 0
    return len(pattern.findall(text))


# ============================================================
# PROCESO PRINCIPAL DE TRANSCRIPCIÓN
# ============================================================
def process_audio(client, uploaded, model, do_correct, custom_vocab=""):
    reset_transcript_state()
    with st.status("procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path: st.error("Error al guardar"); return False
        size_mb = os.path.getsize(path) / (1024*1024)
        st.write(f"archivo: {uploaded.name} — {size_mb:.1f} MB")
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
        if not full_text or not segments: st.error("Error en transcripción"); return False
        st.session_state.raw_transcript = full_text
        st.session_state.transcript_segments = segments
        st.session_state.audio_duration_ms = duration_ms
        st.session_state.coverage_pct = coverage
        st.session_state.transcript_gaps = gaps
        st.session_state.chunks_used = chunks_used
        if custom_vocab and custom_vocab.strip():
            st.write("aplicando vocabulario personalizado...")
            full_text, segments = post_correct_with_vocabulary(client, full_text, segments, custom_vocab)
        if do_correct:
            st.write("corrigiendo ortografía...")
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
        status.update(label=f"listo — {wc:,} palabras · {coverage:.0f}% cobertura", state="complete", expanded=False)
    return True


# ============================================================
# RENDER: línea de código (segmento con gutter de timestamp)
# ============================================================
def render_code_line(idx, seg, html_text, active=False, dim=False):
    start_sec = float(seg.get("start", 0))
    ts = fmt_time(start_sec)
    active_cls = " active" if active else ""
    text_cls = " dim" if dim else ""
    return (f"<div class='code-line{active_cls}' data-time='{start_sec}'>"
            f"<span class='line-no'>{idx + 1}</span>"
            f"<span class='line-time'>{ts}</span>"
            f"<span class='line-text{text_cls}'>{html_text}</span></div>")


# ============================================================
# APP PRINCIPAL
# ============================================================
def main_app():
    client = get_client()
    if not client: st.stop()
    pydub_ok, pydub_msg = check_pydub_ffmpeg()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("<div class='side-comment first'># configuración</div>", unsafe_allow_html=True)
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: "V3 — precisión (recomendado)" if "turbo" not in x else "V3 Turbo — más rápido",
                             label_visibility="collapsed")
        do_correct = st.toggle("Corrección ortográfica (IA)", value=True)

        st.markdown("<div class='side-comment'># vocabulario personalizado</div>", unsafe_allow_html=True)
        st.caption("Nombres propios, siglas o términos técnicos que deben transcribirse tal cual.")
        custom_vocab = st.text_area("Vocabulario", value=st.session_state.get("custom_vocabulary", ""),
            placeholder="Comfenalco\nBedout\nUniversidad Tecnológica de Bolívar", height=110,
            label_visibility="collapsed", key="sidebar_vocab")

        st.markdown("<div class='side-comment'># búsqueda</div>", unsafe_allow_html=True)
        fuzzy_t = st.slider("Sensibilidad a variaciones/typos", 0.55, 0.95, 0.72, 0.02,
                            help="Más bajo = encuentra variaciones más lejanas (ej. Comfenalco / Confenalco).")

        st.markdown("<div class='side-comment'># estado del sistema</div>", unsafe_allow_html=True)
        if pydub_ok:
            st.markdown("<div style='font-family:var(--mono);font-size:0.7rem;color:var(--accent-dark);background:var(--accent-soft);padding:5px 9px;border-radius:6px;border:1px solid #cfe6da'>[ok] pydub + ffmpeg</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-family:var(--mono);font-size:0.7rem;color:var(--amber);background:var(--amber-soft);padding:5px 9px;border-radius:6px;border:1px solid #f0dd93'>[warn] {pydub_msg}</div>", unsafe_allow_html=True)

        st.markdown("---")
        if st.session_state.transcript_text:
            if st.button("＋ subir nuevo audio", use_container_width=True):
                reset_transcript_state()
                st.rerun()
        if st.button("cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    # ── WINDOW CHROME ──
    fname_display = st.session_state.uploaded_filename or "sin_archivo"
    tab_name = f"{fname_display}" if st.session_state.transcript_text else "nuevo_audio"
    badge = "<span class='win-badge'><span class='pulse-dot'></span>listo</span>" if st.session_state.transcript_text else "<span class='win-badge' style='background:var(--surface-alt);color:var(--text-faint);border-color:var(--border)'>en espera</span>"
    st.markdown(f"""
    <div class="win-chrome">
        <div class="win-dots">
            <span class="win-dot red"></span><span class="win-dot yellow"></span><span class="win-dot green"></span>
        </div>
        <div class="win-tabbar">
            <span class="win-tab">▍ transcriptor.py</span>
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
                '<div><span class="prompt">$</span> esperando archivo de audio...</div>'
                '<div class="empty-term-title">Sube un audio para comenzar</div>'
                '<div class="empty-term-sub">MP3 · WAV · M4A · OGG · MP4</div>'
                '</div>', unsafe_allow_html=True)
            st.write("")
            uploaded = st.file_uploader("x", type=["mp3","wav","m4a","ogg","mp4"], label_visibility="collapsed", key="upload_initial")
            if uploaded and st.button("▶ transcribir", type="primary", use_container_width=True):
                if process_audio(client, uploaded, model, do_correct, custom_vocab=custom_vocab): st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # ══════════════════════════════════════════════
    # CON TRANSCRIPCIÓN
    # ══════════════════════════════════════════════
    txt = st.session_state.transcript_text
    if not isinstance(txt, str):
        txt = str(txt) if txt is not None else ""
        st.session_state.transcript_text = txt

    segs = st.session_state.corrected_segments or []
    n_words = len(txt.split())
    duration = max((float(s.get("end", 0)) for s in segs), default=0)
    coverage = st.session_state.coverage_pct
    gaps = st.session_state.transcript_gaps
    chunks_used = st.session_state.chunks_used
    wpm = round(n_words / max(duration/60, 1)) if duration > 0 else 0

    left_col, right_col = st.columns([0.34, 0.66], gap="medium")

    # ── COLUMNA IZQUIERDA: reproductor + status bar ──
    with left_col:
        if st.session_state.audio_path:
            st.markdown("<div class='panel-header'>reproductor</div>", unsafe_allow_html=True)
            st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

        inject_audio_js()

        cov_status_cls = "ok" if coverage >= 95 else "warn" if coverage >= 80 else ""
        corr_status_cls = "ok" if st.session_state.correction_applied else ""

        st.markdown(
            '<div class="status-bar">'
            f'<span class="status-item"><strong>{fmt_duration(duration)}</strong></span>'
            f'<span class="status-item"><strong>{n_words:,}</strong> palabras</span>'
            f'<span class="status-item"><strong>{wpm}</strong> ppm</span>'
            f'<span class="status-item {cov_status_cls}">cobertura <strong>{coverage:.0f}%</strong></span>'
            '</div>'
            '<div class="status-bar">'
            f'<span class="status-item {corr_status_cls}">{"corregido" if st.session_state.correction_applied else "original"}</span>'
            + (f'<span class="status-item">{chunks_used} partes</span>' if chunks_used > 1 else '')
            + (f'<span class="status-item warn">{len(gaps)} huecos</span>' if gaps else '')
            + ('<span class="status-item ok">vocabulario</span>' if st.session_state.get("custom_vocabulary", "").strip() else '')
            + '</div>',
            unsafe_allow_html=True
        )

        if coverage < 100:
            cc = "coverage-ok" if coverage >= 95 else "coverage-warn" if coverage >= 80 else "coverage-bad"
            st.markdown(
                f'<div class="coverage-bar-container"><div class="coverage-bar-fill {cc}" style="width:{coverage}%">{coverage:.1f}%</div></div>',
                unsafe_allow_html=True
            )

        if gaps:
            with st.expander(f"{len(gaps)} huecos detectados", expanded=False):
                for gap in gaps:
                    ts_btn = make_ts_button_html(max(0, gap["start"] - 1))
                    st.markdown(
                        f"<div class='gap-row'>{ts_btn} {fmt_time(gap['start'])} → {fmt_time(gap['end'])} · {gap['duration']:.1f}s</div>",
                        unsafe_allow_html=True
                    )

        st.markdown("<div class='side-comment' style='margin-top:14px'># exportar</div>", unsafe_allow_html=True)
        st.download_button("descargar transcripción (.txt)", data=txt,
                           file_name=f"{fname_display}_transcripcion.txt", mime="text/plain",
                           use_container_width=True)

    # ── COLUMNA DERECHA: búsqueda + transcripción completa ──
    with right_col:
        sc1, sc2 = st.columns([4, 1.3])
        with sc1:
            st.markdown("<div class='search-label'>$ grep --buscar</div>", unsafe_allow_html=True)
            query = st.text_input("buscar", placeholder="ej: Comfenalco, junta directiva, presupuesto...",
                                  label_visibility="collapsed", value=st.session_state.search_query, key="search_box")
        with sc2:
            st.markdown("<div class='search-label'>&nbsp;</div>", unsafe_allow_html=True)
            only_matches = st.toggle("solo coincidencias", value=st.session_state.only_matches, key="toggle_only_matches")
            st.session_state.only_matches = only_matches

        if query != st.session_state.search_query:
            st.session_state.search_query = query
            st.session_state.active_segment_idx = -1

        q_norm = norm(query)
        q_words = [w for w in q_norm.split() if w]

        lines_html = []
        if query:
            pattern, mode = determine_search_mode(query, segs)
            match_count = 0
            for i, seg in enumerate(segs):
                text = seg.get("text", "")
                matched, html = highlight_and_check(text, pattern, q_words, fuzzy_t, mode)
                if matched:
                    match_count += 1
                if matched or not only_matches:
                    lines_html.append(render_code_line(i, seg, html if matched else text,
                                                        active=(i == st.session_state.active_segment_idx),
                                                        dim=(only_matches is False and not matched and False)))

            if mode == "similar":
                st.markdown(
                    f"<div class='similar-banner'>// sin coincidencias exactas para <strong>{query}</strong> — "
                    f"mostrando términos similares o variaciones (posibles errores de transcripción)</div>",
                    unsafe_allow_html=True
                )
                st.markdown(f"<div class='panel-header'>transcripción — <span class='n'>{match_count}</span> coincidencia(s) similar(es)</div>", unsafe_allow_html=True)
            else:
                total_occ = count_exact_occurrences(txt, pattern)
                st.markdown(f"<div class='panel-header'>transcripción — <span class='n'>{match_count}</span> línea(s) · <span class='n'>{total_occ}</span> ocurrencia(s) exactas</div>", unsafe_allow_html=True)

            if match_count == 0:
                st.markdown(
                    f"<div class='no-results-box'>// sin resultados, ni siquiera aproximados, para '{query}'</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(f"<div class='panel-header'>transcripción completa — <span class='n'>{len(segs)}</span> líneas</div>", unsafe_allow_html=True)
            for i, seg in enumerate(segs):
                lines_html.append(render_code_line(i, seg, seg.get("text", ""),
                                                    active=(i == st.session_state.active_segment_idx)))

        if lines_html:
            st.markdown(f"<div class='code-panel'>{''.join(lines_html)}</div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    if check_password():
        main_app()
