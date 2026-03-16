import streamlit as st
import os
import tempfile
import unicodedata
from groq import Groq
from difflib import SequenceMatcher
import re

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Transcriptor Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

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
        --radius: 12px;
        --radius-sm: 8px;
        --radius-xs: 6px;
        --shadow-xs: 0 1px 2px rgba(0,0,0,0.04);
        --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
        --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.06), 0 2px 4px -2px rgba(0,0,0,0.04);
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
    code, .mono { font-family: 'JetBrains Mono', monospace !important; }

    .main .block-container {
        padding: 0.5rem 1.5rem 1rem 1.5rem;
        max-width: 1200px;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* Ocultar TODOS los labels de uploaders, toggles, sliders internos */
    .stFileUploader > label,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > span,
    .uploadedFileName { font-size: 0.78rem !important; }

    /* Ocultar textos fantasma de expander arrow */
    details > summary > span > div[data-testid="stMarkdownContainer"] > p {
        font-size: 0.85rem !important;
    }

    /* LOGIN */
    .login-icon {
        width: 56px; height: 56px;
        background: linear-gradient(135deg, #ea580c, #dc2626);
        border-radius: 16px;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 24px; margin-bottom: 16px;
    }
    .login-title { font-size: 1.25rem; font-weight: 700; color: var(--text); margin: 0 0 4px 0; }
    .login-subtitle { font-size: 0.85rem; color: var(--text-secondary); margin: 0 0 24px 0; }

    /* HEADER */
    .app-bar { display: flex; align-items: center; padding: 8px 0; margin-bottom: 8px; }
    .app-bar-left { display: flex; align-items: center; gap: 10px; }
    .app-logo {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #ea580c, #dc2626);
        border-radius: 10px; display: flex; align-items: center; justify-content: center;
        font-size: 18px; color: white;
    }
    .app-name { font-size: 1.1rem; font-weight: 700; color: var(--text); }
    .app-tag {
        font-size: 0.6rem; background: var(--primary-light); color: var(--primary);
        padding: 2px 8px; border-radius: 20px; font-weight: 600; text-transform: uppercase;
    }

    /* STATS */
    .stats-bar { display: flex; gap: 8px; flex-wrap: wrap; margin: 6px 0 10px 0; }
    .stat-chip {
        display: inline-flex; align-items: center; gap: 4px;
        font-size: 0.72rem; color: var(--text-secondary);
        background: var(--bg); padding: 4px 10px; border-radius: 20px;
        border: 1px solid var(--border); font-weight: 500;
    }
    .stat-chip strong { color: var(--text); font-weight: 600; }
    .stat-chip-ok { background: var(--green-bg); color: var(--green); border-color: #a7f3d0; }

    /* RESULTADOS */
    .sr-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 10px 14px;
        margin-bottom: 6px; box-shadow: var(--shadow-xs); transition: var(--transition);
    }
    .sr-card:hover { border-color: var(--primary-subtle); box-shadow: var(--shadow-sm); }
    .sr-head { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
    .sr-time {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.7rem; font-weight: 500; color: var(--primary);
        background: var(--primary-light); padding: 2px 8px; border-radius: 4px;
    }
    .sr-badge {
        font-size: 0.6rem; font-weight: 700; padding: 1px 6px;
        border-radius: 4px; text-transform: uppercase;
    }
    .sr-badge-high { background: var(--green-bg); color: var(--green); }
    .sr-badge-medium { background: var(--amber-bg); color: var(--amber); }
    .sr-badge-low { background: var(--red-bg); color: var(--red); }
    .sr-body { font-size: 0.82rem; line-height: 1.6; color: var(--text); }
    .sr-ctx { color: var(--text-muted); }

    .hl {
        background: linear-gradient(120deg, #fed7aa, #fdba74);
        color: var(--text); padding: 1px 4px; border-radius: 3px; font-weight: 600;
    }

    /* TEXTO COMPLETO */
    .full-text-box {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 16px 20px;
        font-size: 0.85rem; line-height: 1.85; color: var(--text);
        max-height: 380px; overflow-y: auto;
    }
    .full-text-box::-webkit-scrollbar { width: 5px; }
    .full-text-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

    /* EMPTY */
    .empty-state { text-align: center; padding: 40px 20px; color: var(--text-muted); }
    .empty-state-icon { font-size: 2.5rem; margin-bottom: 8px; opacity: 0.6; }
    .empty-state-title { font-size: 0.95rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
    .empty-state-text { font-size: 0.8rem; color: var(--text-muted); }

    .no-results-box {
        text-align: center; padding: 20px; color: var(--text-secondary);
        background: var(--bg); border-radius: var(--radius-sm); border: 1px dashed var(--border);
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0; background: var(--bg); border-radius: var(--radius-sm);
        padding: 3px; border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.8rem; font-weight: 500; padding: 6px 16px;
        color: var(--text-secondary); border-radius: var(--radius-xs);
        border-bottom: none !important; background: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important; background: var(--surface) !important;
        box-shadow: var(--shadow-xs) !important; border-bottom: none !important;
    }
    .stTabs [data-baseweb="tab-panel"] { padding-top: 10px; }
    .stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

    section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }

    .stButton > button { border-radius: var(--radius-xs) !important; font-weight: 500 !important; font-size: 0.82rem !important; }
    .stButton > button[kind="primary"] { background: var(--primary) !important; border: none !important; }
    .stButton > button[kind="primary"]:hover { background: var(--primary-hover) !important; }

    .stTextInput > div > div > input {
        border-radius: var(--radius-xs) !important; border-color: var(--border) !important; font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.1) !important;
    }

    .stAudio { margin: 4px 0 8px 0; }
    .stChatMessage { font-size: 0.88rem; }
    hr { border-color: var(--border) !important; margin: 8px 0 !important; }
</style>
""", unsafe_allow_html=True)


# --- SESSION STATE ---
DEFAULTS = {
    "authenticated": False,
    "transcript_text": None,
    "transcript_segments": None,
    "corrected_segments": None,
    "raw_transcript": None,
    "audio_path": None,
    "audio_start_time": 0,
    "chat_history": [],
    "search_results": None,
    "last_search_query": "",
    "correction_applied": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# --- UTILIDADES ---
def fmt_time(seconds):
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def norm(text):
    if not text:
        return ""
    t = unicodedata.normalize('NFD', text)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return t.lower().strip()


def highlight_html(text, query):
    if not query or not text:
        return text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(text):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", text)
    result = text
    for w in query.split():
        if len(w) > 2:
            wp = re.compile(re.escape(w), re.IGNORECASE)
            result = wp.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    return result


# --- AUTH ---
def check_password():
    if st.session_state.authenticated:
        return True

    def do_login():
        pwd = st.session_state.get("_pwd_input", "")
        if not pwd:
            return
        try:
            if pwd == st.secrets["general"]["app_password"]:
                st.session_state.authenticated = True
            else:
                st.session_state._login_error = "Contraseña incorrecta"
        except Exception:
            st.session_state._login_error = "Error de configuración"

    st.markdown("<div style='height:12vh'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1, 1.2])
    with col2:
        st.markdown("""
        <div style="text-align:center">
            <div class="login-icon">🎙️</div>
            <p class="login-title">Transcriptor Pro</p>
            <p class="login-subtitle">Ingresa tu contraseña para continuar</p>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "pwd", type="password", label_visibility="collapsed",
            placeholder="Contraseña...", key="_pwd_input", on_change=do_login
        )
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


# --- AUDIO ---
def save_uploaded(f):
    try:
        safe = "".join(c for c in f.name if c.isalnum() or c in "._-") or "audio.mp3"
        path = os.path.join(tempfile.gettempdir(), f"up_{safe}")
        with open(path, "wb") as fp:
            fp.write(f.getbuffer())
        return path
    except Exception:
        return None


def transcribe(client, path, model):
    try:
        with open(path, "rb") as f:
            t = client.audio.transcriptions.create(
                file=(os.path.basename(path), f.read()),
                model=model, response_format="verbose_json",
                language="es", temperature=0.0
            )
        segments_list = []
        if t.segments:
            for seg in t.segments:
                if isinstance(seg, dict):
                    s, e, tx = seg.get("start", 0), seg.get("end", 0), seg.get("text", "")
                else:
                    s, e, tx = getattr(seg, "start", 0), getattr(seg, "end", 0), getattr(seg, "text", "")
                segments_list.append({"start": float(s), "end": float(e), "text": str(tx).strip()})
        return t.text, segments_list
    except Exception as e:
        st.error(f"Error de transcripción: {e}")
        return None, None


# --- CORRECCIÓN ---
def _correct_chunk(client, text):
    prompt = ("Eres un corrector ortográfico. SOLO corrige tildes, mayúsculas y puntuación. "
              "NO cambies, elimines ni agregues palabras. Devuelve únicamente el texto corregido.")
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
    if total_orig == 0:
        return original_segments
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


# --- BÚSQUEDA ---
def search_segments(query, segments, corrected_segments, context_words=20, fuzzy_thresh=0.75):
    if not query:
        return []
    target = corrected_segments if corrected_segments else segments
    if not target:
        return []
    q_norm = norm(query)
    q_words = q_norm.split()
    if not q_words:
        return []

    all_words = []
    for si, seg in enumerate(target):
        for w in seg.get("text", "").split():
            all_words.append((w, si))
    if not all_words:
        return []

    search_norm = [norm(w) for w, _ in all_words]
    found = []

    for i in range(len(search_norm) - len(q_words) + 1):
        window = " ".join(search_norm[i:i + len(q_words)])
        if q_norm in window:
            found.append({"pos": i, "len": len(q_words), "conf": "high", "score": 1.0, "seg": all_words[i][1]})

    if not found and fuzzy_thresh < 1.0:
        offset = 0
        for si, seg in enumerate(target):
            txt = seg.get("text", "")
            if not txt:
                continue
            sc = SequenceMatcher(None, q_norm, norm(txt)).ratio()
            if sc >= fuzzy_thresh:
                wc = len(txt.split())
                found.append({"pos": offset, "len": wc,
                              "conf": "medium" if sc > 0.85 else "low", "score": sc, "seg": si})
            offset += len(txt.split())

    seen, results = set(), []
    for fp in found:
        if fp["seg"] in seen:
            continue
        seen.add(fp["seg"])
        seg = target[fp["seg"]]
        p, ln = fp["pos"], fp["len"]
        cs = max(0, p - context_words)
        ce = min(len(all_words), p + ln + context_words)
        me = min(p + ln, len(all_words))

        before = " ".join(all_words[j][0] for j in range(cs, p))
        match = " ".join(all_words[j][0] for j in range(p, me))
        after = " ".join(all_words[j][0] for j in range(me, ce))

        results.append({
            "start_time": float(seg.get("start", 0)),
            "time_label": fmt_time(float(seg.get("start", 0))),
            "before": before, "match_hl": highlight_html(match, query),
            "after": after, "confidence": fp["conf"],
            "score": fp["score"], "idx": fp["seg"],
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def reset_search():
    st.session_state.search_results = None
    st.session_state.last_search_query = ""


def reset_all():
    for k, v in DEFAULTS.items():
        if k != "authenticated":
            st.session_state[k] = v


def build_timestamped_transcript(segments):
    """Construye transcripción con timestamps para el contexto del chat."""
    lines = []
    for seg in segments:
        t = fmt_time(float(seg.get("start", 0)))
        txt = seg.get("text", "").strip()
        if txt:
            lines.append(f"[{t}] {txt}")
    return "\n".join(lines)


def process_audio(client, uploaded, model, do_correct):
    size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    if size_mb > 25:
        st.error(f"Archivo muy grande ({size_mb:.1f} MB). Máximo 25 MB.")
        return False

    reset_all()

    with st.status("Procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path:
            st.error("Error al guardar archivo")
            return False

        st.session_state.audio_path = path
        st.write(f"📁 {uploaded.name} — {size_mb:.1f} MB")
        st.write("🎧 Transcribiendo...")

        raw, segs = transcribe(client, path, model)
        if not raw or not segs:
            st.error("Error en la transcripción")
            return False

        st.session_state.raw_transcript = raw
        st.session_state.transcript_segments = segs

        if do_correct:
            st.write("✨ Corrigiendo ortografía...")
            txt, csegs = correct_and_align(client, raw, segs)
            st.session_state.transcript_text = txt
            st.session_state.corrected_segments = csegs
            st.session_state.correction_applied = True
        else:
            st.session_state.transcript_text = raw
            st.session_state.corrected_segments = segs
            st.session_state.correction_applied = False

        st.session_state.audio_start_time = 0
        wc = len(raw.split())
        sc = len(segs)
        status.update(label=f"✅ {wc:,} palabras · {sc} segmentos", state="complete", expanded=False)
    return True


# --- APP ---
def main_app():
    client = get_client()
    if not client:
        st.stop()

    with st.sidebar:
        st.markdown("#### ⚙️ Configuración")
        model = st.selectbox("Modelo Whisper", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: "V3 Precisión" if "turbo" not in x else "V3 Turbo")
        do_correct = st.toggle("Corrección ortográfica", value=True)
        st.markdown("---")
        st.markdown("##### 🔍 Búsqueda")
        ctx_w = st.slider("Palabras contexto", 8, 40, 20, step=4)
        use_fuzzy = st.toggle("Aproximada (fuzzy)", value=True)
        fuzzy_t = st.slider("Sensibilidad", 0.5, 1.0, 0.75, 0.05) if use_fuzzy else 1.0
        st.markdown("---")
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # Header
    st.markdown("""
    <div class="app-bar">
        <div class="app-bar-left">
            <div class="app-logo">🎙️</div>
            <span class="app-name">Transcriptor Pro</span>
            <span class="app-tag">BETA</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # === SIN TRANSCRIPCIÓN ===
    if not st.session_state.transcript_text:
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-state-icon">📂</div>
                <div class="empty-state-title">Sube un archivo de audio</div>
                <div class="empty-state-text">MP3, WAV, M4A, OGG o MP4 — Máximo 25 MB</div>
            </div>
            """, unsafe_allow_html=True)

            uploaded = st.file_uploader(
                "x", type=["mp3", "wav", "m4a", "ogg", "mp4"],
                label_visibility="collapsed", key="upload_initial"
            )
            if uploaded:
                if st.button("🚀 Transcribir", type="primary", use_container_width=True):
                    if process_audio(client, uploaded, model, do_correct):
                        st.rerun()
        return

    # === CON TRANSCRIPCIÓN ===
    if st.session_state.audio_path:
        st.audio(st.session_state.audio_path, start_time=int(max(0, st.session_state.audio_start_time)))

    txt = st.session_state.transcript_text
    n_words = len(txt.split())
    n_segs = len(st.session_state.corrected_segments or [])
    corr_chip = "stat-chip stat-chip-ok" if st.session_state.correction_applied else "stat-chip"
    corr_text = "✓ Corregido" if st.session_state.correction_applied else "Original"
    st.markdown(f"""
    <div class="stats-bar">
        <span class="stat-chip"><strong>{n_words:,}</strong> palabras</span>
        <span class="stat-chip"><strong>{n_segs}</strong> segmentos</span>
        <span class="{corr_chip}">{corr_text}</span>
    </div>
    """, unsafe_allow_html=True)

    tab_search, tab_chat, tab_export = st.tabs(["🔍 Búsqueda", "💬 Chat IA", "📥 Exportar"])

    # ===== BÚSQUEDA =====
    with tab_search:
        c1, c2 = st.columns([6, 1])
        with c1:
            query = st.text_input(
                "q", placeholder="Buscar palabra o frase...",
                label_visibility="collapsed", key="q_input"
            )
        with c2:
            do_search = st.button("Buscar", type="primary", use_container_width=True)

        if do_search and query:
            st.session_state.last_search_query = query
            st.session_state.search_results = search_segments(
                query, st.session_state.transcript_segments,
                st.session_state.corrected_segments,
                context_words=ctx_w, fuzzy_thresh=fuzzy_t if use_fuzzy else 1.0
            )
        elif do_search and not query:
            reset_search()

        aq = st.session_state.last_search_query
        res = st.session_state.search_results

        if aq and res:
            st.caption(f"**{len(res)}** resultado{'s' if len(res) != 1 else ''} para \"{aq}\"")
            for i, r in enumerate(res):
                badge_cls = f"sr-badge-{r['confidence']}"
                bh = f"<span class='sr-ctx'>...{r['before']} </span>" if r['before'] else ""
                ah = f"<span class='sr-ctx'> {r['after']}...</span>" if r['after'] else ""
                rc1, rc2 = st.columns([0.6, 5])
                with rc1:
                    if st.button(f"▶ {r['time_label']}", key=f"p_{i}_{r['idx']}"):
                        st.session_state.audio_start_time = max(0, r["start_time"] - 2)
                        st.rerun()
                with rc2:
                    st.markdown(f"""
                    <div class="sr-card">
                        <div class="sr-head">
                            <span class="sr-time">{r['time_label']}</span>
                            <span class="sr-badge {badge_cls}">{r['confidence']}</span>
                        </div>
                        <div class="sr-body">{bh}{r['match_hl']}{ah}</div>
                    </div>
                    """, unsafe_allow_html=True)
        elif aq and res is not None and len(res) == 0:
            st.markdown("""
            <div class="no-results-box">
                🔍 Sin resultados. Prueba con otras palabras o activa búsqueda aproximada.
            </div>
            """, unsafe_allow_html=True)

        # Texto completo - SIN expander para evitar el texto "arrow" fantasma
        st.markdown("---")
        show_full = st.checkbox("📄 Mostrar texto completo", value=not bool(aq), key="show_full_text")
        if show_full:
            hl_text = highlight_html(txt, aq) if aq else txt
            st.markdown(f"<div class='full-text-box'>{hl_text}</div>", unsafe_allow_html=True)

        # Nuevo archivo - SIN expander
        st.markdown("---")
        show_new = st.checkbox("📂 Transcribir otro archivo", value=False, key="show_new_upload")
        if show_new:
            new_file = st.file_uploader(
                "x2", type=["mp3", "wav", "m4a", "ogg", "mp4"],
                label_visibility="collapsed", key="upload_new"
            )
            if new_file:
                if st.button("🔄 Procesar nuevo audio", type="primary", use_container_width=True):
                    if process_audio(client, new_file, model, do_correct):
                        st.rerun()

    # ===== CHAT =====
    with tab_chat:
        if not st.session_state.chat_history:
            st.markdown("""
            <div class="empty-state" style="padding:24px">
                <div class="empty-state-icon">💬</div>
                <div class="empty-state-title">Pregunta lo que quieras</div>
                <div class="empty-state-text">El asistente responde basándose exclusivamente en la transcripción con timestamps</div>
            </div>
            """, unsafe_allow_html=True)

        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Pregunta sobre el audio..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                ph = st.empty()
                full = ""
                try:
                    # Construir contexto con timestamps
                    segs_for_ctx = st.session_state.corrected_segments or st.session_state.transcript_segments or []
                    timestamped_ctx = build_timestamped_transcript(segs_for_ctx)
                    # Limitar a ~15000 chars
                    if len(timestamped_ctx) > 15000:
                        timestamped_ctx = timestamped_ctx[:15000] + "\n[...transcripción truncada...]"

                    system_prompt = (
                        "Eres un asistente que responde EXCLUSIVAMENTE con base en la transcripción de audio proporcionada. "
                        "REGLAS ESTRICTAS:\n"
                        "1. Solo responde con información que esté en la transcripción.\n"
                        "2. Siempre incluye el timestamp [MM:SS] o [H:MM:SS] donde se menciona la información.\n"
                        "3. Si la información NO está en la transcripción, responde: 'No encontré esa información en la transcripción.'\n"
                        "4. NO inventes ni supongas información que no esté explícitamente en el texto.\n"
                        "5. Responde en español, sé conciso y preciso.\n"
                        "6. Cuando cites, usa el formato: \"...texto citado...\" [timestamp]\n\n"
                        f"TRANSCRIPCIÓN CON TIMESTAMPS:\n{timestamped_ctx}"
                    )

                    stream = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            *[{"role": m["role"], "content": m["content"]}
                              for m in st.session_state.chat_history[-6:]],
                        ],
                        stream=True, max_tokens=2048, temperature=0.1,
                    )
                    for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                            full += chunk.choices[0].delta.content
                            ph.markdown(full + "▌")
                    ph.markdown(full)
                    st.session_state.chat_history.append({"role": "assistant", "content": full})
                except Exception as e:
                    st.error(f"Error: {e}")

    # ===== EXPORTAR =====
    with tab_export:
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(
                "📄 Texto (.txt)", data=txt, file_name="transcripcion.txt",
                mime="text/plain", use_container_width=True
            )
        with c2:
            srt = []
            for i, seg in enumerate(st.session_state.corrected_segments or []):
                s, e = float(seg.get("start", 0)), float(seg.get("end", 0))
                srt.append(f"{i+1}")
                srt.append(f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{s%60:06.3f} --> "
                           f"{int(e//3600):02d}:{int((e%3600)//60):02d}:{e%60:06.3f}")
                srt.append(seg.get("text", ""))
                srt.append("")
            st.download_button(
                "🎬 Subtítulos (.srt)", data="\n".join(srt) or "Sin datos",
                file_name="transcripcion.srt", mime="text/plain", use_container_width=True
            )
        show_ts = st.checkbox("Ver con timestamps", value=False, key="show_timestamps")
        if show_ts:
            for seg in (st.session_state.corrected_segments or []):
                st.markdown(f"`{fmt_time(float(seg.get('start',0)))}` {seg.get('text','')}")


if __name__ == "__main__":
    if check_password():
        main_app()
