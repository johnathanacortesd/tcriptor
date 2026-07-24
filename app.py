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
    page_title="Transcriptor Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght=400;500&display=swap');

    :root {
        --primary: #ea580c;
        --primary-hover: #c2410c;
        --primary-light: #fff7ed;
        --primary-subtle: #fed7aa;
        --surface: #ffffff;
        --bg: #fafaf9;
        --text: #1c1917;
        --text-secondary: #78716c;
        --text-muted: #a8a29e;
        --border: #e7e5e4;
        --green: #059669;
        --green-bg: #ecfdf5;
        --amber: #d97706;
        --amber-bg: #fffbeb;
        --red: #dc2626;
        --red-bg: #fef2f2;
        --blue: #2563eb;
        --blue-bg: #eff6ff;
        --radius: 12px;
        --radius-sm: 8px;
        --radius-xs: 6px;
        --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .main > div:first-child { padding-top: 0 !important; }
    .block-container { padding-top: 0.4rem !important; }
    [data-testid="stAppViewContainer"] > section > div:first-child { padding-top: 0 !important; }
    div[data-testid="stVerticalBlock"] > div:first-child { margin-top: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    body, p, div, h1, h2, h3, h4, h5, h6, li, td, th,
    .stMarkdown, .stText, [data-testid="stMarkdownContainer"],
    [data-testid="stCaptionContainer"], [data-testid="stText"],
    .stButton > button, .stSelectbox, .stTextInput input,
    .stRadio label, .stCheckbox label, .stSlider {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    code, pre, .mono, [data-testid="stCode"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    .main .block-container {
        padding: 0.3rem 1.5rem 1rem 1.5rem;
        max-width: 1400px;
    }

    .stFileUploader > label,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > span,
    .uploadedFileName { font-size: 0.78rem !important; }

    .login-icon {
        width: 56px; height: 56px;
        background: linear-gradient(135deg, #ea580c, #dc2626);
        border-radius: 16px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 24px; margin-bottom: 16px;
    }
    .login-title { font-size: 1.25rem; font-weight: 700; color: var(--text); margin: 0 0 4px 0; }
    .login-subtitle { font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 24px 0; }

    .app-bar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 6px 0 4px 0; margin-bottom: 6px;
        border-bottom: 1px solid var(--border);
    }
    .app-bar-left { display: flex; align-items: center; gap: 10px; }
    .app-logo {
        width: 32px; height: 32px;
        background: linear-gradient(135deg, #ea580c, #dc2626);
        border-radius: 9px; display: flex; align-items: center; justify-content: center;
        font-size: 16px; color: white;
    }
    .app-name { font-size: 1rem; font-weight: 700; color: var(--text); }
    .app-tag {
        font-size: 0.58rem; background: var(--primary-light); color: var(--primary);
        padding: 2px 7px; border-radius: 20px; font-weight: 600; text-transform: uppercase;
    }

    .stats-bar { display: flex; gap: 6px; flex-wrap: wrap; margin: 4px 0 6px 0; }
    .stat-chip {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 0.7rem; color: var(--text-secondary);
        background: var(--bg); padding: 3px 9px; border-radius: 20px;
        border: 1px solid var(--border); font-weight: 500;
    }
    .stat-chip strong { color: var(--text); font-weight: 600; }
    .stat-chip-ok { background: var(--green-bg); color: var(--green); border-color: #a7f3d0; }
    .stat-chip-warn { background: var(--amber-bg); color: var(--amber); border-color: #fcd34d; }

    .sr-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 9px 13px;
        margin-bottom: 5px; box-shadow: var(--shadow-xs); transition: var(--transition);
    }
    .sr-card:hover { border-color: var(--primary-subtle); box-shadow: var(--shadow-sm); }
    .sr-head { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
    .sr-time {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.68rem; font-weight: 500; color: var(--primary);
        background: var(--primary-light); padding: 2px 7px; border-radius: 4px;
    }
    .sr-badge {
        font-size: 0.58rem; font-weight: 700; padding: 1px 6px;
        border-radius: 4px; text-transform: uppercase;
    }
    .sr-badge-exacta { background: var(--green-bg); color: var(--green); }
    .sr-badge-similar { background: var(--amber-bg); color: var(--amber); }
    .sr-body { font-size: 0.83rem; line-height: 1.6; color: var(--text); }

    .hl {
        background: linear-gradient(120deg, #fed7aa, #fdba74);
        color: var(--text); padding: 1px 3px; border-radius: 3px; font-weight: 600;
    }
    .hl-approx {
        background: var(--blue-bg); color: var(--blue);
        padding: 1px 3px; border-radius: 3px; font-weight: 600;
        border-bottom: 2px dashed var(--blue);
    }

    .full-text-box {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 14px 18px;
        font-size: 0.84rem; line-height: 1.85; color: var(--text);
        max-height: 620px; overflow-y: auto;
    }
    .full-text-box::-webkit-scrollbar { width: 5px; }
    .full-text-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

    .panel-header {
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.06em; color: var(--text-muted);
        margin-bottom: 6px; padding-bottom: 4px;
        border-bottom: 1px solid var(--border);
    }

    .empty-state { text-align: center; padding: 32px 20px; color: var(--text-muted); }
    .empty-state-icon { font-size: 2.2rem; margin-bottom: 8px; opacity: 0.6; }
    .empty-state-title { font-size: 0.92rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
    .empty-state-text { font-size: 0.78rem; color: var(--text-muted); }
    .no-results-box {
        text-align: center; padding: 16px; color: var(--text-secondary);
        background: var(--bg); border-radius: var(--radius-sm); border: 1px dashed var(--border);
    }
    .similar-banner {
        background: var(--amber-bg); border: 1px solid #fcd34d; color: #92400e;
        border-radius: var(--radius-sm); padding: 8px 12px; font-size: 0.78rem;
        margin-bottom: 8px;
    }

    section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }

    .stButton > button { border-radius: var(--radius-xs) !important; font-weight: 500 !important; font-size: 0.81rem !important; }
    .stButton > button[kind="primary"] { background: var(--primary) !important; border: none !important; }
    .stButton > button[kind="primary"]:hover { background: var(--primary-hover) !important; }

    .stTextInput > div > div > input {
        border-radius: var(--radius-xs) !important; border-color: var(--border) !important; font-size: 0.84rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(234,88,12,0.1) !important;
    }

    .stAudio { margin: 3px 0 6px 0; }
    hr { border-color: var(--border) !important; margin: 6px 0 !important; }

    .coverage-bar-container {
        background: var(--bg); border-radius: 6px; height: 20px;
        overflow: hidden; border: 1px solid var(--border); margin: 6px 0;
    }
    .coverage-bar-fill {
        height: 100%; border-radius: 5px; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.68rem; font-weight: 700; color: white;
    }
    .coverage-ok { background: linear-gradient(90deg, #059669, #10b981); }
    .coverage-warn { background: linear-gradient(90deg, #d97706, #f59e0b); }
    .coverage-bad { background: linear-gradient(90deg, #dc2626, #ef4444); }

    .ts-jump-btn {
        display: inline-flex; align-items: center; gap: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.68rem; font-weight: 600;
        color: var(--primary); background: var(--primary-light);
        border: 1px solid var(--primary-subtle);
        border-radius: 6px; padding: 4px 10px;
        cursor: pointer; transition: var(--transition); text-decoration: none;
    }
    .ts-jump-btn:hover {
        background: var(--primary-subtle); border-color: var(--primary); transform: scale(1.02);
    }
    .ts-jump-btn:active { transform: scale(0.98); }
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
        const btn = e.target.closest('.ts-jump-btn');
        if (btn) {
            e.preventDefault(); e.stopPropagation();
            const seconds = parseFloat(btn.getAttribute('data-time'));
            if (!isNaN(seconds)) { window.jumpToTime(seconds); }
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

    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown('<div style="text-align:center"><div class="login-icon">🎙️</div>'
                    '<p class="login-title">Transcriptor Pro</p>'
                    '<p class="login-subtitle">Ingresa tu contraseña</p></div>', unsafe_allow_html=True)
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
    ext = os.path.splitext(input_path)[1].lower()
    size_mb = os.path.getsize(input_path) / (1024 * 1024)
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for c in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(c): ffmpeg_bin = c; break
    # Siempre normalizamos el audio (mono, 16kHz, volumen) para mejorar precisión del ASR,
    # incluso si ya es mp3, salvo que ffmpeg no esté disponible.
    if not ffmpeg_bin:
        return input_path, False
    out_path = input_path.rsplit(".", 1)[0] + "_norm.mp3"
    if status_writer: status_writer.write(f"🔄 Normalizando audio para mayor precisión ({size_mb:.0f} MB)...")
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
        if sw: sw.write(f"🔄 Hueco {gi+1}/{len(gaps)}: {fmt_time(gap['start'])} → {fmt_time(gap['end'])}")
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
    if ps: ps.write("📏 Analizando audio...")
    dur_ms, audio_seg = get_audio_info(path)
    if dur_ms is None or audio_seg is None:
        if ps: ps.write("ℹ️ Modo directo")
        text, segs, err = transcribe_single(client, path, model, prompt=prompt)
        if err or not segs: return None, None, 0, 0, [], 1
        ds = max(s["end"] for s in segs) if segs else 0
        return text, segs, int(ds*1000), calculate_coverage(segs, ds), [], 1
    ds = dur_ms / 1000.0
    if ps: ps.write(f"⏱️ {fmt_duration(ds)}")
    chunks = split_audio_chunks(audio_seg, overlap_ms=35_000)
    nc = len(chunks)
    if ps: ps.write(f"✂️ {nc} parte{'s' if nc > 1 else ''}")
    all_res = []
    for ci, ch in enumerate(chunks):
        if ps: ps.write(f"🎧 Parte {ci+1}/{nc}...")
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
    if ps: ps.write(f"✅ Cobertura: {cov:.1f}%")
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
            seg["text"] = f"[⚠️ segmento dudoso: {text[:60]}]"
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
        parts = []; bar = st.progress(0, text="Corrigiendo...")
        for i, c in enumerate(chunks):
            parts.append(_correct_chunk(client, c))
            bar.progress((i+1)/len(chunks), text=f"Bloque {i+1}/{len(chunks)}")
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
            result = result.replace(tok, f"<span class='hl-approx'>{tok}</span>", 1)
    return found, result

def highlight_and_check(text, pattern, q_words, fuzzy_thresh, mode):
    """Determina si un segmento coincide con la búsqueda (según el modo) y
    devuelve el texto con el resaltado HTML correspondiente."""
    if mode == "exacta":
        if pattern and pattern.search(text):
            html = pattern.sub(lambda m: f"<span class='hl'>{m.group()}</span>", text)
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
    with st.status("Procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path: st.error("Error al guardar"); return False
        size_mb = os.path.getsize(path) / (1024*1024)
        st.write(f"📁 {uploaded.name} — {size_mb:.1f} MB")
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
            st.write("🏷️ Aplicando vocabulario personalizado...")
            full_text, segments = post_correct_with_vocabulary(client, full_text, segments, custom_vocab)
        if do_correct:
            st.write("✨ Corrigiendo ortografía...")
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
        cov_icon = "✅" if coverage >= 95 else "⚠️" if coverage >= 80 else "❌"
        status.update(label=f"{cov_icon} {wc:,} palabras · {coverage:.0f}% cobertura", state="complete", expanded=False)
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
        st.markdown("#### ⚙️ Configuración")
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: "V3 Precisión (recomendado)" if "turbo" not in x else "V3 Turbo (más rápido)")
        do_correct = st.toggle("Corrección ortográfica (IA)", value=True)
        st.markdown("---")
        st.markdown("##### 📝 Vocabulario personalizado")
        st.caption("Nombres propios, siglas o términos técnicos que deben transcribirse tal cual.")
        custom_vocab = st.text_area("Vocabulario", value=st.session_state.get("custom_vocabulary", ""),
            placeholder="Comfenalco\nBedout\nUniversidad Tecnológica de Bolívar", height=120,
            label_visibility="collapsed", key="sidebar_vocab")
        st.markdown("---")
        st.markdown("##### 🔍 Búsqueda")
        fuzzy_t = st.slider("Sensibilidad a variaciones/typos", 0.55, 0.95, 0.72, 0.02,
                            help="Más bajo = encuentra variaciones más lejanas (ej. Comfenalco / Confenalco).")
        st.markdown("---")
        if pydub_ok:
            st.markdown("<div style='font-size:0.7rem;color:#059669;background:#ecfdf5;padding:5px 9px;border-radius:6px;border:1px solid #a7f3d0'>✅ pydub + ffmpeg OK</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:0.7rem;color:#d97706;background:#fffbeb;padding:5px 9px;border-radius:6px;border:1px solid #fcd34d'>⚠️ {pydub_msg}</div>", unsafe_allow_html=True)

        st.markdown("---")
        if st.session_state.transcript_text:
            if st.button("🆕 Subir nuevo audio", use_container_width=True):
                reset_transcript_state()
                st.rerun()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    # ── APP BAR ──
    st.markdown("""
    <div class="app-bar">
        <div class="app-bar-left">
            <div class="app-logo">🎙️</div>
            <span class="app-name">Transcriptor Pro</span>
            <span class="app-tag">Transcripción + Búsqueda</span>
        </div>
    </div>""", unsafe_allow_html=True)

    # ── SIN TRANSCRIPCIÓN ──
    if not st.session_state.transcript_text:
        _, col_c, _ = st.columns([1, 2, 1])
        with col_c:
            st.markdown('<div class="empty-state"><div class="empty-state-icon">📂</div>'
                        '<div class="empty-state-title">Sube un archivo de audio</div>'
                        '<div class="empty-state-text">MP3, WAV, M4A, OGG o MP4</div></div>', unsafe_allow_html=True)
            uploaded = st.file_uploader("x", type=["mp3","wav","m4a","ogg","mp4"], label_visibility="collapsed", key="upload_initial")
            if uploaded and st.button("🚀 Transcribir", type="primary", use_container_width=True):
                if process_audio(client, uploaded, model, do_correct, custom_vocab=custom_vocab): st.rerun()
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
    fname_display = st.session_state.uploaded_filename or "audio"
    wpm = round(n_words / max(duration/60, 1)) if duration > 0 else 0

    left_col, right_col = st.columns([0.36, 0.64], gap="medium")

    # ── COLUMNA IZQUIERDA: reproductor + stats ──
    with left_col:
        if st.session_state.audio_path:
            st.markdown("<div class='panel-header'>🎵 Reproductor</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:0.72rem;color:var(--text-secondary);margin-bottom:4px'>📁 <strong>{fname_display[:32]}</strong></div>", unsafe_allow_html=True)
            st.audio(st.session_state.audio_path, start_time=st.session_state.audio_start_time)

        inject_audio_js()

        corr_chip = "stat-chip stat-chip-ok" if st.session_state.correction_applied else "stat-chip"
        corr_text = "✓ Corregido" if st.session_state.correction_applied else "Original"
        cov_chip = "stat-chip stat-chip-ok" if coverage >= 95 else "stat-chip stat-chip-warn" if coverage >= 80 else "stat-chip"
        cov_icon = "✅" if coverage >= 95 else "⚠️" if coverage >= 80 else "❌"
        chunk_html = f'<span class="stat-chip">✂️ <strong>{chunks_used}</strong> partes</span>' if chunks_used > 1 else ""
        gap_html = f'<span class="stat-chip stat-chip-warn">🕳️ <strong>{len(gaps)}</strong> huecos</span>' if gaps else ""
        vocab_chip = '<span class="stat-chip stat-chip-ok">📝 Vocabulario</span>' if st.session_state.get("custom_vocabulary", "").strip() else ""

        st.markdown(
            f'<div class="stats-bar" style="flex-direction:column;align-items:flex-start;gap:4px">'
            f'<span class="stat-chip">⏱️ <strong>{fmt_duration(duration)}</strong></span>'
            f'<span class="stat-chip"><strong>{n_words:,}</strong> palabras · <strong>{wpm}</strong> pal/min</span>'
            f'<span class="{cov_chip}">{cov_icon} Cobertura <strong>{coverage:.0f}%</strong></span>'
            f'<span class="{corr_chip}">{corr_text}</span>{chunk_html}{gap_html}{vocab_chip}</div>',
            unsafe_allow_html=True
        )

        if coverage < 100:
            cc = "coverage-ok" if coverage >= 95 else "coverage-warn" if coverage >= 80 else "coverage-bad"
            st.markdown(
                f'<div class="coverage-bar-container"><div class="coverage-bar-fill {cc}" style="width:{coverage}%">{coverage:.1f}%</div></div>',
                unsafe_allow_html=True
            )

        if gaps:
            with st.expander(f"⚠️ {len(gaps)} huecos detectados", expanded=False):
                for gap in gaps:
                    ts_btn = make_ts_button_html(max(0, gap["start"] - 1))
                    st.markdown(
                        f"{ts_btn} `{fmt_time(gap['start'])}` → `{fmt_time(gap['end'])}` — **{gap['duration']:.1f}s**",
                        unsafe_allow_html=True
                    )

        st.markdown("---")
        st.markdown("##### 📥 Exportar")
        st.download_button("📄 Descargar transcripción (.txt)", data=txt,
                           file_name=f"{fname_display}_transcripcion.txt", mime="text/plain",
                           use_container_width=True)

    # ── COLUMNA DERECHA: búsqueda avanzada + segmentos ──
    with right_col:
        st.markdown("<div class='panel-header'>🔍 Buscar término y localizarlo en el audio</div>", unsafe_allow_html=True)

        query = st.text_input("buscar", placeholder="Ej: Comfenalco, junta directiva, presupuesto...",
                              label_visibility="collapsed", value=st.session_state.search_query, key="search_box")
        if query != st.session_state.search_query:
            st.session_state.search_query = query
            st.session_state.active_segment_idx = -1

        q_norm = norm(query)
        q_words = [w for w in q_norm.split() if w]

        if query:
            pattern, mode = determine_search_mode(query, segs)

            results = []
            for i, seg in enumerate(segs):
                text = seg.get("text", "")
                matched, html = highlight_and_check(text, pattern, q_words, fuzzy_t, mode)
                if matched:
                    results.append((i, seg, html))

            if mode == "similar":
                st.markdown(
                    "<div class='similar-banner'>⚠️ No se encontraron coincidencias exactas para "
                    f"<strong>{query}</strong>. Mostrando términos similares o variaciones (posibles errores de transcripción).</div>",
                    unsafe_allow_html=True
                )
                total_occ = len(results)
            else:
                total_occ = count_exact_occurrences(txt, pattern)

            if results:
                badge_cls = "sr-badge-exacta" if mode == "exacta" else "sr-badge-similar"
                badge_txt = "exacta" if mode == "exacta" else "similar"
                st.caption(f"**{len(results)}** segmento(s) con coincidencia" + (f" · {total_occ} ocurrencias" if mode == "exacta" else ""))
                for i, seg, html in results:
                    start_sec = float(seg.get("start", 0))
                    ts_btn = make_ts_button_html(max(0, start_sec - 1))
                    end_label = fmt_time(float(seg.get("end", 0)))
                    st.markdown(
                        f"""<div class="sr-card"><div class="sr-head">{ts_btn}
                        <span class="sr-time" style="margin-left:4px">{fmt_time(start_sec)} → {end_label}</span>
                        <span class="sr-badge {badge_cls}">{badge_txt}</span></div>
                        <div class="sr-body">{html}</div></div>""",
                        unsafe_allow_html=True
                    )
            else:
                st.markdown(
                    f"<div class='no-results-box'>🔍 Sin resultados, ni siquiera aproximados, para '<strong>{query}</strong>'.</div>",
                    unsafe_allow_html=True
                )
        else:
            st.caption(f"Mostrando los {len(segs)} segmentos de la transcripción. Escribe un término para filtrar y saltar directamente a ese punto del audio.")
            for i, seg in enumerate(segs):
                start_sec = float(seg.get("start", 0))
                ts_btn = make_ts_button_html(max(0, start_sec - 1))
                end_label = fmt_time(float(seg.get("end", 0)))
                st.markdown(
                    f"""<div class="sr-card"><div class="sr-head">{ts_btn}
                    <span class="sr-time" style="margin-left:4px">{fmt_time(start_sec)} → {end_label}</span></div>
                    <div class="sr-body">{seg.get("text","")}</div></div>""",
                    unsafe_allow_html=True
                )

        st.markdown("---")
        with st.expander("📄 Ver transcripción completa"):
            if query:
                pattern2, mode2 = determine_search_mode(query, segs)
                _, full_html = highlight_and_check(txt, pattern2, q_words, fuzzy_t, mode2)
            else:
                full_html = txt
            st.markdown(f"<div class='full-text-box'>{full_html}</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    if check_password():
        main_app()
