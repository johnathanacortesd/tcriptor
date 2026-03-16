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

    /* Header compacto */
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

    /* Cards */
    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: var(--shadow-sm);
    }

    /* Resultado de búsqueda */
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

    /* Highlight */
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

    /* Texto completo con highlights */
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

    /* No results */
    .no-results {
        text-align: center;
        padding: 24px;
        color: var(--text-secondary);
    }

    /* Stats inline */
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

    /* Login */
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

    /* Ajustes Streamlit */
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
    div[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
    }

    /* Botones */
    .stButton > button[kind="primary"] {
        background: var(--primary);
        border: none;
        border-radius: var(--radius);
        font-weight: 500;
    }

    /* Ocultar menú hamburguesa y footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Scrollbar */
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
    """Formato de timestamp compacto."""
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def norm(text):
    """Normaliza texto: quita acentos, minúsculas."""
    if not text:
        return ""
    t = unicodedata.normalize('NFD', text)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return t.lower().strip()


def highlight_html(text, query):
    """Resalta query en text con <span class='hl'>."""
    if not query or not text:
        return text

    # Intentar frase completa
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(text):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", text)

    # Palabras individuales (>2 chars)
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
    """Guarda archivo subido en tmp."""
    try:
        safe = "".join(c for c in f.name if c.isalnum() or c in "._-") or "audio.mp3"
        path = os.path.join(tempfile.gettempdir(), f"up_{safe}")
        with open(path, "wb") as fp:
            fp.write(f.getbuffer())
        return path
    except Exception:
        return None


def transcribe(client, path, model):
    """Transcribe con Groq Whisper."""
    try:
        with open(path, "rb") as f:
            t = client.audio.transcriptions.create(
                file=(os.path.basename(path), f.read()),
                model=model,
                response_format="verbose_json",
                language="es",
                temperature=0.0
            )
        return t.text, t.segments
    except Exception as e:
        st.error(f"Error de transcripción: {e}")
        return None, None


# --- CORRECCIÓN ---
def _correct_chunk(client, text):
    """Corrige un chunk de texto."""
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
        # Limpiar prefijos del modelo
        for prefix in ["Aquí", "Texto corregido", "Corrección"]:
            if out.startswith(prefix) and ":" in out[:30]:
                out = out.split(":", 1)[1].strip()
                break
        return out
    except Exception:
        return text


def realign_segments(corrected_text, original_segments):
    """Redistribuye texto corregido en segmentos originales proporcionalmente."""
    words = corrected_text.split()
    total_orig = sum(len(s['text'].split()) for s in original_segments)
    if total_orig == 0:
        return original_segments

    aligned = []
    idx = 0
    for i, seg in enumerate(original_segments):
        seg_word_count = len(seg['text'].split())

        if i == len(original_segments) - 1:
            # Último segmento: tomar todo lo restante
            chunk = words[idx:]
        else:
            # Proporcional
            ratio = seg_word_count / total_orig
            take = max(1, round(ratio * len(words)))
            chunk = words[idx:idx + take]
            idx += len(chunk)

        aligned.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': " ".join(chunk) if chunk else seg['text']
        })

    return aligned


def correct_and_align(client, raw_text, segments):
    """Corrige ortografía y realinea con segmentos."""
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


