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

# --- CSS COMPACTO ESTILO GOOGLE MATERIAL ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --primary: #1a73e8;
        --primary-light: #e8f0fe;
        --surface: #ffffff;
        --bg: #f8f9fa;
        --text: #202124;
        --text-secondary: #5f6368;
        --border: #dadce0;
        --green: #34a853;
        --yellow: #fbbc04;
        --red: #ea4335;
        --radius: 8px;
        --shadow-sm: 0 1px 2px rgba(60,64,67,0.1), 0 1px 3px rgba(60,64,67,0.08);
        --shadow-md: 0 1px 3px rgba(60,64,67,0.15), 0 4px 8px rgba(60,64,67,0.1);
    }

    * { font-family: 'Inter', -apple-system, sans-serif !important; }

    .main .block-container {
        padding: 1rem 2rem 2rem 2rem;
        max-width: 1100px;
    }

    .app-header {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0 8px 0;
        border-bottom: 1px solid var(--border);
        margin-bottom: 16px;
    }
    .app-header h1 {
        font-size: 1.4rem;
        font-weight: 600;
        color: var(--text);
        margin: 0;
        letter-spacing: -0.5px;
    }
    .app-header .subtitle {
        font-size: 0.8rem;
        color: var(--text-secondary);
        margin-left: auto;
    }

    .search-result {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 12px 16px;
        margin-bottom: 8px;
        box-shadow: var(--shadow-sm);
        transition: box-shadow 0.2s;
    }
    .search-result:hover {
        box-shadow: var(--shadow-md);
    }

    .result-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }

    .timestamp-chip {
        background: var(--primary-light);
        color: var(--primary);
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        white-space: nowrap;
    }

    .badge {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.65rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-high { background: #e6f4ea; color: var(--green); }
    .badge-medium { background: #fef7e0; color: #e37400; }
    .badge-low { background: #fce8e6; color: var(--red); }

    .hl {
        background: #fbbc04;
        color: #202124;
        padding: 1px 3px;
        border-radius: 3px;
        font-weight: 600;
        box-decoration-break: clone;
        -webkit-box-decoration-break: clone;
    }

    .result-text {
        font-size: 0.9rem;
        line-height: 1.65;
        color: var(--text);
    }
    .ctx {
        color: var(--text-secondary);
        font-weight: 300;
    }

    .full-text-container {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 20px;
        font-size: 0.9rem;
        line-height: 1.8;
        color: var(--text);
        max-height: 500px;
        overflow-y: auto;
    }

    .no-results {
        text-align: center;
        padding: 24px;
        color: var(--text-secondary);
    }

    .stats-row {
        display: flex;
        gap: 16px;
        margin: 8px 0;
    }
    .stat-item {
        font-size: 0.8rem;
        color: var(--text-secondary);
    }
    .stat-item strong {
        color: var(--text);
    }

    .login-box {
        max-width: 360px;
        margin: 80px auto;
        text-align: center;
    }
    .login-box h2 {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .login-box p {
        color: var(--text-secondary);
        font-size: 0.85rem;
        margin-bottom: 20px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 0.85rem;
        font-weight: 500;
        padding: 8px 16px;
        color: var(--text-secondary);
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary) !important;
        border-bottom-color: var(--primary) !important;
    }

    div[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border);
    }

    .stButton > button[kind="primary"] {
        background: var(--primary);
        border: none;
        border-radius: var(--radius);
        font-weight: 500;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .full-text-container::-webkit-scrollbar { width: 6px; }
    .full-text-container::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 3px;
    }
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

    st.markdown("""
    <div class="login-box">
        <h2>🎙️ Transcriptor Pro</h2>
        <p>Ingresa la contraseña para continuar</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        pwd = st.text_input("Contraseña", type="password", label_visibility="collapsed",
                            placeholder="Contraseña...")
        if st.button("Ingresar", use_container_width=True, type="primary"):
            try:
                if pwd == st.secrets["general"]["app_password"]:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta")
            except Exception:
                st.error("Error de configuración (secrets.toml)")
    return False


def get_client():
    try:
        return Groq(api_key=st.secrets["general"]["groq_api_key"])
    except Exception:
        st.error("❌ API key no configurada")
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
                model=model,
                response_format="verbose_json",
                language="es",
                temperature=0.0
            )
        segments_list = []
        if t.segments:
            for seg in t.segments:
                segments_list.append({
                    "start": float(seg.get("start", seg.get("start", 0)) if isinstance(seg, dict) else getattr(seg, "start", 0)),
                    "end": float(seg.get("end", seg.get("end", 0)) if isinstance(seg, dict) else getattr(seg, "end", 0)),
                    "text": str(seg.get("text", "") if isinstance(seg, dict) else getattr(seg, "text", "")).strip()
                })
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
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
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

    aligned = []
    idx = 0
    for i, seg in enumerate(original_segments):
        seg_wc = len(seg["text"].split())
        if i == len(original_segments) - 1:
            chunk = words[idx:]
        else:
            ratio = seg_wc / total_orig
            take = max(1, round(ratio * len(words)))
            chunk = words[idx:idx + take]
            idx += len(chunk)

        aligned.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": " ".join(chunk) if chunk else seg["text"]
        })
    return aligned


def correct_and_align(client, raw_text, segments):
    MAX_CHUNK = 5000
    if len(raw_text) <= MAX_CHUNK:
        corrected = _correct_chunk(client, raw_text)
    else:
        sentences = raw_text.split(". ")
        chunks, current = [], ""
        for s in sentences:
            if len(current) + len(s) < MAX_CHUNK:
                current += s + ". "
            else:
                chunks.append(current.strip())
                current = s + ". "
        if current.strip():
            chunks.append(current.strip())

        parts = []
        bar = st.progress(0, text="Corrigiendo ortografía...")
        for i, c in enumerate(chunks):
            parts.append(_correct_chunk(client, c))
            bar.progress((i + 1) / len(chunks), text=f"Corrigiendo... {i+1}/{len(chunks)}")
        bar.empty()
        corrected = " ".join(parts)

    corrected_segs = realign_segments(corrected, segments)
    return corrected, corrected_segs


# --- BÚSQUEDA ---
def search_segments(query, segments, corrected_segments, context_words=25, fuzzy_thresh=0.75):
    if not query:
        return []

    target = corrected_segments if corrected_segments else segments
    if not target:
        return []

    results = []
    q_norm = norm(query)
    q_words = q_norm.split()

    if not q_words:
        return []

    # Construir lista plana de palabras con referencia a segmento
    all_words = []
    for si, seg in enumerate(target):
        seg_text = seg.get("text", "")
        if seg_text:
            for wi, w in enumerate(seg_text.split()):
                all_words.append((w, si))

    if not all_words:
        return []

    search_words_norm = [norm(w) for w, _ in all_words]
    found_positions = []

    # Búsqueda exacta de frase
    for i in range(len(search_words_norm) - len(q_words) + 1):
        window = " ".join(search_words_norm[i:i + len(q_words)])
        if q_norm in window:
            found_positions.append({
                "pos": i,
                "length": len(q_words),
                "confidence": "high",
                "score": 1.0,
                "seg_idx": all_words[i][1]
            })

    # Fuzzy por segmento si no hay exactos
    if not found_positions and fuzzy_thresh < 1.0:
        word_offset = 0
        for si, seg in enumerate(target):
            seg_text = seg.get("text", "")
            if not seg_text:
                continue
            score = SequenceMatcher(None, q_norm, norm(seg_text)).ratio()
            if score >= fuzzy_thresh:
                wc = len(seg_text.split())
                conf = "medium" if score > 0.85 else "low"
                found_positions.append({
                    "pos": word_offset,
                    "length": wc,
                    "confidence": conf,
                    "score": score,
                    "seg_idx": si
                })
            word_offset += len(seg_text.split())

    # Deduplicar por segmento
    seen = set()
    for fp in found_positions:
        seg_idx = fp["seg_idx"]
        if seg_idx in seen:
            continue
        seen.add(seg_idx)

        pos = fp["pos"]
        length = fp["length"]
        seg = target[seg_idx]

        ctx_start = max(0, pos - context_words)
        ctx_end = min(len(all_words), pos + length + context_words)

        before_words = [all_words[j][0] for j in range(ctx_start, pos)]
        match_end = min(pos + length, len(all_words))
        match_words = [all_words[j][0] for j in range(pos, match_end)]
        after_words = [all_words[j][0] for j in range(match_end, ctx_end)]

        before_text = " ".join(before_words)
        match_text = " ".join(match_words)
        after_text = " ".join(after_words)

        match_hl = highlight_html(match_text, query)

        start_time = float(seg.get("start", 0))

        results.append({
            "start_time": start_time,
            "time_label": fmt_time(start_time),
            "before": before_text,
            "match_hl": match_hl,
            "after": after_text,
            "confidence": fp["confidence"],
            "score": fp["score"],
            "idx": seg_idx,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def build_full_text_html(text, query):
    if not query:
        return f"<div class='full-text-container'>{text}</div>"
    highlighted = highlight_html(text, query)
    return f"<div class='full-text-container'>{highlighted}</div>"


# --- APP PRINCIPAL ---
def main_app():
    client = get_client()
    if not client:
        st.stop()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Ajustes")
        model = st.selectbox("Modelo", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: x.replace("whisper-large-", "Whisper ").upper())
        correct = st.toggle("Corrección ortográfica", value=True)
        st.divider()
        st.markdown("##### Búsqueda")
        ctx_words = st.slider("Palabras de contexto", 10, 50, 25, step=5)
        use_fuzzy = st.toggle("Búsqueda aproximada", value=True)
        fuzzy_t = st.slider("Sensibilidad", 0.5, 1.0, 0.75, step=0.05) if use_fuzzy else 1.0
        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Header
    st.markdown("""
    <div class="app-header">
        <h1>🎙️ Transcriptor Pro</h1>
        <span class="subtitle">Transcripción · Búsqueda · Chat IA</span>
    </div>
    """, unsafe_allow_html=True)

    # Upload
    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Audio", type=["mp3", "wav", "m4a", "ogg", "mp4"],
                                     label_visibility="collapsed")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        do_transcribe = st.button("🚀 Transcribir", type="primary",
                                   use_container_width=True, disabled=not uploaded)

    if uploaded and do_transcribe:
        size_mb = len(uploaded.getvalue()) / (1024 * 1024)
        if size_mb > 25:
            st.error(f"Archivo demasiado grande ({size_mb:.1f} MB). Máximo: 25 MB.")
        else:
            st.session_state.search_results = None
            st.session_state.last_search_query = ""

            with st.status("Procesando audio...", expanded=True) as status:
                path = save_uploaded(uploaded)
                if not path:
                    st.error("Error guardando archivo")
                    st.stop()

                st.session_state.audio_path = path
                st.write(f"📁 {uploaded.name} ({size_mb:.1f} MB)")

                st.write("🎧 Transcribiendo...")
                raw, segs = transcribe(client, path, model)
                if not raw or not segs:
                    st.error("No se pudo transcribir el audio.")
                    st.stop()

                st.session_state.raw_transcript = raw
                st.session_state.transcript_segments = segs

                if correct:
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
                word_count = len(raw.split())
                seg_count = len(segs)
                status.update(label=f"✅ Listo — {word_count} palabras, {seg_count} segmentos",
                              state="complete", expanded=False)

    # Reproductor
    if st.session_state.audio_path:
        start_t = int(max(0, st.session_state.audio_start_time))
        st.audio(st.session_state.audio_path, start_time=start_t)

    # Contenido
    if st.session_state.transcript_text:
        txt = st.session_state.transcript_text
        words_total = len(txt.split())
        segs_total = len(st.session_state.corrected_segments or [])
        corr_label = "✅ Corregido" if st.session_state.correction_applied else "📝 Original"
        st.markdown(f"""
        <div class="stats-row">
            <span class="stat-item"><strong>{words_total:,}</strong> palabras</span>
            <span class="stat-item"><strong>{segs_total}</strong> segmentos</span>
            <span class="stat-item">{corr_label}</span>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🔍 Búsqueda", "💬 Chat IA", "📥 Exportar"])

        # --- TAB BÚSQUEDA ---
        with tab1:
            c1, c2 = st.columns([5, 1])
            with c1:
                query = st.text_input("Buscar en transcripción",
                                       placeholder="Escribe una palabra o frase...",
                                       label_visibility="collapsed",
                                       key="search_input")
            with c2:
                search_btn = st.button("Buscar", type="primary", use_container_width=True)

            if search_btn and query:
                st.session_state.last_search_query = query
                st.session_state.search_results = search_segments(
                    query,
                    st.session_state.transcript_segments,
                    st.session_state.corrected_segments,
                    context_words=ctx_words,
                    fuzzy_thresh=fuzzy_t if use_fuzzy else 1.0
                )
            elif search_btn and not query:
                st.session_state.last_search_query = ""
                st.session_state.search_results = None

            active_query = st.session_state.last_search_query
            results = st.session_state.search_results

            if active_query and results:
                st.caption(f"{len(results)} resultado{'s' if len(results) != 1 else ''} para **\"{active_query}\"**")

                for i, r in enumerate(results):
                    col_time, col_text = st.columns([1, 5])
                    with col_time:
                        btn_key = f"play_{i}_{r['idx']}"
                        if st.button(f"▶ {r['time_label']}", key=btn_key,
                                     help="Reproducir desde aquí"):
                            st.session_state.audio_start_time = max(0, r["start_time"] - 2)
                            st.rerun()

                    with col_text:
                        badge_class = f"badge-{r['confidence']}"
                        before_html = f"<span class='ctx'>...{r['before']} </span>" if r['before'] else ""
                        after_html = f"<span class='ctx'> {r['after']}...</span>" if r['after'] else ""
                        st.markdown(f"""
                        <div class="search-result">
                            <div class="result-header">
                                <span class="timestamp-chip">{r['time_label']}</span>
                                <span class="badge {badge_class}">{r['confidence']}</span>
                            </div>
                            <div class="result-text">
                                {before_html}{r['match_hl']}{after_html}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            elif active_query and results is not None and len(results) == 0:
                st.markdown("""
                <div class="no-results">
                    <p>🔍 No se encontraron resultados</p>
                    <p style="font-size:0.8rem">Intenta con otras palabras o activa la búsqueda aproximada</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("##### 📄 Texto completo")
            full_html = build_full_text_html(st.session_state.transcript_text, active_query)
            st.markdown(full_html, unsafe_allow_html=True)

        # --- TAB CHAT ---
        with tab2:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            if prompt := st.chat_input("Pregunta sobre el audio..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full = ""
                    try:
                        ctx = st.session_state.transcript_text[:15000]
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system",
                                 "content": (
                                     "Eres un asistente que responde preguntas basándose en esta transcripción de audio. "
                                     "Responde en español, sé conciso y preciso. Si no encuentras la información, dilo.\n\n"
                                     f"TRANSCRIPCIÓN:\n{ctx}"
                                 )},
                                *[{"role": m["role"], "content": m["content"]}
                                  for m in st.session_state.chat_history[-6:]],
                            ],
                            stream=True,
                            max_tokens=2048,
                        )
                        for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                full += chunk.choices[0].delta.content
                                placeholder.markdown(full + "▌")
                        placeholder.markdown(full)
                        st.session_state.chat_history.append({"role": "assistant", "content": full})
                    except Exception as e:
                        st.error(f"Error: {e}")

        # --- TAB EXPORTAR ---
        with tab3:
            st.markdown("##### Descargar transcripción")
            c1, c2 = st.columns(2)

            with c1:
                st.download_button(
                    "📄 Texto plano (.txt)",
                    data=st.session_state.transcript_text,
                    file_name="transcripcion.txt",
                    mime="text/plain",
                    use_container_width=True
                )

            with c2:
                srt_lines = []
                segs_export = st.session_state.corrected_segments or st.session_state.transcript_segments or []
                for i, seg in enumerate(segs_export):
                    s = float(seg.get("start", 0))
                    e = float(seg.get("end", 0))
                    sh, sm, ss = int(s // 3600), int((s % 3600) // 60), s % 60
                    eh, em, es = int(e // 3600), int((e % 3600) // 60), e % 60
                    srt_lines.append(f"{i+1}")
                    srt_lines.append(f"{sh:02d}:{sm:02d}:{ss:06.3f} --> {eh:02d}:{em:02d}:{es:06.3f}")
                    srt_lines.append(seg.get("text", ""))
                    srt_lines.append("")

                srt_content = "\n".join(srt_lines) if srt_lines else "Sin segmentos"

                st.download_button(
                    "🎬 Subtítulos (.srt)",
                    data=srt_content,
                    file_name="transcripcion.srt",
                    mime="text/plain",
                    use_container_width=True
                )

            if st.toggle("Ver transcripción con timestamps"):
                segs_show = st.session_state.corrected_segments or []
                for seg in segs_show:
                    t_label = fmt_time(float(seg.get("start", 0)))
                    st.markdown(f"`{t_label}` {seg.get('text', '')}")


# --- ENTRY POINT ---
if __name__ == "__main__":
    if check_password():
        main_app()
