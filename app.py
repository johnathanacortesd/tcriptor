import streamlit as st
import os
import tempfile
import unicodedata
from groq import Groq
from difflib import SequenceMatcher
import re
import json
import time
from datetime import datetime

st.set_page_config(page_title="Transcriptor Pro", page_icon="🎙️", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
    :root {
        --primary: #ea580c; --primary-hover: #c2410c; --primary-light: #fff7ed; --primary-subtle: #fed7aa;
        --surface: #ffffff; --bg: #fafaf9; --text: #1c1917; --text-secondary: #78716c; --text-muted: #a8a29e;
        --border: #e7e5e4; --green: #059669; --green-bg: #ecfdf5; --amber: #d97706; --amber-bg: #fffbeb;
        --red: #dc2626; --red-bg: #fef2f2; --blue: #2563eb; --blue-bg: #eff6ff;
        --radius: 12px; --radius-sm: 8px; --radius-xs: 6px;
        --shadow-xs: 0 1px 2px rgba(0,0,0,0.04); --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .main > div:first-child { padding-top: 0 !important; }
    .block-container { padding-top: 0.4rem !important; }
    [data-testid="stToolbar"] { display: none !important; }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
    body, p, div, h1, h2, h3, h4, h5, h6, li, td, th,
    .stMarkdown, .stText, [data-testid="stMarkdownContainer"],
    .stButton > button, .stSelectbox, .stTextInput input,
    .stRadio label, .stCheckbox label, .stSlider {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    code, pre, .mono { font-family: 'JetBrains Mono', monospace !important; }
    .main .block-container { padding: 0.3rem 1.5rem 1rem 1.5rem; max-width: 1400px; }
    .login-icon { width:56px;height:56px;background:linear-gradient(135deg,#ea580c,#dc2626);border-radius:16px;display:inline-flex;align-items:center;justify-content:center;font-size:24px;margin-bottom:16px; }
    .login-title { font-size:1.25rem;font-weight:700;color:var(--text);margin:0 0 4px 0; }
    .login-subtitle { font-size:0.85rem;color:var(--text-secondary);margin:0 0 24px 0; }
    .app-bar { display:flex;align-items:center;justify-content:space-between;padding:6px 0 4px 0;margin-bottom:4px;border-bottom:1px solid var(--border); }
    .app-bar-left { display:flex;align-items:center;gap:10px; }
    .app-logo { width:32px;height:32px;background:linear-gradient(135deg,#ea580c,#dc2626);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:16px;color:white; }
    .app-name { font-size:1rem;font-weight:700;color:var(--text); }
    .app-tag { font-size:0.58rem;background:var(--primary-light);color:var(--primary);padding:2px 7px;border-radius:20px;font-weight:600;text-transform:uppercase; }
    .hist-bar { display:flex;gap:4px;flex-wrap:wrap;padding:4px 0 6px 0;margin-bottom:4px;border-bottom:1px solid var(--border); }
    .hist-chip { display:inline-flex;align-items:center;gap:5px;font-size:0.72rem;padding:4px 10px;border-radius:20px;border:1px solid var(--border);background:var(--bg);color:var(--text-secondary);cursor:pointer;font-weight:500;white-space:nowrap; }
    .hist-chip.active { background:var(--primary);color:white;border-color:var(--primary); }
    .hist-chip-dot { width:6px;height:6px;border-radius:50%;background:currentColor;opacity:0.6; }
    .stats-bar { display:flex;gap:6px;flex-wrap:wrap;margin:4px 0 6px 0; }
    .stat-chip { display:inline-flex;align-items:center;gap:4px;font-size:0.7rem;color:var(--text-secondary);background:var(--bg);padding:3px 9px;border-radius:20px;border:1px solid var(--border);font-weight:500; }
    .stat-chip strong { color:var(--text);font-weight:600; }
    .stat-chip-ok { background:var(--green-bg);color:var(--green);border-color:#a7f3d0; }
    .stat-chip-warn { background:var(--amber-bg);color:var(--amber);border-color:#fcd34d; }
    .sr-card { background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:9px 13px;margin-bottom:5px;box-shadow:var(--shadow-xs); }
    .sr-card:hover { border-color:var(--primary-subtle);box-shadow:var(--shadow-sm); }
    .sr-card-global { border-left:3px solid var(--blue); }
    .sr-head { display:flex;align-items:center;gap:6px;margin-bottom:4px; }
    .sr-time { font-family:'JetBrains Mono',monospace!important;font-size:0.68rem;font-weight:500;color:var(--primary);background:var(--primary-light);padding:2px 7px;border-radius:4px; }
    .sr-badge { font-size:0.58rem;font-weight:700;padding:1px 6px;border-radius:4px;text-transform:uppercase; }
    .sr-badge-high { background:var(--green-bg);color:var(--green); }
    .sr-badge-medium { background:var(--amber-bg);color:var(--amber); }
    .sr-badge-low { background:var(--red-bg);color:var(--red); }
    .sr-body { font-size:0.81rem;line-height:1.6;color:var(--text); }
    .sr-ctx { color:var(--text-muted); }
    .sr-segment-full { font-size:0.76rem;line-height:1.5;color:var(--text-secondary);margin-top:5px;padding-top:5px;border-top:1px dashed var(--border); }
    .hl { background:linear-gradient(120deg,#fed7aa,#fdba74);color:var(--text);padding:1px 3px;border-radius:3px;font-weight:600; }
    .ent-person { background:#dbeafe;color:#1d4ed8;padding:1px 5px;border-radius:3px;font-weight:600;font-size:0.88em;border-bottom:2px solid #93c5fd; }
    .ent-org { background:#d1fae5;color:#065f46;padding:1px 5px;border-radius:3px;font-weight:600;font-size:0.88em;border-bottom:2px solid #6ee7b7; }
    .ent-place { background:#fef3c7;color:#92400e;padding:1px 5px;border-radius:3px;font-weight:600;font-size:0.88em;border-bottom:2px solid #fcd34d; }
    .ent-date { background:#f3e8ff;color:#6b21a8;padding:1px 5px;border-radius:3px;font-weight:600;font-size:0.88em;border-bottom:2px solid #d8b4fe; }
    .ent-other { background:#f1f5f9;color:#475569;padding:1px 5px;border-radius:3px;font-weight:600;font-size:0.88em;border-bottom:2px solid #cbd5e1; }
    .marker-card { display:flex;align-items:center;gap:8px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-xs);padding:7px 11px;margin-bottom:4px;font-size:0.8rem; }
    .marker-card:hover { border-color:var(--primary-subtle); }
    .marker-label { flex:1;color:var(--text);font-weight:500; }
    .marker-note { color:var(--text-secondary);font-size:0.75rem;font-style:italic; }
    .lead-box { background:linear-gradient(135deg,#fff7ed,#fef3c7);border:1px solid var(--primary-subtle);border-radius:var(--radius-sm);padding:16px 20px;margin:8px 0; }
    .lead-titular { font-size:1.05rem;font-weight:700;color:var(--text);line-height:1.3;margin-bottom:8px; }
    .lead-subtitular { font-size:0.85rem;color:var(--text-secondary);font-weight:500;margin-bottom:10px;line-height:1.4; }
    .lead-body { font-size:0.83rem;line-height:1.7;color:var(--text);border-top:1px solid var(--primary-subtle);padding-top:10px; }
    .lead-label { font-size:0.62rem;font-weight:700;text-transform:uppercase;color:var(--primary);letter-spacing:0.05em;margin-bottom:4px; }
    .seg-viewer { background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);max-height:100%;overflow-y:auto;padding:6px 2px; }
    .seg-viewer::-webkit-scrollbar { width:4px; }
    .seg-viewer::-webkit-scrollbar-thumb { background:var(--border);border-radius:2px; }
    .seg-row { display:flex;align-items:flex-start;gap:8px;padding:5px 10px;border-radius:6px;margin:1px 4px;cursor:pointer;border-left:3px solid transparent; }
    .seg-row:hover { background:var(--primary-light); }
    .seg-row.active { background:linear-gradient(90deg,#fff7ed,#ffedd5);border-left-color:var(--primary); }
    .seg-ts { font-family:'JetBrains Mono',monospace;font-size:0.62rem;color:var(--primary);background:var(--primary-light);padding:2px 5px;border-radius:3px;white-space:nowrap;margin-top:2px;min-width:44px;text-align:center; }
    .seg-txt { font-size:0.81rem;line-height:1.55;color:var(--text-secondary); }
    .seg-row.active .seg-txt { font-weight:500;color:var(--text); }
    .full-text-box { background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 18px;font-size:0.84rem;line-height:1.85;color:var(--text);height:100%;max-height:620px;overflow-y:auto; }
    .full-text-box::-webkit-scrollbar { width:5px; }
    .full-text-box::-webkit-scrollbar-thumb { background:var(--border);border-radius:3px; }
    .panel-header { font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);margin-bottom:6px;padding-bottom:4px;border-bottom:1px solid var(--border); }
    .empty-state { text-align:center;padding:32px 20px;color:var(--text-muted); }
    .empty-state-icon { font-size:2.2rem;margin-bottom:8px;opacity:0.6; }
    .empty-state-title { font-size:0.92rem;font-weight:600;color:var(--text-secondary);margin-bottom:4px; }
    .empty-state-text { font-size:0.78rem;color:var(--text-muted); }
    .no-results-box { text-align:center;padding:16px;color:var(--text-secondary);background:var(--bg);border-radius:var(--radius-sm);border:1px dashed var(--border); }
    .stTabs [data-baseweb="tab-list"] { gap:0;background:var(--bg);border-radius:var(--radius-sm);padding:3px;border:1px solid var(--border); }
    .stTabs [data-baseweb="tab"] { font-size:0.78rem;font-weight:500;padding:5px 14px;color:var(--text-secondary);border-radius:var(--radius-xs);border-bottom:none!important;background:transparent; }
    .stTabs [aria-selected="true"] { color:var(--primary)!important;background:var(--surface)!important;box-shadow:var(--shadow-xs)!important; }
    .stTabs [data-baseweb="tab-panel"] { padding-top:8px; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display:none; }
    section[data-testid="stSidebar"] { background:var(--surface);border-right:1px solid var(--border); }
    .stButton > button { border-radius:var(--radius-xs)!important;font-weight:500!important;font-size:0.81rem!important; }
    .stButton > button[kind="primary"] { background:var(--primary)!important;border:none!important; }
    .stButton > button[kind="primary"]:hover { background:var(--primary-hover)!important; }
    .stTextInput > div > div > input { border-radius:var(--radius-xs)!important;border-color:var(--border)!important;font-size:0.84rem!important; }
    .stTextInput > div > div > input:focus { border-color:var(--primary)!important;box-shadow:0 0 0 3px rgba(234,88,12,0.1)!important; }
    .stAudio { margin:3px 0 6px 0; }
    .stChatMessage { font-size:0.87rem; }
    hr { border-color:var(--border)!important;margin:6px 0!important; }
    .kpi-grid { display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin:8px 0; }
    .kpi-card { background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:12px 14px;text-align:center; }
    .kpi-value { font-size:1.3rem;font-weight:700;color:var(--primary); }
    .kpi-label { font-size:0.68rem;color:var(--text-muted);margin-top:2px;text-transform:uppercase;font-weight:500; }
    .coverage-bar-container { background:var(--bg);border-radius:6px;height:20px;overflow:hidden;border:1px solid var(--border);margin:6px 0; }
    .coverage-bar-fill { height:100%;border-radius:5px;display:flex;align-items:center;justify-content:center;font-size:0.68rem;font-weight:700;color:white; }
    .coverage-ok { background:linear-gradient(90deg,#059669,#10b981); }
    .coverage-warn { background:linear-gradient(90deg,#d97706,#f59e0b); }
    .coverage-bad { background:linear-gradient(90deg,#dc2626,#ef4444); }
    .hist-card { background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-sm);padding:10px 14px;margin-bottom:6px;cursor:pointer; }
    .hist-card:hover { border-color:var(--primary-subtle);box-shadow:var(--shadow-sm); }
    .hist-card.active { border-color:var(--primary);border-left:3px solid var(--primary); }
    .hist-card-name { font-size:0.82rem;font-weight:600;color:var(--text);margin-bottom:3px; }
    .hist-card-meta { font-size:0.7rem;color:var(--text-muted); }
    /* ── WORD FREQUENCY — ancho expandido para palabras largas ── */
    .freq-bar-row { display:flex;align-items:center;gap:10px;margin:3px 0;font-size:0.78rem; }
    .freq-bar-label { width:170px;min-width:170px;font-weight:500;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap; }
    .freq-bar-track { flex:1;background:var(--bg);border-radius:5px;height:18px;overflow:hidden;border:1px solid var(--border);min-width:80px; }
    .freq-bar-fill { height:100%;border-radius:4px;display:flex;align-items:center;padding-left:6px;font-size:0.65rem;font-weight:700;color:white;white-space:nowrap;min-width:4px; }
    .freq-bar-count { width:30px;min-width:30px;text-align:right;color:var(--text-secondary);font-size:0.72rem;font-weight:500; }
    /* ── IDIOMA TAG ── */
    .lang-en { background:#dbeafe;color:#1e40af;padding:0px 4px;border-radius:3px;font-size:0.65em;font-weight:700;letter-spacing:0.04em;vertical-align:middle;border:1px solid #93c5fd;margin-left:3px; }
    /* ── GLOSSARY BOX ── */
    .glossary-box { font-size:0.72rem;background:var(--primary-light);border:1px solid var(--primary-subtle);border-radius:6px;padding:6px 9px;color:var(--text-secondary);line-height:1.6; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
AUDIO_DEFAULTS = {
    "transcript_text": None, "transcript_segments": None, "corrected_segments": None,
    "raw_transcript": None, "audio_path": None, "audio_start_time": 0,
    "correction_applied": False, "analysis_cache": {}, "uploaded_filename": None,
    "audio_duration_ms": 0, "coverage_pct": 100.0, "transcript_gaps": [],
    "chunks_used": 1, "active_segment_idx": -1, "markers": [], "entities": None, "lead_cache": None,
}
GLOBAL_DEFAULTS = {
    "authenticated": False, "pydub_available": None, "chat_history": [],
    "search_results": None, "last_search_query": "", "global_search_results": None,
    "last_global_query": "", "audio_history": [], "active_audio_id": None,
    "_search_pending": False, "_global_search_pending": False, "_jump_counter": 0,
    # Glosario de sesión: persiste entre audios, se envía a Whisper como contexto
    "session_glossary": [],
}
for k, v in {**AUDIO_DEFAULTS, **GLOBAL_DEFAULTS}.items():
    if k not in st.session_state:
        st.session_state[k] = v

MAX_HISTORY = 6

def history_save_current():
    aid = st.session_state.active_audio_id
    if not aid or not st.session_state.transcript_text:
        return
    snapshot = {k: st.session_state[k] for k in AUDIO_DEFAULTS}
    snapshot["id"] = aid
    snapshot["saved_at"] = datetime.now().isoformat()
    hist = st.session_state.audio_history
    for i, h in enumerate(hist):
        if h["id"] == aid:
            hist[i] = snapshot
            return
    if len(hist) >= MAX_HISTORY:
        hist.pop(0)
    hist.append(snapshot)

def history_load(audio_id):
    for h in st.session_state.audio_history:
        if h["id"] == audio_id:
            for k in AUDIO_DEFAULTS:
                st.session_state[k] = h.get(k, AUDIO_DEFAULTS[k])
            st.session_state.active_audio_id = audio_id
            st.session_state.chat_history = []
            st.session_state.search_results = None
            st.session_state.last_search_query = ""
            return True
    return False

def history_new_id():
    return f"audio_{int(time.time()*1000)}"

def reset_current_audio():
    for k, v in AUDIO_DEFAULTS.items():
        st.session_state[k] = v
    st.session_state.chat_history = []
    st.session_state.search_results = None
    st.session_state.last_search_query = ""

def check_pydub_ffmpeg():
    if st.session_state.pydub_available is not None:
        return st.session_state.pydub_available, ""
    try:
        from pydub import AudioSegment
    except ImportError:
        st.session_state.pydub_available = False
        return False, "pydub no instalado"
    import shutil
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(candidate):
                ffmpeg_bin = candidate
                os.environ["PATH"] = os.path.dirname(candidate) + os.pathsep + os.environ.get("PATH", "")
                break
    if not ffmpeg_bin:
        st.session_state.pydub_available = False
        return False, "ffmpeg no en PATH"
    try:
        from pydub import AudioSegment
        _ = len(AudioSegment.silent(duration=100))
    except Exception as e:
        st.session_state.pydub_available = False
        return False, f"pydub falla: {e}"
    st.session_state.pydub_available = True
    return True, ""

def fmt_time(seconds):
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"

def fmt_duration(seconds):
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    parts = []
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{sec}s")
    return " ".join(parts)

def norm(text):
    if not text: return ""
    t = unicodedata.normalize('NFD', text)
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn').lower().strip()

def highlight_html(text, query):
    if not query or not text: return text
    result = text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(result):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    for w in query.split():
        if len(w) > 1:
            result = re.compile(re.escape(w), re.IGNORECASE).sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    return result

def highlight_full_text(text, query):
    if not query or not text: return text
    result = text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(result):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    for w in [w for w in query.split() if len(w) > 1]:
        result = re.compile(r'(?<![<\w])(' + re.escape(w) + r')(?![>\w])', re.IGNORECASE).sub(r"<span class='hl'>\1</span>", result)
    return result

def count_occurrences(text, query):
    if not query or not text: return 0
    count = len(re.findall(re.escape(query), text, re.IGNORECASE))
    if count == 0:
        for w in query.split():
            if len(w) > 1:
                count += len(re.findall(re.escape(w), text, re.IGNORECASE))
    return count

def get_audio_duration(segments):
    if not segments: return 0
    return max(float(seg.get("end", 0)) for seg in segments)

def build_timestamped_transcript(segments):
    lines = []
    for seg in segments:
        t = fmt_time(float(seg.get("start", 0)))
        txt = seg.get("text", "").strip()
        if txt:
            lines.append(f"[{t}] {txt}")
    return "\n".join(lines)

def jump_to_time(seconds, segment_idx=-1):
    st.session_state._jump_counter = st.session_state.get("_jump_counter", 0) + 1
    st.session_state.audio_start_time = max(0.0, float(seconds))
    st.session_state._audio_start_actual = max(0.0, float(seconds)) + st.session_state._jump_counter * 0.001
    if segment_idx >= 0:
        st.session_state.active_segment_idx = segment_idx

# ============================================================
# GLOSARIO + PROMPT PARA WHISPER
# ============================================================
# Términos en inglés frecuentes en periodismo colombiano.
# Incluirlos en el prompt de Whisper evita que los fonetice en español.
_EN_JOURNALISM_WORDS = {
    "streaming", "online", "offline", "podcast", "live", "trending", "smartphone",
    "app", "apps", "software", "hardware", "wifi", "whatsapp", "twitter", "instagram",
    "facebook", "tiktok", "youtube", "google", "selfie", "fake", "hacker", "hacking",
    "startup", "fintech", "blockchain", "bitcoin", "crypto", "lobbying", "lobby",
    "dumping", "rating", "ranking", "default", "impeachment", "briefing", "compliance",
    "governance", "accountability", "benchmark", "playoff", "playoffs", "draft", "coach",
    "manager", "penalty", "comeback", "knockout", "show", "fashion", "marketing",
    "branding", "pitch", "feedback", "workshop", "networking", "freelance", "outsourcing",
    "bullying", "stalking", "boom", "crash", "background", "off the record", "press release",
}

def build_whisper_prompt(session_glossary=None):
    """
    Prompt inicial enviado a Whisper como contexto previo ("memoria a corto plazo").

    Por qué funciona:
      Whisper trata este texto como el fragmento transcrito JUSTO ANTES del audio.
      Aprende el vocabulario, estilo y nombres propios del contexto, lo que:
      1. Reduce confusiones de apellidos (Bedout → no lo convierte en Benito)
      2. Mantiene palabras en inglés en inglés (streaming, off the record)
      3. Orienta el registro a periodismo colombiano formal

    Límite: ~850 caracteres. Se trunca automáticamente.
    """
    parts = [
        "Periodismo colombiano. Entrevista en español con posibles anglicismos y nombres propios. "
        "Transcribir con precisión. Palabras en inglés tal como se pronuncian en inglés."
    ]
    glossary_terms = list(session_glossary or [])
    if glossary_terms:
        seen = set()
        unique = []
        for t in glossary_terms:
            tl = t.strip()
            if tl and tl.lower() not in seen:
                seen.add(tl.lower())
                unique.append(tl)
        parts.append("Nombres propios y términos: " + ", ".join(unique[:35]) + ".")
    prompt = " ".join(parts)
    return prompt[:850] if len(prompt) > 850 else prompt

# ============================================================
# AUTH
# ============================================================
def check_password():
    if st.session_state.authenticated:
        return True
    def do_login():
        pwd = st.session_state.get("_pwd_input", "")
        if not pwd: return
        try:
            if pwd == st.secrets["general"]["app_password"]:
                st.session_state.authenticated = True
            else:
                st.session_state._login_error = "Contraseña incorrecta"
        except Exception:
            st.session_state._login_error = "Error de configuración"
    st.markdown("<div style='height:10vh'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown("""<div style="text-align:center">
            <div class="login-icon">🎙️</div>
            <p class="login-title">Transcriptor Pro</p>
            <p class="login-subtitle">Ingresa tu contraseña para continuar</p>
        </div>""", unsafe_allow_html=True)
        st.text_input("pwd", type="password", label_visibility="collapsed",
                      placeholder="Contraseña...", key="_pwd_input", on_change=do_login)
        st.button("Ingresar", use_container_width=True, type="primary", on_click=do_login)
        if st.session_state.get("_login_error"):
            st.error(st.session_state._login_error)
            st.session_state._login_error = None
    if st.session_state.authenticated:
        st.rerun()
    return False

def get_client():
    try:
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except Exception:
        st.error("API key no configurada")
        return None

# ============================================================
# AUDIO: SAVE, CONVERT, INFO, CHUNKS
# ============================================================
def save_uploaded(f):
    try:
        safe = "".join(c for c in f.name if c.isalnum() or c in "._-") or "audio.mp3"
        path = os.path.join(tempfile.gettempdir(), f"up_{safe}")
        with open(path, "wb") as fp:
            fp.write(f.getbuffer())
        return path
    except Exception:
        return None

def convert_to_mp3(input_path, status_writer=None):
    import shutil
    ext = os.path.splitext(input_path)[1].lower()
    size_mb = os.path.getsize(input_path) / (1024 * 1024)
    if ext == ".mp3" and size_mb < 24:
        return input_path, False
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
            if os.path.isfile(candidate):
                ffmpeg_bin = candidate
                break
    if not ffmpeg_bin:
        return input_path, False
    out_path = input_path.rsplit(".", 1)[0] + "_converted.mp3"
    if status_writer:
        status_writer.write(f"🔄 Convirtiendo a MP3 ({size_mb:.0f} MB → ~{size_mb*0.08:.0f}-{size_mb*0.12:.0f} MB)...")
    import subprocess
    cmd = [ffmpeg_bin, "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame",
           "-ac", "1", "-ar", "16000", "-b:a", "64k", "-af", "aresample=16000,volume=1.5", out_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode != 0:
            cmd2 = [ffmpeg_bin, "-y", "-i", input_path, "-vn", "-acodec", "libmp3lame", "-ac", "1", "-b:a", "64k", out_path]
            result2 = subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
            if result2.returncode != 0:
                return input_path, False
        new_size_mb = os.path.getsize(out_path) / (1024 * 1024)
        if status_writer:
            status_writer.write(f"✅ Convertido: {size_mb:.1f} MB → {new_size_mb:.1f} MB")
        return out_path, True
    except subprocess.TimeoutExpired:
        return input_path, False
    except Exception:
        return input_path, False

def get_audio_info(path):
    ok, _ = check_pydub_ffmpeg()
    if not ok: return None, None
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(path)
        return len(audio), audio
    except Exception as e:
        st.warning(f"⚠️ No se pudo analizar el audio: {e}")
        return None, None

def split_audio_chunks(audio_segment, chunk_duration_ms=600_000, overlap_ms=15_000):
    total_ms = len(audio_segment)
    chunks = []
    if total_ms <= chunk_duration_ms:
        chunk_path = os.path.join(tempfile.gettempdir(), "chunk_0.mp3")
        audio_segment.export(chunk_path, format="mp3", bitrate="128k")
        chunks.append({"path": chunk_path, "start_ms": 0, "end_ms": total_ms, "index": 0})
        return chunks
    start, idx = 0, 0
    while start < total_ms:
        end = min(start + chunk_duration_ms, total_ms)
        chunk = audio_segment[start:end]
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{idx}.mp3")
        chunk.export(chunk_path, format="mp3", bitrate="128k")
        if os.path.getsize(chunk_path) / (1024 * 1024) > 24:
            chunk.export(chunk_path, format="mp3", bitrate="64k")
        chunks.append({"path": chunk_path, "start_ms": start, "end_ms": end, "index": idx})
        if end >= total_ms: break
        start = end - overlap_ms
        idx += 1
    return chunks

# ============================================================
# TRANSCRIPCIÓN PRINCIPAL — SOPORTE MULTILINGÜE
# ============================================================
def transcribe_single(client, path, model, whisper_prompt="", max_retries=3):
    """
    Transcribe un chunk con máxima cobertura y soporte de extranjerismos.

    Estrategia:
    ───────────
    1. language="es" SIEMPRE — garantiza cobertura completa del audio.
       Quitar este parámetro causó que Whisper truncara la transcripción
       a ~1 minuto de un audio de 4 minutos (bug confirmado con Groq/Whisper).

    2. prompt=whisper_prompt — glosario con nombres propios y términos en inglés.
       Whisper los usa como contexto previo: mejora el reconocimiento de
       apellidos (Bedout, Uribe) y anglicismos (streaming, off the record)
       SIN necesidad de quitar el idioma.
       Razón: el prompt actúa como "memoria" que sesga el vocabulario,
       no como un cambio de idioma. Whisper con language="es" y un prompt
       que incluya "Bedout, off the record" transcribirá esos términos
       correctamente porque los "recuerda" del contexto previo.

    3. temperature=0.0 — sin alucinaciones.
    """
    for attempt in range(max_retries):
        try:
            with open(path, "rb") as f:
                file_data = f.read()
            kwargs = dict(
                file=(os.path.basename(path), file_data),
                model=model,
                response_format="verbose_json",
                language="es",   # SIEMPRE español — crítico para cobertura completa
                temperature=0.0,
            )
            # El prompt enseña a Whisper los nombres propios y términos en inglés
            # sin cambiar el idioma de transcripción. Es el mecanismo correcto
            # para manejar code-switching en periodismo colombiano.
            if whisper_prompt:
                kwargs["prompt"] = whisper_prompt
            t = client.audio.transcriptions.create(**kwargs)
            segments = []
            if t.segments:
                for seg in t.segments:
                    if isinstance(seg, dict):
                        s, e, tx = seg.get("start", 0), seg.get("end", 0), seg.get("text", "")
                    else:
                        s, e, tx = getattr(seg, "start", 0), getattr(seg, "end", 0), getattr(seg, "text", "")
                    text = str(tx).strip()
                    if text:
                        segments.append({"start": float(s), "end": float(e), "text": text})
            return t.text or "", segments, None
        except Exception as e:
            err_str = str(e)
            if any(kw in err_str.lower() for kw in ["invalid_api_key", "413", "too large"]):
                return None, None, err_str
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                return None, None, err_str
    return None, None, "Max retries exceeded"

def merge_chunk_segments(all_chunk_results, overlap_ms=15_000):
    if not all_chunk_results: return [], ""
    if len(all_chunk_results) == 1:
        r = all_chunk_results[0]
        return r["segments"], r["text"]
    merged_segments = []
    for ci, chunk_result in enumerate(all_chunk_results):
        chunk_start_sec = chunk_result["start_ms"] / 1000.0
        adjusted = [{"start": seg["start"] + chunk_start_sec,
                     "end": seg["end"] + chunk_start_sec,
                     "text": seg["text"]} for seg in chunk_result["segments"]]
        if ci == 0:
            merged_segments.extend(adjusted)
            continue
        if not merged_segments:
            merged_segments.extend(adjusted)
            continue
        last_end = merged_segments[-1]["end"]
        for seg in adjusted:
            if seg["start"] < last_end - 1.0:
                seg_n = norm(seg["text"])
                is_dup = any(
                    SequenceMatcher(None, seg_n, norm(e["text"])).ratio() > 0.7 or
                    seg_n in norm(e["text"]) or norm(e["text"]) in seg_n
                    for e in merged_segments[-10:] if e.get("text")
                )
                if is_dup: continue
            merged_segments.append(seg)
            last_end = max(last_end, seg["end"])
    merged_segments.sort(key=lambda x: x["start"])
    return merged_segments, " ".join(seg["text"] for seg in merged_segments)

def find_coverage_gaps(segments, total_duration_sec, gap_threshold=5.0):
    if not segments:
        return [{"start": 0, "end": total_duration_sec, "duration": total_duration_sec}]
    gaps = []
    sorted_segs = sorted(segments, key=lambda x: x["start"])
    if sorted_segs[0]["start"] > gap_threshold:
        gaps.append({"start": 0, "end": sorted_segs[0]["start"], "duration": sorted_segs[0]["start"]})
    for i in range(len(sorted_segs) - 1):
        gs, ge = sorted_segs[i]["end"], sorted_segs[i+1]["start"]
        if ge - gs > gap_threshold:
            gaps.append({"start": gs, "end": ge, "duration": ge - gs})
    if sorted_segs and total_duration_sec - sorted_segs[-1]["end"] > gap_threshold:
        gaps.append({"start": sorted_segs[-1]["end"], "end": total_duration_sec,
                     "duration": total_duration_sec - sorted_segs[-1]["end"]})
    return gaps

def calculate_coverage(segments, total_duration_sec):
    if not segments or total_duration_sec <= 0: return 0.0
    intervals = sorted([(seg["start"], seg["end"]) for seg in segments])
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        if s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return min(100.0, (sum(e - s for s, e in merged) / total_duration_sec) * 100)

def retranscribe_gaps(client, audio_segment, gaps, model, whisper_prompt="", status_writer=None):
    recovered = []
    for gi, gap in enumerate(gaps):
        if status_writer:
            status_writer.write(f"🔄 Re-transcribiendo hueco {gi+1}/{len(gaps)}: {fmt_time(gap['start'])} → {fmt_time(gap['end'])}")
        margin_ms = 2000
        start_ms = max(0, int(gap["start"] * 1000) - margin_ms)
        end_ms = min(len(audio_segment), int(gap["end"] * 1000) + margin_ms)
        gap_audio = audio_segment[start_ms:end_ms]
        gap_path = os.path.join(tempfile.gettempdir(), f"gap_{gi}.mp3")
        gap_audio.export(gap_path, format="mp3", bitrate="128k")
        _, segments, _ = transcribe_single(client, gap_path, model, whisper_prompt=whisper_prompt, max_retries=3)
        if segments:
            offset = start_ms / 1000.0
            for seg in segments:
                seg["start"] += offset
                seg["end"] += offset
                seg["recovered"] = True
            recovered.extend(segments)
        try: os.remove(gap_path)
        except Exception: pass
    return recovered

def transcribe_complete(client, path, model, whisper_prompt="", progress_status=None):
    if progress_status: progress_status.write("📏 Analizando audio...")
    duration_ms, audio_segment = get_audio_info(path)
    if duration_ms is None or audio_segment is None:
        if progress_status: progress_status.write("ℹ️ Modo directo (sin segmentación)")
        text, segments, error = transcribe_single(client, path, model, whisper_prompt=whisper_prompt)
        if error or not segments: return None, None, 0, 0, [], 1
        duration_sec = max(seg["end"] for seg in segments) if segments else 0
        coverage = calculate_coverage(segments, duration_sec)
        return text, segments, int(duration_sec * 1000), coverage, [], 1
    duration_sec = duration_ms / 1000.0
    if progress_status: progress_status.write(f"⏱️ Duración: {fmt_duration(duration_sec)}")
    chunks = split_audio_chunks(audio_segment)
    n_chunks = len(chunks)
    if progress_status: progress_status.write(f"✂️ {n_chunks} parte{'s' if n_chunks > 1 else ''}")
    all_results = []
    for ci, chunk in enumerate(chunks):
        if progress_status:
            progress_status.write(f"🎧 Parte {ci+1}/{n_chunks} ({fmt_time(chunk['start_ms']/1000)} → {fmt_time(chunk['end_ms']/1000)})...")
        text, segments, error = transcribe_single(client, chunk["path"], model, whisper_prompt=whisper_prompt)
        if segments:
            all_results.append({"text": text, "segments": segments,
                                 "start_ms": chunk["start_ms"], "end_ms": chunk["end_ms"], "index": ci})
        try: os.remove(chunk["path"])
        except Exception: pass
    if not all_results: return None, None, duration_ms, 0, [], n_chunks
    if progress_status: progress_status.write("🔗 Fusionando...")
    merged_segments, full_text = merge_chunk_segments(all_results)
    coverage = calculate_coverage(merged_segments, duration_sec)
    gaps = find_coverage_gaps(merged_segments, duration_sec)
    if progress_status: progress_status.write(f"📊 Cobertura: {coverage:.1f}%")
    if gaps and coverage < 98.0:
        significant_gaps = [g for g in gaps if g["duration"] >= 3.0]
        if significant_gaps:
            if progress_status: progress_status.write(f"🔍 Recuperando {len(significant_gaps)} huecos...")
            recovered = retranscribe_gaps(client, audio_segment, significant_gaps, model,
                                          whisper_prompt=whisper_prompt, status_writer=progress_status)
            if recovered:
                merged_segments.extend(recovered)
                merged_segments.sort(key=lambda x: x["start"])
                deduped = []
                for seg in merged_segments:
                    if not any(abs(seg["start"] - e["start"]) < 1.0 and
                               SequenceMatcher(None, norm(seg["text"]), norm(e["text"])).ratio() > 0.7
                               for e in deduped[-5:]):
                        deduped.append(seg)
                merged_segments = deduped
                full_text = " ".join(seg["text"] for seg in merged_segments)
                coverage = calculate_coverage(merged_segments, duration_sec)
                gaps = find_coverage_gaps(merged_segments, duration_sec)
                if progress_status: progress_status.write(f"✅ Cobertura final: {coverage:.1f}%")
    return full_text, merged_segments, duration_ms, coverage, gaps, n_chunks

# ============================================================
# CORRECCIÓN ORTOGRÁFICA — PRESERVA EXTRANJERISMOS
# ============================================================
def _correct_chunk(client, text):
    """
    Corrección ortográfica con preservación de palabras en inglés y nombres propios.
    CAMBIO vs anterior: el LLM ahora tiene instrucción explícita de NO españolizar
    términos en inglés ni adaptar apellidos extranjeros.
    """
    prompt = (
        "Eres un corrector ortográfico para periodismo colombiano. "
        "REGLAS:\n"
        "1. SOLO corrige tildes, mayúsculas y puntuación.\n"
        "2. NUNCA cambies, elimines ni agregues palabras.\n"
        "3. PRESERVA palabras en inglés tal como están (streaming, off the record, etc.).\n"
        "4. PRESERVA apellidos y nombres propios sin adaptarlos (Bedout, Trump, etc.).\n"
        "5. Devuelve ÚNICAMENTE el texto corregido, sin comentarios."
    )
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            temperature=0.0
        )
        out = r.choices[0].message.content.strip()
        for prefix in ["Aquí", "Texto corregido", "Corrección"]:
            if out.startswith(prefix) and ":" in out[:30]:
                out = out.split(":", 1)[1].strip()
                break
        return out
    except Exception:
        return text

def realign_segments(corrected_text, original_segments):
    words = corrected_text.split()
    total_orig = sum(len(s["text"].split()) for s in original_segments)
    if total_orig == 0: return original_segments
    aligned, idx = [], 0
    for i, seg in enumerate(original_segments):
        seg_wc = len(seg["text"].split())
        if i == len(original_segments) - 1:
            chunk = words[idx:]
        else:
            take = max(1, round((seg_wc / total_orig) * len(words)))
            chunk = words[idx:idx + take]
            idx += len(chunk)
        aligned.append({"start": seg["start"], "end": seg["end"],
                        "text": " ".join(chunk) if chunk else seg["text"]})
    return aligned

def correct_and_align(client, raw_text, segments):
    MAX = 5000
    if len(raw_text) <= MAX:
        corrected = _correct_chunk(client, raw_text)
    else:
        sentences = raw_text.split(". ")
        chunks, cur = [], ""
        for s in sentences:
            if len(cur) + len(s) < MAX:
                cur += s + ". "
            else:
                chunks.append(cur.strip())
                cur = s + ". "
        if cur.strip():
            chunks.append(cur.strip())
        parts = []
        bar = st.progress(0, text="Corrigiendo...")
        for i, c in enumerate(chunks):
            parts.append(_correct_chunk(client, c))
            bar.progress((i + 1) / len(chunks), text=f"Bloque {i+1}/{len(chunks)}")
        bar.empty()
        corrected = " ".join(parts)
    return corrected, realign_segments(corrected, segments)

# ============================================================
# BÚSQUEDA
# ============================================================
def search_segments(query, segments, corrected_segments, context_words=30, fuzzy_thresh=0.75):
    if not query: return []
    target = corrected_segments if corrected_segments else segments
    if not target: return []
    q_norm = norm(query)
    q_words = q_norm.split()
    if not q_words: return []
    all_words = [(w, si) for si, seg in enumerate(target) for w in seg.get("text", "").split()]
    if not all_words: return []
    search_norm = [norm(w) for w, _ in all_words]
    found = []
    for i in range(len(search_norm) - len(q_words) + 1):
        if q_norm in " ".join(search_norm[i:i + len(q_words)]):
            found.append({"pos": i, "len": len(q_words), "conf": "high", "score": 1.0, "seg": all_words[i][1]})
    if not found:
        for i, wn in enumerate(search_norm):
            for qw in q_words:
                if len(qw) > 2 and qw in wn:
                    found.append({"pos": i, "len": 1, "conf": "high", "score": 0.95, "seg": all_words[i][1]})
                    break
    if not found and fuzzy_thresh < 1.0:
        offset = 0
        for si, seg in enumerate(target):
            txt = seg.get("text", "")
            sc = SequenceMatcher(None, q_norm, norm(txt)).ratio()
            if sc >= fuzzy_thresh:
                found.append({"pos": offset, "len": len(txt.split()),
                              "conf": "medium" if sc > 0.85 else "low", "score": sc, "seg": si})
            offset += len(txt.split())
    seen, results = set(), []
    for fp in found:
        if fp["seg"] in seen: continue
        seen.add(fp["seg"])
        seg = target[fp["seg"]]
        p, ln = fp["pos"], fp["len"]
        cs, ce = max(0, p - context_words), min(len(all_words), p + ln + context_words)
        me = min(p + ln, len(all_words))
        results.append({
            "start_time": float(seg.get("start", 0)), "end_time": float(seg.get("end", 0)),
            "time_label": fmt_time(float(seg.get("start", 0))), "end_label": fmt_time(float(seg.get("end", 0))),
            "before": " ".join(all_words[j][0] for j in range(cs, p)),
            "match_hl": highlight_html(" ".join(all_words[j][0] for j in range(p, me)), query),
            "after": " ".join(all_words[j][0] for j in range(me, ce)),
            "confidence": fp["conf"], "score": fp["score"], "idx": fp["seg"],
            "full_segment": seg.get("text", ""),
            "prev_segment": target[fp["seg"]-1].get("text","") if fp["seg"] > 0 else "",
            "next_segment": target[fp["seg"]+1].get("text","") if fp["seg"] < len(target)-1 else "",
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def global_search(query, audio_history, fuzzy_thresh=0.75):
    if not query or not audio_history: return []
    all_results = []
    for audio in audio_history:
        segs = audio.get("corrected_segments") or audio.get("transcript_segments") or []
        hits = search_segments(query, segs, audio.get("corrected_segments"), context_words=20, fuzzy_thresh=fuzzy_thresh)
        for h in hits:
            h["audio_id"] = audio.get("id", "")
            h["audio_name"] = audio.get("uploaded_filename", "audio")
        all_results.extend(hits)
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results

# ============================================================
# IA: ENTIDADES
# ============================================================
def extract_entities(client, text):
    if st.session_state.entities is not None:
        return st.session_state.entities
    system = """Eres un extractor de entidades para periodismo colombiano.
Extrae del texto:
- PERSONAS: nombres de personas mencionadas
- ORGANIZACIONES: empresas, instituciones, partidos, medios
- LUGARES: países, ciudades, regiones
- FECHAS: fechas, períodos temporales
- OTROS: conceptos clave

Responde ÚNICAMENTE en JSON:
{"personas":[],"organizaciones":[],"lugares":[],"fechas":[],"otros":[]}"""
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:8000]}],
            temperature=0.0, max_tokens=800
        )
        raw = re.sub(r"```json\s*|\s*```", "", r.choices[0].message.content.strip()).strip()
        entities = json.loads(raw)
        result = {k: entities.get(k, []) for k in ["personas", "organizaciones", "lugares", "fechas", "otros"]}
        st.session_state.entities = result
        # Auto-poblar glosario de sesión con personas y orgs detectadas
        # para que el PRÓXIMO audio también se beneficie
        new_terms = result.get("personas", []) + result.get("organizaciones", [])
        existing = {t.lower() for t in st.session_state.session_glossary}
        for term in new_terms:
            if term and len(term) > 2 and term.lower() not in existing:
                st.session_state.session_glossary.append(term)
                existing.add(term.lower())
        return result
    except Exception:
        fallback = {"personas":[],"organizaciones":[],"lugares":[],"fechas":[],"otros":[]}
        st.session_state.entities = fallback
        return fallback

def highlight_entities_in_text(text, entities):
    if not entities or not text: return text
    pairs = []
    for ent in entities.get("personas", []):
        if ent and len(ent) > 2: pairs.append((ent, "ent-person"))
    for ent in entities.get("organizaciones", []):
        if ent and len(ent) > 2: pairs.append((ent, "ent-org"))
    for ent in entities.get("lugares", []):
        if ent and len(ent) > 2: pairs.append((ent, "ent-place"))
    for ent in entities.get("fechas", []):
        if ent and len(ent) > 2: pairs.append((ent, "ent-date"))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    result = text
    for term, cls in pairs:
        pat = re.compile(r'(?<![<\w])(' + re.escape(term) + r')(?![>\w\-])', re.IGNORECASE)
        result = pat.sub(lambda m: f"<span class='{cls}'>{m.group()}</span>", result)
    return result

def render_entity_panel(entities):
    if not entities: return
    cats = [("personas","ent-person","👤 Personas"),("organizaciones","ent-org","🏛️ Organizaciones"),
            ("lugares","ent-place","📍 Lugares"),("fechas","ent-date","📅 Fechas"),("otros","ent-other","🏷️ Conceptos")]
    html_parts = []
    for key, cls, label in cats:
        items = entities.get(key, [])
        if items:
            tags = " ".join(f"<span class='{cls}'>{e}</span>" for e in items)
            html_parts.append(f"<div style='margin-bottom:10px'><div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em;color:var(--text-muted);margin-bottom:5px'>{label}</div><div style='display:flex;flex-wrap:wrap;gap:5px'>{tags}</div></div>")
    if html_parts:
        st.markdown("".join(html_parts), unsafe_allow_html=True)
    else:
        st.caption("No se detectaron entidades.")

def generate_lead(client, text, filename=""):
    if st.session_state.lead_cache is not None:
        return st.session_state.lead_cache
    system = """Eres un periodista experto. Redacta:
1. TITULAR periodístico (máx 12 palabras)
2. SUBTÍTULO (máx 20 palabras)
3. LEAD que responda Qué, Quién, Cuándo, Dónde, Por qué (máx 60 palabras)
4. CONTEXTO breve (máx 3 oraciones)
JSON: {"titular":"...","subtitulo":"...","lead":"...","contexto":"..."}"""
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": text[:10000]}],
            temperature=0.2, max_tokens=600
        )
        raw = re.sub(r"```json\s*|\s*```", "", r.choices[0].message.content.strip()).strip()
        result = json.loads(raw)
        st.session_state.lead_cache = result
        return result
    except Exception:
        fallback = {"titular":"Error al generar titular","subtitulo":"","lead":"","contexto":""}
        st.session_state.lead_cache = fallback
        return fallback

def ai_generate(client, system_prompt, user_content, max_tokens=2048, temp=0.1):
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_content}],
            temperature=temp, max_tokens=max_tokens
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

def generate_summary(client, text):
    if "summary" in st.session_state.analysis_cache: return st.session_state.analysis_cache["summary"]
    result = ai_generate(client, "Genera resumen ejecutivo en español:\n## Resumen Ejecutivo\n## Puntos Clave (máx 7)\n## Conclusiones", text[:12000])
    st.session_state.analysis_cache["summary"] = result; return result

def generate_topics(client, text):
    if "topics" in st.session_state.analysis_cache: return st.session_state.analysis_cache["topics"]
    result = ai_generate(client, "Extrae en español:\n## Temas Principales\n## Palabras Clave (10-15)\n## Categoría del Contenido", text[:12000])
    st.session_state.analysis_cache["topics"] = result; return result

def generate_action_items(client, text):
    if "actions" in st.session_state.analysis_cache: return st.session_state.analysis_cache["actions"]
    result = ai_generate(client, "Extrae en español:\n## Tareas Pendientes\n## Decisiones Tomadas\n## Preguntas Abiertas\n## Compromisos", text[:12000])
    st.session_state.analysis_cache["actions"] = result; return result

def generate_sentiment(client, text):
    if "sentiment" in st.session_state.analysis_cache: return st.session_state.analysis_cache["sentiment"]
    result = ai_generate(client, "Analiza en español:\n## Tono General\n## Sentimiento\n## Momentos Destacados\n## Formalidad (1-10)", text[:12000])
    st.session_state.analysis_cache["sentiment"] = result; return result

# ============================================================
# PROCESO PRINCIPAL DE AUDIO
# ============================================================
def process_audio(client, uploaded, model, do_correct):
    history_save_current()
    new_id = history_new_id()
    st.session_state.active_audio_id = new_id
    reset_current_audio()
    with st.status("Procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path:
            st.error("Error al guardar archivo"); return False
        size_mb = os.path.getsize(path) / (1024 * 1024)
        st.write(f"📁 {uploaded.name} — {size_mb:.1f} MB")
        st.session_state.uploaded_filename = uploaded.name
        converted_path, was_converted = convert_to_mp3(path, status_writer=status)
        if was_converted:
            st.write(f"🎵 Audio listo: {os.path.getsize(converted_path)/(1024*1024):.1f} MB")
        st.session_state.audio_path = path
        # Construir prompt con glosario de sesión
        whisper_prompt = build_whisper_prompt(session_glossary=st.session_state.session_glossary)
        n_gl = len(st.session_state.session_glossary)
        if n_gl > 0:
            st.write(f"📚 Glosario activo: {n_gl} término{'s' if n_gl != 1 else ''}")
        full_text, segments, duration_ms, coverage, gaps, chunks_used = transcribe_complete(
            client, converted_path, model, whisper_prompt=whisper_prompt, progress_status=status
        )
        if was_converted and converted_path != path:
            try: os.remove(converted_path)
            except Exception: pass
        if not full_text or not segments:
            st.error("Error en la transcripción. Si el archivo es muy largo, intenta con un fragmento más corto.")
            return False
        st.session_state.raw_transcript = full_text
        st.session_state.transcript_segments = segments
        st.session_state.audio_duration_ms = duration_ms
        st.session_state.coverage_pct = coverage
        st.session_state.transcript_gaps = gaps
        st.session_state.chunks_used = chunks_used
        if do_correct:
            st.write("✨ Corrigiendo ortografía (preservando extranjerismos)...")
            txt, csegs = correct_and_align(client, full_text, segments)
            st.session_state.transcript_text = txt
            st.session_state.corrected_segments = csegs
            st.session_state.correction_applied = True
        else:
            st.session_state.transcript_text = full_text
            st.session_state.corrected_segments = segments
            st.session_state.correction_applied = False
        st.session_state.audio_start_time = 0
        wc = len(full_text.split())
        cov_icon = "✅" if coverage >= 95 else "⚠️" if coverage >= 80 else "❌"
        chunk_info = f" · {chunks_used} partes" if chunks_used > 1 else ""
        status.update(label=f"{cov_icon} {wc:,} palabras · {len(segments)} segmentos · {coverage:.0f}% cobertura{chunk_info}",
                      state="complete", expanded=False)
    history_save_current()
    return True

# ============================================================
# VISOR DE SEGMENTOS
# ============================================================
def render_segment_viewer(segments, active_idx=-1, search_query="", max_height="580px"):
    if not segments: return
    rows_html = []
    for i, seg in enumerate(segments):
        is_active = (i == active_idx)
        ts = fmt_time(float(seg.get("start", 0)))
        text = seg.get("text", "").strip()
        if search_query:
            text = highlight_html(text, search_query)
        recovered_mark = " <span style='color:var(--amber);font-size:0.7em'>🔄</span>" if seg.get("recovered") else ""
        active_class = "active" if is_active else ""
        rows_html.append(f"<div class='seg-row {active_class}'><span class='seg-ts'>{ts}</span><span class='seg-txt'>{text}{recovered_mark}</span></div>")
    st.markdown(f"<div class='seg-viewer' style='max-height:{max_height}'>{''.join(rows_html)}</div>", unsafe_allow_html=True)

# ============================================================
# MARCADORES
# ============================================================
MARKER_COLORS = {"🔴 Importante":"#dc2626","🟡 Dato clave":"#d97706","🟢 Cierre":"#059669","🔵 Declaración":"#2563eb","⚪ Nota":"#78716c"}

def render_markers(markers, segs):
    if not markers:
        st.markdown('<div class="no-results-box" style="padding:14px">📌 Sin marcadores. Agrega uno con el botón de abajo.</div>', unsafe_allow_html=True)
        return
    for i, m in enumerate(sorted(markers, key=lambda x: x["time"])):
        color = MARKER_COLORS.get(m.get("type","⚪ Nota"), "#78716c")
        mc1, mc2, mc3 = st.columns([0.8, 4, 0.5])
        with mc1:
            if st.button(f"▶ {fmt_time(m['time'])}", key=f"mk_play_{i}"):
                seg_idx = next((j for j, s in enumerate(segs) if s.get("start",0) <= m["time"] <= s.get("end",0)), -1)
                jump_to_time(max(0, m["time"] - 1), seg_idx); st.rerun()
        with mc2:
            note_html = f"<span class='marker-note'> — {m['note']}</span>" if m.get("note") else ""
            st.markdown(f"<div class='marker-card'><span style='width:8px;height:8px;border-radius:50%;background:{color};flex-shrink:0'></span><span class='marker-label'>{m.get('type','Nota')}</span>{note_html}</div>", unsafe_allow_html=True)
        with mc3:
            if st.button("✕", key=f"mk_del_{i}", help="Eliminar marcador"):
                st.session_state.markers = [x for x in st.session_state.markers if x != m]
                history_save_current(); st.rerun()

# ============================================================
# APP PRINCIPAL
# ============================================================
def main_app():
    client = get_client()
    if not client: st.stop()
    pydub_ok, pydub_msg = check_pydub_ffmpeg()

    # ── SIDEBAR ──
    with st.sidebar:
        st.markdown("#### ⚙️ Config")
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3","whisper-large-v3-turbo"],
                             format_func=lambda x: "V3 Precisión" if "turbo" not in x else "V3 Turbo")
        do_correct = st.toggle("Corrección ortográfica", value=True)
        st.markdown("---")

        # ── GLOSARIO DE PRECISIÓN ──
        st.markdown("##### 📚 Glosario de precisión")
        st.caption("Nombres propios, apellidos y términos en inglés. Se envían a Whisper antes de cada transcripción.")
        session_gl = st.session_state.session_glossary
        if session_gl:
            gl_display = ", ".join(session_gl[:12])
            if len(session_gl) > 12: gl_display += f" +{len(session_gl)-12} más"
            st.markdown(f"<div class='glossary-box'><strong style='color:var(--primary)'>{len(session_gl)} términos:</strong> {gl_display}</div>", unsafe_allow_html=True)
        new_term = st.text_input("Agregar término", placeholder="Ej: Bedout, Uribe, off the record...",
                                  key="new_glossary_term", label_visibility="collapsed")
        g1, g2 = st.columns([3, 1])
        with g1:
            if st.button("➕ Agregar al glosario", key="add_glossary", use_container_width=True):
                term = new_term.strip()
                if term and term.lower() not in {t.lower() for t in session_gl}:
                    st.session_state.session_glossary.append(term); st.rerun()
        with g2:
            if st.button("🗑", key="clear_glossary", help="Limpiar glosario"):
                st.session_state.session_glossary = []; st.rerun()

        st.markdown("---")
        st.markdown("##### 🔍 Búsqueda")
        ctx_w = st.slider("Palabras contexto", 10, 60, 30, step=5)
        use_fuzzy = st.toggle("Aproximada (fuzzy)", value=True)
        fuzzy_t = st.slider("Sensibilidad", 0.5, 1.0, 0.75, 0.05) if use_fuzzy else 1.0
        st.markdown("---")
        if pydub_ok:
            st.markdown("<div style='font-size:0.7rem;color:#059669;background:#ecfdf5;padding:5px 9px;border-radius:6px;border:1px solid #a7f3d0'>✅ pydub + ffmpeg OK</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:0.7rem;color:#d97706;background:#fffbeb;padding:5px 9px;border-radius:6px;border:1px solid #fcd34d'>⚠️ Modo básico — {pydub_msg}</div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

    st.markdown("""<div class="app-bar"><div class="app-bar-left">
        <div class="app-logo">🎙️</div>
        <span class="app-name">Transcriptor Pro</span>
        <span class="app-tag">BETA</span>
    </div></div>""", unsafe_allow_html=True)

    hist = st.session_state.audio_history
    if hist:
        chips_html = "<div class='hist-bar'>"
        for h in hist:
            is_active = h["id"] == st.session_state.active_audio_id
            cls = "hist-chip active" if is_active else "hist-chip"
            fname = h.get("uploaded_filename","audio")[:22]
            dur = fmt_duration(get_audio_duration(h.get("corrected_segments") or []))
            chips_html += f"<span class='{cls}'><span class='hist-chip-dot'></span>{fname} <span style='opacity:0.7'>· {dur}</span></span>"
        chips_html += "</div>"
        st.markdown(chips_html, unsafe_allow_html=True)
        if len(hist) > 1:
            btn_cols = st.columns(len(hist))
            for i, h in enumerate(hist):
                with btn_cols[i]:
                    fname = h.get("uploaded_filename", f"Audio {i+1}")[:18]
                    is_active = h["id"] == st.session_state.active_audio_id
                    if not is_active:
                        if st.button(f"▶ {fname}", key=f"switch_{h['id']}", use_container_width=True):
                            history_save_current(); history_load(h["id"]); st.rerun()
                    else:
                        st.button(f"✓ {fname}", key=f"active_{h['id']}", use_container_width=True, disabled=True)

    if not st.session_state.transcript_text:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""<div class="empty-state">
                <div class="empty-state-icon">📂</div>
                <div class="empty-state-title">Sube un archivo de audio</div>
                <div class="empty-state-text">MP3, WAV, M4A, OGG o MP4 · Sin límite de duración</div>
            </div>""", unsafe_allow_html=True)
            uploaded = st.file_uploader("x", type=["mp3","wav","m4a","ogg","mp4"],
                                        label_visibility="collapsed", key="upload_initial")
            if uploaded:
                if st.button("🚀 Transcribir", type="primary", use_container_width=True):
                    if process_audio(client, uploaded, model, do_correct): st.rerun()
        return

    txt = st.session_state.transcript_text
    segs = st.session_state.corrected_segments or []
    n_words = len(txt.split())
    duration = get_audio_duration(segs)
    coverage = st.session_state.coverage_pct
    gaps = st.session_state.transcript_gaps
    chunks_used = st.session_state.chunks_used
    fname_display = st.session_state.uploaded_filename or "audio"
    wpm = round(n_words / max(duration / 60, 1)) if duration > 0 else 0
    corr_chip = "stat-chip stat-chip-ok" if st.session_state.correction_applied else "stat-chip"
    corr_text = "✓ Corregido" if st.session_state.correction_applied else "Original"
    cov_chip = "stat-chip stat-chip-ok" if coverage >= 95 else "stat-chip stat-chip-warn" if coverage >= 80 else "stat-chip"
    cov_icon = "✅" if coverage >= 95 else "⚠️" if coverage >= 80 else "❌"
    chunk_html = f'<span class="stat-chip">✂️ <strong>{chunks_used}</strong> partes</span>' if chunks_used > 1 else ""
    gap_html = f'<span class="stat-chip stat-chip-warn">🕳️ <strong>{len(gaps)}</strong> huecos</span>' if gaps else ""

    st.markdown(f"""<div class="stats-bar">
        <span class="stat-chip">📁 <strong>{fname_display}</strong></span>
        <span class="stat-chip">⏱️ <strong>{fmt_duration(duration)}</strong></span>
        <span class="stat-chip"><strong>{n_words:,}</strong> palabras</span>
        <span class="stat-chip"><strong>{wpm}</strong> pal/min</span>
        <span class="{cov_chip}">{cov_icon} <strong>{coverage:.0f}%</strong></span>
        <span class="{corr_chip}">{corr_text}</span>
        {chunk_html}{gap_html}
    </div>""", unsafe_allow_html=True)

    if coverage < 100:
        cov_class = "coverage-ok" if coverage >= 95 else "coverage-warn" if coverage >= 80 else "coverage-bad"
        st.markdown(f'<div class="coverage-bar-container"><div class="coverage-bar-fill {cov_class}" style="width:{coverage}%">{coverage:.1f}%</div></div>', unsafe_allow_html=True)

    tab_busqueda, tab_redaccion, tab_global, tab_chat, tab_analisis, tab_export = st.tabs([
        "🔍 Búsqueda","✍️ Redacción","🌐 Global","💬 Chat IA","📊 Análisis","📥 Exportar"
    ])

    # ════════════════════════════════════════════════════
    # TAB: REDACCIÓN
    # ════════════════════════════════════════════════════
    with tab_redaccion:
        lead_col1, lead_col2 = st.columns([2, 1])
        with lead_col1:
            if st.button("📰 Generar Titular y Lead", type="primary"):
                with st.spinner("Redactando..."): generate_lead(client, txt, fname_display)
            if st.session_state.lead_cache:
                lead = st.session_state.lead_cache
                st.markdown(f"""<div class="lead-box">
                    <div class="lead-label">📰 Titular</div>
                    <div class="lead-titular">{lead.get('titular','')}</div>
                    <div class="lead-subtitular">{lead.get('subtitulo','')}</div>
                    <div class="lead-label">🔰 Lead</div>
                    <div class="lead-body">{lead.get('lead','')}</div>
                    <div style="margin-top:10px"><div class="lead-label">🗂️ Contexto</div>
                    <div class="lead-body">{lead.get('contexto','')}</div></div>
                </div>""", unsafe_allow_html=True)
        with lead_col2:
            if st.button("🏷️ Extraer Entidades", type="primary", use_container_width=True):
                with st.spinner("Extrayendo..."): extract_entities(client, txt)
            if st.session_state.entities is not None:
                render_entity_panel(st.session_state.entities)

        st.markdown("---")
        st.markdown("<div class='panel-header'>Vista de dos paneles — Audio y Transcripción</div>", unsafe_allow_html=True)
        panel_audio, panel_trans = st.columns([1, 1], gap="medium")

        with panel_audio:
            st.markdown("<div class='panel-header'>🎵 Reproductor</div>", unsafe_allow_html=True)
            if st.session_state.audio_path:
                _start = st.session_state.get("_audio_start_actual", st.session_state.audio_start_time)
                st.audio(st.session_state.audio_path, start_time=_start)
            st.markdown("<div class='panel-header' style='margin-top:10px'>📌 Marcadores</div>", unsafe_allow_html=True)
            show_mk_form = st.checkbox("➕ Agregar marcador", value=False, key="show_mk_form")
            if show_mk_form:
                mk_col1, mk_col2 = st.columns([1, 1])
                with mk_col1:
                    mk_time_str = st.text_input("⏱ Tiempo", value=fmt_time(st.session_state.audio_start_time),
                                                key="mk_time_input", placeholder="1:23", help="Formato M:SS o H:MM:SS")
                with mk_col2:
                    mk_type = st.selectbox("🏷 Tipo", list(MARKER_COLORS.keys()), key="mk_type")
                mk_note = st.text_input("📝 Nota (opcional)", key="mk_note", placeholder="Describe este momento...")
                if st.button("📌 Guardar marcador", use_container_width=True, type="primary"):
                    try:
                        parts_t = mk_time_str.strip().split(":")
                        if len(parts_t) == 2: mk_sec = int(parts_t[0]) * 60 + float(parts_t[1])
                        elif len(parts_t) == 3: mk_sec = int(parts_t[0]) * 3600 + int(parts_t[1]) * 60 + float(parts_t[2])
                        else: mk_sec = float(mk_time_str)
                        st.session_state.markers.append({"time": mk_sec, "type": mk_type, "note": mk_note.strip()})
                        st.session_state.markers.sort(key=lambda x: x["time"])
                        history_save_current(); st.session_state.show_mk_form = False; st.rerun()
                    except Exception:
                        st.error("Formato inválido. Usa M:SS — ejemplo: 1:23 o 0:45")
            render_markers(st.session_state.markers, segs)

        with panel_trans:
            st.markdown("<div class='panel-header'>📄 Transcripción</div>", unsafe_allow_html=True)
            view_mode = st.radio("Vista", ["Texto","Segmentos"], horizontal=True,
                                 label_visibility="collapsed", key="view_mode_redaccion")
            active_idx = st.session_state.active_segment_idx
            show_ents = st.checkbox("Resaltar entidades", value=False, key="show_ents_redaccion",
                                    disabled=(st.session_state.entities is None))
            if view_mode == "Texto":
                display_txt = txt
                if show_ents and st.session_state.entities:
                    display_txt = highlight_entities_in_text(display_txt, st.session_state.entities)
                st.markdown(f"<div class='full-text-box'>{display_txt}</div>", unsafe_allow_html=True)
            else:
                if 0 <= active_idx < len(segs):
                    seg_active = segs[active_idx]
                    st.caption(f"▶ {fmt_time(seg_active.get('start',0))} — {seg_active.get('text','')[:70]}...")
                render_segment_viewer(segs, active_idx=active_idx, max_height="560px")
                if segs and active_idx >= 0:
                    nav1, nav2 = st.columns(2)
                    with nav1:
                        if st.button("⏮ Anterior", disabled=(active_idx <= 0), key="nav_prev_red"):
                            new_idx = max(0, active_idx - 1)
                            jump_to_time(float(segs[new_idx].get("start",0)), new_idx); st.rerun()
                    with nav2:
                        if st.button("⏭ Siguiente", disabled=(active_idx >= len(segs)-1), key="nav_next_red"):
                            new_idx = min(len(segs)-1, active_idx+1)
                            jump_to_time(float(segs[new_idx].get("start",0)), new_idx); st.rerun()

    # ════════════════════════════════════════════════════
    # TAB: BÚSQUEDA
    # ════════════════════════════════════════════════════
    with tab_busqueda:
        def execute_search():
            q = (st.session_state.get("q_input") or st.session_state.get("q_input_0") or "").strip()
            if q:
                st.session_state.last_search_query = q
                st.session_state._search_pending = True

        if st.session_state.audio_path:
            _start = st.session_state.get("_audio_start_actual", st.session_state.audio_start_time)
            st.audio(st.session_state.audio_path, start_time=_start)

        # Limpiar campo de búsqueda: usar key dinámica para forzar reset
        q_key = "q_input_0" if st.session_state.get("_clear_q") else "q_input"
        if st.session_state.get("_clear_q"):
            st.session_state._clear_q = False
        sq1, sq2 = st.columns([5, 0.7])
        with sq1:
            st.text_input("q", placeholder="🔍 Buscar palabra o frase... (Enter para buscar)",
                          label_visibility="collapsed", key=q_key, on_change=execute_search)
        with sq2:
            if st.button("✕ Limpiar", key="clear_search", use_container_width=True):
                st.session_state.search_results = None
                st.session_state.last_search_query = ""
                st.session_state._clear_q = True
                st.rerun()

        if st.session_state.get("_search_pending"):
            sq = st.session_state.last_search_query
            st.session_state.search_results = search_segments(
                sq, st.session_state.transcript_segments, st.session_state.corrected_segments,
                context_words=ctx_w, fuzzy_thresh=fuzzy_t if use_fuzzy else 1.0
            )
            st.session_state._search_pending = False

        aq = st.session_state.last_search_query
        res = st.session_state.search_results

        if aq and res:
            total_occ = count_occurrences(txt, aq)
            st.caption(f"**{len(res)}** resultado{'s' if len(res)!=1 else ''} ({total_occ} ocurrencia{'s' if total_occ!=1 else ''}) para **{aq}**")
            for i, r in enumerate(res):
                badge_cls = f"sr-badge-{r.get('confidence','low')}"
                bh = f"<span class='sr-ctx'>...{r.get('before','')} </span>" if r.get('before') else ""
                ah = f"<span class='sr-ctx'> {r.get('after','')}...</span>" if r.get('after') else ""
                expanded_ctx = ""
                if r.get('prev_segment') or r.get('next_segment'):
                    ctx_parts = []
                    if r.get('prev_segment'): ctx_parts.append(f"<span class='sr-ctx'>↑ {highlight_html(r['prev_segment'],aq)}</span>")
                    if r.get('next_segment'): ctx_parts.append(f"<span class='sr-ctx'>↓ {highlight_html(r['next_segment'],aq)}</span>")
                    expanded_ctx = f"<div class='sr-segment-full'>{'<br>'.join(ctx_parts)}</div>"
                rc1, rc2 = st.columns([0.65, 5])
                with rc1:
                    if st.button(f"▶ {r.get('time_label','0:00')}", key=f"p_{i}_{r.get('idx',i)}"):
                        jump_to_time(max(0, r.get("start_time",0)-2), r.get("idx",-1)); st.rerun()
                with rc2:
                    st.markdown(f"""<div class="sr-card">
                        <div class="sr-head">
                            <span class="sr-time">{r.get('time_label','0:00')} → {r.get('end_label','')}</span>
                            <span class="sr-badge {badge_cls}">{r.get('confidence','low')}</span>
                        </div>
                        <div class="sr-body">{bh}{r.get('match_hl','')}{ah}</div>
                        {expanded_ctx}
                    </div>""", unsafe_allow_html=True)
        elif aq and res is not None and len(res) == 0:
            st.markdown('<div class="no-results-box">🔍 Sin resultados. Prueba con otras palabras o activa búsqueda aproximada en el sidebar.</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("##### 📄 Texto completo")
        if aq:
            total_in_text = count_occurrences(txt, aq)
            if total_in_text > 0:
                st.caption(f"🔶 {total_in_text} ocurrencia{'s' if total_in_text!=1 else ''} resaltada{'s' if total_in_text!=1 else ''}")
        hl_txt = highlight_full_text(txt, aq) if aq else txt
        st.markdown(f"<div class='full-text-box'>{hl_txt}</div>", unsafe_allow_html=True)

        if gaps:
            st.markdown("---")
            with st.expander(f"⚠️ {len(gaps)} hueco{'s' if len(gaps)!=1 else ''} detectado{'s' if len(gaps)!=1 else ''}", expanded=False):
                st.caption("Secciones sin habla (silencio, música o ruido)")
                for gap in gaps:
                    gc1, gc2 = st.columns([3, 1])
                    with gc1:
                        st.markdown(f"`{fmt_time(gap['start'])}` → `{fmt_time(gap['end'])}` — **{gap['duration']:.1f}s**")
                    with gc2:
                        if st.button("▶ ir", key=f"gap_{gap['start']:.0f}"):
                            jump_to_time(max(0, gap["start"]-1)); st.rerun()

        st.markdown("---")
        show_new_b = st.checkbox("📂 Agregar otro audio", value=False, key="show_new_busqueda")
        if show_new_b:
            if len(hist) >= MAX_HISTORY:
                st.warning(f"Historial lleno ({MAX_HISTORY} audios).")
            else:
                new_file_b = st.file_uploader("xb", type=["mp3","wav","m4a","ogg","mp4"],
                                              label_visibility="collapsed", key="upload_new_b")
                if new_file_b:
                    if st.button("🔄 Procesar", type="primary", use_container_width=True, key="proc_b"):
                        if process_audio(client, new_file_b, model, do_correct): st.rerun()

    # ════════════════════════════════════════════════════
    # TAB: BÚSQUEDA GLOBAL
    # ════════════════════════════════════════════════════
    with tab_global:
        if len(hist) <= 1:
            st.markdown("""<div class="empty-state">
                <div class="empty-state-icon">🌐</div>
                <div class="empty-state-title">Agrega más audios para buscar entre todos</div>
                <div class="empty-state-text">Necesitas al menos 2 audios en el historial</div>
            </div>""", unsafe_allow_html=True)
        else:
            def execute_global_search():
                q = st.session_state.get("gq_input","").strip()
                if q:
                    st.session_state.last_global_query = q
                    st.session_state._global_search_pending = True
                else:
                    st.session_state.global_search_results = None
                    st.session_state.last_global_query = ""

            st.text_input("gq", placeholder=f"Buscar en todos los audios ({len(hist)} archivos)...",
                          label_visibility="collapsed", key="gq_input", on_change=execute_global_search)
            if st.session_state.get("_global_search_pending"):
                st.session_state.global_search_results = global_search(
                    st.session_state.last_global_query, hist,
                    fuzzy_thresh=fuzzy_t if use_fuzzy else 1.0
                )
                st.session_state._global_search_pending = False
            gres = st.session_state.global_search_results
            gaq = st.session_state.last_global_query
            if gaq and gres:
                st.caption(f"**{len(gres)}** resultado{'s' if len(gres)!=1 else ''} en {len(hist)} archivos para **{gaq}**")
                by_file = {}
                for r in gres:
                    by_file.setdefault(r.get("audio_name","audio"), []).append(r)
                for fname, file_results in by_file.items():
                    with st.expander(f"📁 {fname} — {len(file_results)} resultado{'s' if len(file_results)!=1 else ''}", expanded=True):
                        for i, r in enumerate(file_results):
                            badge_cls = f"sr-badge-{r.get('confidence','low')}"
                            bh = f"<span class='sr-ctx'>...{r.get('before','')} </span>" if r.get('before') else ""
                            ah = f"<span class='sr-ctx'> {r.get('after','')}...</span>" if r.get('after') else ""
                            gc1, gc2 = st.columns([0.8, 5])
                            with gc1:
                                if st.button("▶ ir", key=f"gp_{fname}_{i}", help=f"Ir a {r.get('time_label','')} en {fname}"):
                                    aid = r.get("audio_id","")
                                    if aid != st.session_state.active_audio_id:
                                        history_save_current(); history_load(aid)
                                    jump_to_time(max(0, r.get("start_time",0)-2), r.get("idx",-1)); st.rerun()
                            with gc2:
                                st.markdown(f"""<div class="sr-card sr-card-global">
                                    <div class="sr-head"><span class="sr-time">{r.get('time_label','')}</span>
                                    <span class="sr-badge {badge_cls}">{r.get('confidence','low')}</span></div>
                                    <div class="sr-body">{bh}{r.get('match_hl','')}{ah}</div>
                                </div>""", unsafe_allow_html=True)
            elif gaq and gres is not None and len(gres) == 0:
                st.markdown('<div class="no-results-box">🔍 Sin resultados en ningún archivo.</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### 📚 Audios en sesión")
            for h in hist:
                is_active = h["id"] == st.session_state.active_audio_id
                dur = fmt_duration(get_audio_duration(h.get("corrected_segments") or []))
                wc = len((h.get("transcript_text") or "").split())
                cov = h.get("coverage_pct", 0)
                active_mark = " ← activo" if is_active else ""
                hc1, hc2, hc3 = st.columns([3, 1, 1])
                with hc1:
                    st.markdown(f"<div class='hist-card {'active' if is_active else ''}'><div class='hist-card-name'>📁 {h.get('uploaded_filename','audio')}{active_mark}</div><div class='hist-card-meta'>⏱ {dur} · {wc:,} palabras · {cov:.0f}% cobertura</div></div>", unsafe_allow_html=True)
                with hc2:
                    if not is_active:
                        if st.button("Cargar", key=f"hist_load_{h['id']}"):
                            history_save_current(); history_load(h["id"]); st.rerun()
                with hc3:
                    if st.button("🗑", key=f"hist_del_{h['id']}", help="Eliminar del historial"):
                        st.session_state.audio_history = [x for x in st.session_state.audio_history if x["id"] != h["id"]]
                        if is_active and st.session_state.audio_history:
                            history_load(st.session_state.audio_history[-1]["id"])
                        elif not st.session_state.audio_history:
                            reset_current_audio(); st.session_state.active_audio_id = None
                        st.rerun()

    # ════════════════════════════════════════════════════
    # TAB: CHAT IA
    # ════════════════════════════════════════════════════
    with tab_chat:
        if not st.session_state.chat_history:
            st.markdown("""<div class="empty-state" style="padding:20px">
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-title">Pregunta sobre el audio activo</div>
                <div class="empty-state-text">Responde con timestamps y citas exactas</div>
            </div>""", unsafe_allow_html=True)
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Pregunta sobre el audio..."):
            st.session_state.chat_history.append({"role":"user","content":prompt})
            with st.chat_message("user"): st.markdown(prompt)
            with st.chat_message("assistant"):
                ph = st.empty(); full = ""
                try:
                    segs_ctx = st.session_state.corrected_segments or st.session_state.transcript_segments or []
                    ts_ctx = build_timestamped_transcript(segs_ctx)
                    if len(ts_ctx) > 15000: ts_ctx = ts_ctx[:15000] + "\n[...truncado...]"
                    entities_ctx = ""
                    if st.session_state.entities:
                        e = st.session_state.entities
                        entities_ctx = f"\n\nENTIDADES:\nPersonas: {', '.join(e.get('personas',[]))}\nOrgs: {', '.join(e.get('organizaciones',[]))}\nLugares: {', '.join(e.get('lugares',[]))}"
                    system_prompt = (
                        "Eres un asistente periodístico. Responde SOLO con info de la transcripción.\n"
                        "1. Solo información explícita.\n2. Incluye timestamp [MM:SS].\n"
                        "3. Si no está: 'No encontré esa información.'\n4. NO inventes.\n"
                        f"\nTRANSCRIPCIÓN:{ts_ctx}{entities_ctx}"
                    )
                    stream = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role":"system","content":system_prompt},
                                  *[{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history[-6:]]],
                        stream=True, max_tokens=2048, temperature=0.1,
                    )
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            full += chunk.choices[0].delta.content
                            ph.markdown(full + "▌")
                    ph.markdown(full)
                    st.session_state.chat_history.append({"role":"assistant","content":full})
                except Exception as e:
                    st.error(f"Error: {e}")
        if st.session_state.chat_history:
            if st.button("🗑️ Limpiar conversación"):
                st.session_state.chat_history = []; st.rerun()

    # ════════════════════════════════════════════════════
    # TAB: ANÁLISIS
    # ════════════════════════════════════════════════════
    with tab_analisis:
        chars = len(txt)
        sentences = len(re.split(r'[.!?]+', txt))
        wpm_a = round(n_words / max(duration / 60, 1)) if duration > 0 else 0
        st.markdown(f"""<div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-value">{n_words:,}</div><div class="kpi-label">Palabras</div></div>
            <div class="kpi-card"><div class="kpi-value">{sentences}</div><div class="kpi-label">Oraciones</div></div>
            <div class="kpi-card"><div class="kpi-value">{chars:,}</div><div class="kpi-label">Caracteres</div></div>
            <div class="kpi-card"><div class="kpi-value">{wpm_a}</div><div class="kpi-label">Pal/min</div></div>
            <div class="kpi-card"><div class="kpi-value">{fmt_duration(duration)}</div><div class="kpi-label">Duración</div></div>
            <div class="kpi-card"><div class="kpi-value">{coverage:.0f}%</div><div class="kpi-label">Cobertura</div></div>
        </div>""", unsafe_allow_html=True)

        st.markdown("---")
        an1, an2 = st.columns(2)
        with an1:
            if st.button("📝 Resumen", use_container_width=True, type="primary"):
                with st.spinner("Generando..."): generate_summary(client, txt)
            if "summary" in st.session_state.analysis_cache:
                with st.expander("📝 Resumen", expanded=True): st.markdown(st.session_state.analysis_cache["summary"])
        with an2:
            if st.button("🏷️ Temas", use_container_width=True, type="primary"):
                with st.spinner("Extrayendo..."): generate_topics(client, txt)
            if "topics" in st.session_state.analysis_cache:
                with st.expander("🏷️ Temas", expanded=True): st.markdown(st.session_state.analysis_cache["topics"])
        st.markdown("---")
        an3, an4 = st.columns(2)
        with an3:
            if st.button("✅ Tareas y Decisiones", use_container_width=True):
                with st.spinner("Extrayendo..."): generate_action_items(client, txt)
            if "actions" in st.session_state.analysis_cache:
                with st.expander("✅ Tareas", expanded=True): st.markdown(st.session_state.analysis_cache["actions"])
        with an4:
            if st.button("🎭 Análisis de Tono", use_container_width=True):
                with st.spinner("Analizando..."): generate_sentiment(client, txt)
            if "sentiment" in st.session_state.analysis_cache:
                with st.expander("🎭 Tono", expanded=True): st.markdown(st.session_state.analysis_cache["sentiment"])

        # ── PALABRAS MÁS FRECUENTES — diseño expandido con soporte EN ──
        st.markdown("---")
        st.markdown("##### 📈 Palabras más frecuentes")
        stopwords_es = {
            'de','la','que','el','en','y','a','los','del','se','las','por','un','para','con',
            'no','una','su','al','lo','como','más','pero','sus','le','ya','o','este','sí',
            'porque','esta','entre','cuando','muy','sin','sobre','también','me','hasta','hay',
            'donde','quien','desde','todo','nos','durante','todos','uno','les','ni','contra',
            'otros','ese','eso','ante','ellos','esto','antes','algunos','qué','unos','yo',
            'otro','otras','otra','él','tanto','esa','estos','mucho','quienes','nada','muchos',
            'cual','poco','ella','estar','estas','algunas','algo','nosotros','mi','mis','tú',
            'te','ti','tu','tus','ellas','nosotras','vosotros','vosotras','os','es','son',
            'fue','ser','ha','han','era','sido','tiene','puede','hacer','cada','hemos',
            'vamos','va','así','pues','bueno','entonces','después','ahora','aquí','bien',
            'sólo','solo','vez','esas','dos','tres','mas','sea','si','he','tal','esos','tan',
        }
        # Palabras en español
        words_es = re.findall(r'\b[a-záéíóúñü]{3,}\b', txt.lower())
        # Palabras en inglés del glosario periodístico que aparecen en el texto
        txt_lower = txt.lower()
        word_freq = {}
        for w in words_es:
            if w not in stopwords_es:
                word_freq[w] = word_freq.get(w, 0) + 1
        # Añadir términos EN detectados en el texto
        for en_word in _EN_JOURNALISM_WORDS:
            if " " not in en_word and en_word in txt_lower:
                count = len(re.findall(r'\b' + re.escape(en_word) + r'\b', txt_lower))
                if count > 0:
                    word_freq[en_word] = word_freq.get(en_word, 0) + count

        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:25]
        if top_words:
            max_freq = top_words[0][1]
            # Detectar cuáles son términos en inglés
            en_in_text = {w for w in _EN_JOURNALISM_WORDS if " " not in w and w in txt_lower}
            bars_html = []
            for word, freq in top_words:
                pct = max(4, round((freq / max_freq) * 100))
                is_en = word in en_in_text
                lang_tag = " <span class='lang-en'>EN</span>" if is_en else ""
                # Azul para inglés, naranja para español
                bar_color = "linear-gradient(90deg,#bfdbfe,#3b82f6)" if is_en else "linear-gradient(90deg,#fed7aa,#ea580c)"
                count_in_bar = str(freq) if pct >= 22 else ""
                bars_html.append(
                    f"<div class='freq-bar-row'>"
                    f"<span class='freq-bar-label'>{word}{lang_tag}</span>"
                    f"<div class='freq-bar-track'>"
                    f"<div class='freq-bar-fill' style='width:{pct}%;background:{bar_color}'>{count_in_bar}</div>"
                    f"</div>"
                    f"<span class='freq-bar-count'>{freq}</span>"
                    f"</div>"
                )
            st.markdown("".join(bars_html), unsafe_allow_html=True)
            if en_in_text and any(w in en_in_text for w, _ in top_words):
                st.markdown(
                    "<div style='margin-top:8px;font-size:0.7rem;color:var(--text-muted);display:flex;align-items:center;gap:8px'>"
                    "<span class='lang-en'>EN</span> <span>= término en inglés</span>&nbsp;"
                    "<span style='display:inline-block;width:14px;height:8px;border-radius:2px;background:linear-gradient(90deg,#fed7aa,#ea580c)'></span> <span>español</span>&nbsp;"
                    "<span style='display:inline-block;width:14px;height:8px;border-radius:2px;background:linear-gradient(90deg,#bfdbfe,#3b82f6)'></span> <span>inglés</span>"
                    "</div>", unsafe_allow_html=True
                )

    # ════════════════════════════════════════════════════
    # TAB: EXPORTAR
    # ════════════════════════════════════════════════════
    with tab_export:
        st.markdown("##### 📥 Exportar transcripción activa")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button("📄 Texto plano (.txt)", data=txt,
                               file_name=f"{fname_display}_transcripcion.txt", mime="text/plain", use_container_width=True)
        with c2:
            srt = []
            for i, seg in enumerate(segs):
                s, e = float(seg.get("start",0)), float(seg.get("end",0))
                srt.extend([f"{i+1}",
                    f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{s%60:06.3f} --> {int(e//3600):02d}:{int((e%3600)//60):02d}:{e%60:06.3f}",
                    seg.get("text",""), ""])
            st.download_button("🎬 Subtítulos (.srt)", data="\n".join(srt),
                               file_name=f"{fname_display}.srt", mime="text/plain", use_container_width=True)
        with c3:
            ts_lines = [f"[{fmt_time(float(seg.get('start',0)))}] {seg.get('text','')}" for seg in segs]
            st.download_button("⏱️ Con timestamps (.txt)", data="\n".join(ts_lines),
                               file_name=f"{fname_display}_timestamps.txt", mime="text/plain", use_container_width=True)
        st.markdown("---")
        c4, c5 = st.columns(2)
        with c4:
            json_data = {"filename":fname_display,"date":datetime.now().isoformat(),"duration_seconds":duration,
                         "word_count":n_words,"coverage_percent":coverage,"chunks_used":chunks_used,"gaps":gaps,
                         "correction_applied":st.session_state.correction_applied,"markers":st.session_state.markers,
                         "entities":st.session_state.entities,"lead":st.session_state.lead_cache,
                         "full_text":txt,"segments":segs}
            st.download_button("🗂️ Datos completos (.json)", data=json.dumps(json_data, ensure_ascii=False, indent=2),
                               file_name=f"{fname_display}.json", mime="application/json", use_container_width=True)
        with c5:
            if st.session_state.analysis_cache or st.session_state.lead_cache:
                analysis_export = {"filename":fname_display,"date":datetime.now().isoformat(),
                                   "lead":st.session_state.lead_cache,"entities":st.session_state.entities,
                                   "analyses":st.session_state.analysis_cache}
                st.download_button("📊 Análisis + Lead (.json)", data=json.dumps(analysis_export, ensure_ascii=False, indent=2),
                                   file_name=f"{fname_display}_analisis.json", mime="application/json", use_container_width=True)
            else:
                st.button("📊 Análisis + Lead (.json)", disabled=True, use_container_width=True,
                          help="Genera al menos un análisis o lead primero")

        if len(hist) > 1:
            st.markdown("---")
            st.markdown("##### 📦 Exportar sesión completa")
            session_export = {"session_date":datetime.now().isoformat(),"total_audios":len(hist),
                "audios":[{"filename":h.get("uploaded_filename"),"duration_seconds":get_audio_duration(h.get("corrected_segments") or []),
                           "word_count":len((h.get("transcript_text") or "").split()),"coverage_percent":h.get("coverage_pct",0),
                           "full_text":h.get("transcript_text",""),"lead":h.get("lead_cache"),"entities":h.get("entities"),
                           "markers":h.get("markers",[])} for h in hist]}
            st.download_button("📦 Exportar toda la sesión (.json)",
                               data=json.dumps(session_export, ensure_ascii=False, indent=2),
                               file_name="sesion_completa.json", mime="application/json", use_container_width=True)

        st.markdown("---")
        if st.checkbox("Ver segmentos con timestamps", value=False, key="show_ts_export"):
            for seg in segs:
                t_start = fmt_time(float(seg.get('start',0)))
                sc1, sc2 = st.columns([0.8, 5])
                with sc1: st.caption(f"`{t_start}`")
                with sc2:
                    recovered_tag = " 🔄" if seg.get("recovered") else ""
                    st.markdown(f"<span style='font-size:0.82rem'>{seg.get('text','')}{recovered_tag}</span>", unsafe_allow_html=True)

# ── ENTRY POINT ──
if __name__ == "__main__":
    if check_password():
        main_app()