# --- BÚSQUEDA PRECISA ---
def search_segments(query, segments, corrected_segments, context_words=25, fuzzy_thresh=0.75):
    """
    Búsqueda en segmentos con contexto por PALABRAS (no segmentos).
    Devuelve resultados con ventana de contexto precisa.
    """
    if not query:
        return []

    target = corrected_segments or segments
    results = []
    q_norm = norm(query)
    q_words = q_norm.split()

    # Construir texto plano con mapeo a segmentos
    all_words = []  # [(word, seg_index, word_pos_in_seg)]
    for si, seg in enumerate(target):
        for wi, w in enumerate(seg['text'].split()):
            all_words.append((w, si, wi))

    all_text_norm = " ".join(w for w, _, _ in all_words)

    # Buscar ocurrencias en texto plano
    found_positions = []

    # Búsqueda exacta de frase
    search_text_words = [norm(w) for w, _, _ in all_words]
    for i in range(len(search_text_words) - len(q_words) + 1):
        window = " ".join(search_text_words[i:i + len(q_words)])
        if q_norm in window:
            found_positions.append((i, len(q_words), "high", 1.0))

    # Si no hay exactos, buscar fuzzy por segmento
    if not found_positions and fuzzy_thresh < 1.0:
        for si, seg in enumerate(target):
            score = SequenceMatcher(None, q_norm, norm(seg['text'])).ratio()
            if score >= fuzzy_thresh:
                # Encontrar posición en all_words
                pos = sum(len(target[j]['text'].split()) for j in range(si))
                wc = len(seg['text'].split())
                conf = "medium" if score > 0.85 else "low"
                found_positions.append((pos, wc, conf, score))

    # Deduplicar por segmento
    seen_segs = set()
    for pos, wc, conf, score in found_positions:
        if pos >= len(all_words):
            continue
        seg_idx = all_words[pos][1]
        if seg_idx in seen_segs:
            continue
        seen_segs.add(seg_idx)

        seg = target[seg_idx]

        # Contexto: ±context_words PALABRAS alrededor del match
        ctx_start = max(0, pos - context_words)
        ctx_end = min(len(all_words), pos + wc + context_words)

        before_words = [all_words[j][0] for j in range(ctx_start, pos)]
        match_words = [all_words[j][0] for j in range(pos, min(pos + wc, len(all_words)))]
        after_words = [all_words[j][0] for j in range(min(pos + wc, len(all_words)), ctx_end)]

        before_text = " ".join(before_words)
        match_text = " ".join(match_words)
        after_text = " ".join(after_words)

        # Highlight en el match
        match_hl = highlight_html(match_text, query)

        results.append({
            "start": seg['start'],
            "time": fmt_time(seg['start']),
            "before": before_text,
            "match_hl": match_hl,
            "after": after_text,
            "confidence": conf,
            "score": score,
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def build_full_text_html(text, query):
    """Construye HTML del texto completo con highlights de la búsqueda."""
    if not query:
        # Sin búsqueda, texto plano
        paragraphs = text.split('\n')
        html = "<br>".join(p for p in paragraphs if p.strip())
        return f"<div class='full-text-container'>{html}</div>"

    highlighted = highlight_html(text, query)
    return f"<div class='full-text-container'>{highlighted}</div>"


# --- APP PRINCIPAL ---
def main_app():
    client = get_client()
    if not client:
        st.stop()

    # Sidebar compacto
    with st.sidebar:
        st.markdown("### ⚙️ Ajustes")
        model = st.selectbox("Modelo", ["whisper-large-v3", "whisper-large-v3-turbo"],
                             format_func=lambda x: x.replace("whisper-large-", "").upper())
        correct = st.toggle("Corrección ortográfica", value=True)
        st.divider()
        st.markdown("##### Búsqueda")
        ctx_words = st.slider("Palabras de contexto", 10, 50, 25, step=5)
        use_fuzzy = st.toggle("Búsqueda aproximada", value=True)
        fuzzy_t = st.slider("Sensibilidad", 0.5, 1.0, 0.75, step=0.05) if use_fuzzy else 1.0
        st.divider()
        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # Header
    st.markdown("""
    <div class="app-header">
        <h1>🎙️ Transcriptor Pro</h1>
        <span class="subtitle">Transcripción • Búsqueda • Chat IA</span>
    </div>
    """, unsafe_allow_html=True)

    # Upload + Transcribe
    col_up, col_btn = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Audio", type=["mp3", "wav", "m4a", "ogg", "mp4"],
                                     label_visibility="collapsed")
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        do_transcribe = st.button("🚀 Transcribir", type="primary",
                                   use_container_width=True, disabled=not uploaded)

    if uploaded and do_transcribe:
        # Validar tamaño
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
                if not raw:
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
                    st.session_state.corrected_segments = [
                        {'start': s['start'], 'end': s['end'], 'text': s['text']} for s in segs
                    ]
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

    # Contenido principal
    if st.session_state.transcript_text:
        # Stats compactas
        txt = st.session_state.transcript_text
        words = len(txt.split())
        segs = len(st.session_state.corrected_segments or [])
        corr_label = "✅ Corregido" if st.session_state.correction_applied else "📝 Original"
        st.markdown(f"""
        <div class="stats-row">
            <span class="stat-item"><strong>{words:,}</strong> palabras</span>
            <span class="stat-item"><strong>{segs}</strong> segmentos</span>
            <span class="stat-item">{corr_label}</span>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["🔍 Búsqueda", "💬 Chat IA", "📥 Exportar"])

        # --- TAB BÚSQUEDA ---
        with tab1:
            c1, c2 = st.columns([5, 1])
            with c1:
                query = st.text_input("Buscar en transcripción", placeholder="Escribe una palabra o frase...",
                                       label_visibility="collapsed", key="search_input")
            with c2:
                search_btn = st.button("Buscar", type="primary", use_container_width=True)

            # Ejecutar búsqueda
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

            # Mostrar resultados
            active_query = st.session_state.last_search_query
            results = st.session_state.search_results

            if active_query and results:
                st.caption(f"{len(results)} resultado{'s' if len(results) != 1 else ''} para **\"{active_query}\"**")

                for i, r in enumerate(results):
                    # Botón de timestamp para saltar
                    col_time, col_text = st.columns([0.8, 5])
                    with col_time:
                        if st.button(f"▶ {r['time']}", key=f"play_{i}_{r['start']}",
                                     help="Reproducir desde aquí"):
                            st.session_state.audio_start_time = max(0, r['start'] - 2)
                            st.rerun()

                    with col_text:
                        badge_class = f"badge-{r['confidence']}"
                        st.markdown(f"""
                        <div class="search-result">
                            <div class="result-header">
                                <span class="timestamp-chip">{r['time']}</span>
                                <span class="badge {badge_class}">{r['confidence']}</span>
                            </div>
                            <div class="result-text">
                                <span class="ctx">...{r['before']} </span>{r['match_hl']}<span class="ctx"> {r['after']}...</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

            elif active_query and results is not None:
                st.markdown("""
                <div class="no-results">
                    <p>🔍 No se encontraron resultados</p>
                    <p style="font-size:0.8rem">Intenta con otras palabras o activa la búsqueda aproximada</p>
                </div>
                """, unsafe_allow_html=True)

            # Texto completo con highlights
            st.markdown("---")
            st.markdown("##### 📄 Texto completo")
            full_html = build_full_text_html(st.session_state.transcript_text, active_query)
            st.markdown(full_html, unsafe_allow_html=True)

        # --- TAB CHAT ---
        with tab2:
            # Historial
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
                        # Limitar contexto a 15000 chars para no exceder límites
                        ctx = st.session_state.transcript_text[:15000]
                        stream = client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[
                                {"role": "system",
                                 "content": f"Eres un asistente que responde preguntas basándose en esta transcripción de audio. "
                                            f"Responde en español, sé conciso y preciso. Si no encuentras la información, dilo.\n\n"
                                            f"TRANSCRIPCIÓN:\n{ctx}"},
                                *[{"role": m["role"], "content": m["content"]}
                                  for m in st.session_state.chat_history[-6:]],  # Últimos 6 mensajes
                            ],
                            stream=True,
                            max_tokens=2048,
                        )
                        for chunk in stream:
                            delta = chunk.choices[0].delta.content
                            if delta:
                                full += delta
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
                # SRT
                srt_content = ""
                segs_export = st.session_state.corrected_segments or st.session_state.transcript_segments
                if segs_export:
                    for i, seg in enumerate(segs_export):
                        s = seg['start']
                        e = seg['end']
                        sh, sm, ss = int(s//3600), int((s%3600)//60), s%60
                        eh, em, es = int(e//3600), int((e%3600)//60), e%60
                        srt_content += f"{i+1}\n"
                        srt_content += f"{sh:02d}:{sm:02d}:{ss:06.3f} --> {eh:02d}:{em:02d}:{es:06.3f}\n"
                        srt_content += f"{seg['text']}\n\n"

                st.download_button(
                    "🎬 Subtítulos (.srt)",
                    data=srt_content or "Sin segmentos disponibles",
                    file_name="transcripcion.srt",
                    mime="text/plain",
                    use_container_width=True
                )

            # Vista previa
            if st.toggle("Ver transcripción con timestamps"):
                segs_show = st.session_state.corrected_segments or []
                for seg in segs_show:
                    st.markdown(f"`{fmt_time(seg['start'])}` {seg['text']}")


# --- ENTRY POINT ---
if __name__ == "__main__":
    if check_password():
        main_app()
