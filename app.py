import streamlit as st
import os
import tempfile
import unicodedata
from groq import Groq
from difflib import SequenceMatcher
import re
import json
import time
import math
from datetime import datetime

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
        --blue: #2563eb;
        --blue-bg: #eff6ff;
        --purple: #7c3aed;
        --purple-bg: #f5f3ff;
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

    .stFileUploader > label,
    .stFileUploader [data-testid="stFileUploaderDropzoneInstructions"] > div > span,
    .uploadedFileName { font-size: 0.78rem !important; }

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
    .stat-chip-warn { background: var(--amber-bg); color: var(--amber); border-color: #fcd34d; }

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
    .sr-segment-full {
        font-size: 0.78rem; line-height: 1.5; color: var(--text-secondary);
        margin-top: 6px; padding-top: 6px; border-top: 1px dashed var(--border);
    }

    .hl {
        background: linear-gradient(120deg, #fed7aa, #fdba74);
        color: var(--text); padding: 1px 4px; border-radius: 3px; font-weight: 600;
    }

    /* TEXTO COMPLETO */
    .full-text-box {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 16px 20px;
        font-size: 0.85rem; line-height: 1.85; color: var(--text);
        max-height: 480px; overflow-y: auto;
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

    /* ANALYSIS CARDS */
    .analysis-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 16px 20px;
        margin-bottom: 10px; box-shadow: var(--shadow-xs);
    }
    .analysis-card h4 {
        font-size: 0.9rem; font-weight: 600; color: var(--text);
        margin: 0 0 8px 0; display: flex; align-items: center; gap: 6px;
    }
    .analysis-content {
        font-size: 0.83rem; line-height: 1.7; color: var(--text);
    }

    .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin: 10px 0; }
    .kpi-card {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 14px 16px; text-align: center;
    }
    .kpi-value { font-size: 1.4rem; font-weight: 700; color: var(--primary); }
    .kpi-label { font-size: 0.7rem; color: var(--text-muted); margin-top: 2px; text-transform: uppercase; font-weight: 500; }

    /* COVERAGE BAR */
    .coverage-bar-container {
        background: var(--bg); border-radius: 6px; height: 24px;
        overflow: hidden; border: 1px solid var(--border); position: relative;
        margin: 8px 0;
    }
    .coverage-bar-fill {
        height: 100%; border-radius: 5px; transition: width 0.5s ease;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.7rem; font-weight: 700; color: white;
    }
    .coverage-ok { background: linear-gradient(90deg, #059669, #10b981); }
    .coverage-warn { background: linear-gradient(90deg, #d97706, #f59e0b); }
    .coverage-bad { background: linear-gradient(90deg, #dc2626, #ef4444); }
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
    "analysis_cache": {},
    "uploaded_filename": None,
    "audio_duration_ms": 0,
    "coverage_pct": 100.0,
    "transcript_gaps": [],
    "chunks_used": 1,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v


# --- UTILIDADES ---
def fmt_time(seconds):
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_duration(seconds):
    s = max(0, int(seconds))
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    parts.append(f"{sec}s")
    return " ".join(parts)


def norm(text):
    if not text:
        return ""
    t = unicodedata.normalize('NFD', text)
    t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
    return t.lower().strip()


def highlight_html(text, query):
    if not query or not text:
        return text
    result = text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(result):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    for w in query.split():
        if len(w) > 1:
            wp = re.compile(re.escape(w), re.IGNORECASE)
            result = wp.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    return result


def highlight_full_text(text, query):
    if not query or not text:
        return text
    result = text
    pat = re.compile(re.escape(query), re.IGNORECASE)
    if pat.search(result):
        return pat.sub(lambda m: f"<span class='hl'>{m.group()}</span>", result)
    words = [w for w in query.split() if len(w) > 1]
    for w in words:
        wp = re.compile(r'(?<![<\w])(' + re.escape(w) + r')(?![>\w])', re.IGNORECASE)
        result = wp.sub(r"<span class='hl'>\1</span>", result)
    return result


def count_occurrences(text, query):
    if not query or not text:
        return 0
    count = len(re.findall(re.escape(query), text, re.IGNORECASE))
    if count == 0:
        for w in query.split():
            if len(w) > 1:
                count += len(re.findall(re.escape(w), text, re.IGNORECASE))
    return count


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


# ============================================================
# AUDIO: SEGMENTACIÓN, TRANSCRIPCIÓN ROBUSTA Y VERIFICACIÓN
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


def get_audio_duration_ms(path):
    """Obtiene duración del audio en milisegundos usando pydub."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(path)
        return len(audio), audio
    except Exception:
        return None, None


def split_audio_chunks(audio_segment, chunk_duration_ms=600_000, overlap_ms=15_000):
    """
    Divide el audio en chunks con overlap para no perder contenido en los bordes.

    Args:
        audio_segment: pydub AudioSegment
        chunk_duration_ms: duración de cada chunk (default 10 min = 600,000 ms)
        overlap_ms: overlap entre chunks (default 15 seg = 15,000 ms)

    Returns:
        Lista de tuplas (chunk_audio, start_ms, end_ms, chunk_path)
    """
    total_ms = len(audio_segment)
    chunks = []

    if total_ms <= chunk_duration_ms:
        # Audio cabe en un solo chunk
        chunk_path = os.path.join(tempfile.gettempdir(), "chunk_0.mp3")
        audio_segment.export(chunk_path, format="mp3", bitrate="128k")
        chunks.append({
            "path": chunk_path,
            "start_ms": 0,
            "end_ms": total_ms,
            "index": 0
        })
        return chunks

    # Dividir con overlap
    start = 0
    idx = 0
    while start < total_ms:
        end = min(start + chunk_duration_ms, total_ms)
        chunk = audio_segment[start:end]

        # Exportar chunk como mp3 con bitrate controlado
        chunk_path = os.path.join(tempfile.gettempdir(), f"chunk_{idx}.mp3")
        chunk.export(chunk_path, format="mp3", bitrate="128k")

        # Verificar que no exceda 25 MB
        file_size = os.path.getsize(chunk_path) / (1024 * 1024)
        if file_size > 24:
            # Re-exportar con bitrate menor
            chunk.export(chunk_path, format="mp3", bitrate="64k")

        chunks.append({
            "path": chunk_path,
            "start_ms": start,
            "end_ms": end,
            "index": idx
        })

        if end >= total_ms:
            break

        # Siguiente chunk empieza antes del final del actual (overlap)
        start = end - overlap_ms
        idx += 1

    return chunks


def transcribe_single(client, path, model, max_retries=3):
    """Transcribe un archivo de audio con reintentos automáticos."""
    for attempt in range(max_retries):
        try:
            with open(path, "rb") as f:
                file_data = f.read()

            t = client.audio.transcriptions.create(
                file=(os.path.basename(path), file_data),
                model=model,
                response_format="verbose_json",
                language="es",
                temperature=0.0
            )

            segments = []
            if t.segments:
                for seg in t.segments:
                    if isinstance(seg, dict):
                        s = seg.get("start", 0)
                        e = seg.get("end", 0)
                        tx = seg.get("text", "")
                    else:
                        s = getattr(seg, "start", 0)
                        e = getattr(seg, "end", 0)
                        tx = getattr(seg, "text", "")
                    text = str(tx).strip()
                    if text:  # Solo agregar segmentos con texto
                        segments.append({
                            "start": float(s),
                            "end": float(e),
                            "text": text
                        })

            return t.text, segments, None

        except Exception as e:
            error_str = str(e)
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2  # Backoff: 2s, 4s, 6s
                time.sleep(wait)
            else:
                return None, None, error_str

    return None, None, "Max retries exceeded"


def merge_chunk_segments(all_chunk_results, overlap_ms=15_000):
    """
    Fusiona segmentos de múltiples chunks, eliminando duplicados del overlap.

    La estrategia:
    - Cada chunk tiene sus timestamps relativos a su inicio
    - Ajustamos timestamps al tiempo absoluto del audio completo
    - En zonas de overlap, eliminamos segmentos duplicados comparando texto
    """
    if not all_chunk_results:
        return [], ""

    if len(all_chunk_results) == 1:
        result = all_chunk_results[0]
        return result["segments"], result["text"]

    merged_segments = []
    overlap_sec = overlap_ms / 1000.0

    for ci, chunk_result in enumerate(all_chunk_results):
        chunk_start_sec = chunk_result["start_ms"] / 1000.0
        chunk_segments = chunk_result["segments"]

        if not chunk_segments:
            continue

        # Ajustar timestamps al tiempo absoluto
        adjusted = []
        for seg in chunk_segments:
            adjusted.append({
                "start": seg["start"] + chunk_start_sec,
                "end": seg["end"] + chunk_start_sec,
                "text": seg["text"]
            })

        if ci == 0:
            # Primer chunk: agregar todo
            merged_segments.extend(adjusted)
        else:
            # Chunks subsecuentes: filtrar overlap
            if not merged_segments:
                merged_segments.extend(adjusted)
                continue

            last_merged_end = merged_segments[-1]["end"]

            for seg in adjusted:
                # Si el segmento empieza antes del final del último segmento fusionado
                # es parte del overlap -> verificar si es duplicado
                if seg["start"] < last_merged_end - 1.0:
                    # Buscar si ya existe un segmento similar
                    is_duplicate = False
                    seg_norm = norm(seg["text"])
                    for existing in merged_segments[-10:]:  # Comparar con últimos 10
                        existing_norm = norm(existing["text"])
                        # Comparar similitud
                        if seg_norm and existing_norm:
                            ratio = SequenceMatcher(None, seg_norm, existing_norm).ratio()
                            if ratio > 0.7:
                                is_duplicate = True
                                break
                            # También verificar si es subcadena
                            if seg_norm in existing_norm or existing_norm in seg_norm:
                                is_duplicate = True
                                break
                    if is_duplicate:
                        continue

                # No es duplicado o está fuera del overlap -> agregar
                merged_segments.append(seg)
                last_merged_end = max(last_merged_end, seg["end"])

    # Ordenar por tiempo de inicio
    merged_segments.sort(key=lambda x: x["start"])

    # Construir texto completo
    full_text = " ".join(seg["text"] for seg in merged_segments)

    return merged_segments, full_text


def find_coverage_gaps(segments, total_duration_sec, gap_threshold=5.0):
    """
    Detecta huecos en la transcripción donde no hay segmentos.

    Args:
        segments: lista de segmentos con start/end
        total_duration_sec: duración total del audio en segundos
        gap_threshold: segundos mínimos para considerar un hueco (default 5s)

    Returns:
        Lista de huecos {"start": float, "end": float, "duration": float}
    """
    if not segments:
        return [{"start": 0, "end": total_duration_sec, "duration": total_duration_sec}]

    gaps = []
    sorted_segs = sorted(segments, key=lambda x: x["start"])

    # Hueco al inicio
    if sorted_segs[0]["start"] > gap_threshold:
        gaps.append({
            "start": 0,
            "end": sorted_segs[0]["start"],
            "duration": sorted_segs[0]["start"]
        })

    # Huecos entre segmentos
    for i in range(len(sorted_segs) - 1):
        gap_start = sorted_segs[i]["end"]
        gap_end = sorted_segs[i + 1]["start"]
        gap_duration = gap_end - gap_start
        if gap_duration > gap_threshold:
            gaps.append({
                "start": gap_start,
                "end": gap_end,
                "duration": gap_duration
            })

    # Hueco al final
    if sorted_segs and total_duration_sec - sorted_segs[-1]["end"] > gap_threshold:
        gaps.append({
            "start": sorted_segs[-1]["end"],
            "end": total_duration_sec,
            "duration": total_duration_sec - sorted_segs[-1]["end"]
        })

    return gaps


def calculate_coverage(segments, total_duration_sec):
    """Calcula el porcentaje de cobertura temporal de la transcripción."""
    if not segments or total_duration_sec <= 0:
        return 0.0

    # Crear intervalos cubiertos y fusionar overlaps
    intervals = sorted([(seg["start"], seg["end"]) for seg in segments])
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    covered = sum(end - start for start, end in merged)
    return min(100.0, (covered / total_duration_sec) * 100)


def retranscribe_gaps(client, audio_segment, gaps, model, status_text=None):
    """
    Re-transcribe secciones del audio donde se detectaron huecos.

    Args:
        client: Groq client
        audio_segment: pydub AudioSegment completo
        gaps: lista de huecos detectados
        model: modelo Whisper a usar
        status_text: streamlit element para mostrar progreso

    Returns:
        Lista de segmentos recuperados de los huecos
    """
    recovered_segments = []

    for gi, gap in enumerate(gaps):
        if status_text:
            status_text.write(f"🔄 Re-transcribiendo hueco {gi+1}/{len(gaps)}: "
                            f"{fmt_time(gap['start'])} → {fmt_time(gap['end'])} "
                            f"({gap['duration']:.0f}s)")

        # Extraer la sección del audio con margen extra
        margin_ms = 2000  # 2 segundos de margen
        start_ms = max(0, int(gap["start"] * 1000) - margin_ms)
        end_ms = min(len(audio_segment), int(gap["end"] * 1000) + margin_ms)

        gap_audio = audio_segment[start_ms:end_ms]

        # Exportar
        gap_path = os.path.join(tempfile.gettempdir(), f"gap_{gi}.mp3")
        gap_audio.export(gap_path, format="mp3", bitrate="128k")

        # Transcribir con reintentos
        text, segments, error = transcribe_single(client, gap_path, model, max_retries=3)

        if segments:
            # Ajustar timestamps al tiempo absoluto
            offset_sec = start_ms / 1000.0
            for seg in segments:
                seg["start"] += offset_sec
                seg["end"] += offset_sec
                seg["recovered"] = True  # Marcar como recuperado
            recovered_segments.extend(segments)

        # Limpiar
        try:
            os.remove(gap_path)
        except Exception:
            pass

    return recovered_segments


def transcribe_complete(client, path, model, progress_status=None):
    """
    Pipeline completo de transcripción que garantiza cobertura total.

    1. Obtener duración del audio
    2. Si es grande, dividir en chunks con overlap
    3. Transcribir cada chunk con reintentos
    4. Fusionar resultados eliminando duplicados
    5. Verificar cobertura
    6. Re-transcribir huecos detectados
    7. Fusionar segmentos recuperados

    Returns:
        (full_text, segments, audio_duration_ms, coverage_pct, gaps, chunks_used)
    """
    # Paso 1: Obtener duración y cargar audio
    if progress_status:
        progress_status.write("📏 Analizando audio...")

    duration_ms, audio_segment = get_audio_duration_ms(path)

    if duration_ms is None or audio_segment is None:
        # Fallback: transcripción directa sin pydub
        if progress_status:
            progress_status.write("⚠️ pydub no disponible, transcripción directa...")

        text, segments, error = transcribe_single(client, path, model)
        if error:
            return None, None, 0, 0, [], 1
        duration_sec = max(seg["end"] for seg in segments) if segments else 0
        coverage = calculate_coverage(segments, duration_sec)
        return text, segments, int(duration_sec * 1000), coverage, [], 1

    duration_sec = duration_ms / 1000.0
    if progress_status:
        progress_status.write(f"⏱️ Duración: {fmt_duration(duration_sec)}")

    # Paso 2: Dividir en chunks si es necesario
    # Chunk de 10 minutos con 15 segundos de overlap
    chunk_duration_ms = 600_000  # 10 minutos
    overlap_ms = 15_000  # 15 segundos

    chunks = split_audio_chunks(audio_segment, chunk_duration_ms, overlap_ms)
    n_chunks = len(chunks)

    if progress_status:
        if n_chunks > 1:
            progress_status.write(f"✂️ Audio dividido en {n_chunks} segmentos")
        else:
            progress_status.write("📦 Audio en un solo segmento")

    # Paso 3: Transcribir cada chunk
    all_results = []
    errors = []

    for ci, chunk in enumerate(chunks):
        if progress_status:
            progress_status.write(
                f"🎧 Transcribiendo segmento {ci+1}/{n_chunks} "
                f"({fmt_time(chunk['start_ms']/1000)} → {fmt_time(chunk['end_ms']/1000)})..."
            )

        text, segments, error = transcribe_single(client, chunk["path"], model)

        if error:
            errors.append(f"Chunk {ci+1}: {error}")
            if progress_status:
                progress_status.write(f"⚠️ Error en segmento {ci+1}: {error}")
        else:
            all_results.append({
                "text": text,
                "segments": segments,
                "start_ms": chunk["start_ms"],
                "end_ms": chunk["end_ms"],
                "index": ci
            })

        # Limpiar archivo temporal del chunk
        try:
            os.remove(chunk["path"])
        except Exception:
            pass

    if not all_results:
        return None, None, duration_ms, 0, [], n_chunks

    # Paso 4: Fusionar resultados
    if progress_status:
        progress_status.write("🔗 Fusionando segmentos...")

    merged_segments, full_text = merge_chunk_segments(all_results, overlap_ms)

    # Paso 5: Verificar cobertura
    coverage = calculate_coverage(merged_segments, duration_sec)
    gaps = find_coverage_gaps(merged_segments, duration_sec, gap_threshold=5.0)

    if progress_status:
        progress_status.write(f"📊 Cobertura inicial: {coverage:.1f}%")

    # Paso 6: Re-transcribir huecos significativos
    if gaps and coverage < 98.0:
        significant_gaps = [g for g in gaps if g["duration"] >= 3.0]  # Huecos de 3+ segundos

        if significant_gaps and progress_status:
            progress_status.write(
                f"🔍 Detectados {len(significant_gaps)} huecos, re-transcribiendo..."
            )

        if significant_gaps:
            recovered = retranscribe_gaps(
                client, audio_segment, significant_gaps, model, progress_status
            )

            if recovered:
                # Paso 7: Fusionar segmentos recuperados
                merged_segments.extend(recovered)
                merged_segments.sort(key=lambda x: x["start"])

                # Eliminar duplicados que pudieran surgir
                deduped = []
                for seg in merged_segments:
                    is_dup = False
                    for existing in deduped[-5:]:
                        if abs(seg["start"] - existing["start"]) < 1.0:
                            ratio = SequenceMatcher(
                                None, norm(seg["text"]), norm(existing["text"])
                            ).ratio()
                            if ratio > 0.7:
                                is_dup = True
                                break
                    if not is_dup:
                        deduped.append(seg)
                merged_segments = deduped

                # Reconstruir texto
                full_text = " ".join(seg["text"] for seg in merged_segments)

                # Recalcular cobertura
                coverage = calculate_coverage(merged_segments, duration_sec)
                gaps = find_coverage_gaps(merged_segments, duration_sec, gap_threshold=5.0)

                if progress_status:
                    progress_status.write(
                        f"✅ Cobertura después de recuperación: {coverage:.1f}% "
                        f"(+{len(recovered)} segmentos recuperados)"
                    )

    return full_text, merged_segments, duration_ms, coverage, gaps, n_chunks


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
def search_segments(query, segments, corrected_segments, context_words=30, fuzzy_thresh=0.75):
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

    # Búsqueda exacta de frase
    for i in range(len(search_norm) - len(q_words) + 1):
        window = " ".join(search_norm[i:i + len(q_words)])
        if q_norm in window:
            found.append({"pos": i, "len": len(q_words), "conf": "high", "score": 1.0, "seg": all_words[i][1]})

    # Búsqueda por palabras individuales
    if not found:
        for i, wn in enumerate(search_norm):
            for qw in q_words:
                if len(qw) > 2 and qw in wn:
                    found.append({"pos": i, "len": 1, "conf": "high", "score": 0.95, "seg": all_words[i][1]})
                    break

    # Búsqueda fuzzy
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

        full_segment_text = seg.get("text", "")
        prev_seg_text = target[fp["seg"] - 1].get("text", "") if fp["seg"] > 0 else ""
        next_seg_text = target[fp["seg"] + 1].get("text", "") if fp["seg"] < len(target) - 1 else ""

        results.append({
            "start_time": float(seg.get("start", 0)),
            "end_time": float(seg.get("end", 0)),
            "time_label": fmt_time(float(seg.get("start", 0))),
            "end_label": fmt_time(float(seg.get("end", 0))),
            "before": before, "match_hl": highlight_html(match, query),
            "after": after, "confidence": fp["conf"],
            "score": fp["score"], "idx": fp["seg"],
            "full_segment": full_segment_text,
            "prev_segment": prev_seg_text,
            "next_segment": next_seg_text,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def execute_search():
    query = st.session_state.get("q_input", "").strip()
    if query:
        st.session_state.last_search_query = query
        st.session_state._search_pending = True
    else:
        st.session_state.search_results = None
        st.session_state.last_search_query = ""


def reset_search():
    st.session_state.search_results = None
    st.session_state.last_search_query = ""


def reset_all():
    for k, v in DEFAULTS.items():
        if k != "authenticated":
            st.session_state[k] = v


def build_timestamped_transcript(segments):
    lines = []
    for seg in segments:
        t = fmt_time(float(seg.get("start", 0)))
        txt = seg.get("text", "").strip()
        if txt:
            lines.append(f"[{t}] {txt}")
    return "\n".join(lines)


def get_audio_duration(segments):
    if not segments:
        return 0
    return max(float(seg.get("end", 0)) for seg in segments)


# --- ANÁLISIS IA ---
def ai_generate(client, system_prompt, user_content, max_tokens=2048, temp=0.1):
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=temp, max_tokens=max_tokens
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"


def generate_summary(client, text):
    cache_key = "summary"
    if cache_key in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[cache_key]
    system = (
        "Eres un asistente experto en crear resúmenes claros y estructurados en español. "
        "Genera un resumen ejecutivo del siguiente texto transcrito de un audio. "
        "Estructura tu respuesta así:\n"
        "## Resumen Ejecutivo\nUn párrafo conciso con la idea principal.\n\n"
        "## Puntos Clave\nLista con viñetas de los puntos más importantes (máximo 7).\n\n"
        "## Conclusiones\nConclusiones principales o mensajes clave."
    )
    result = ai_generate(client, system, text[:12000])
    st.session_state.analysis_cache[cache_key] = result
    return result


def generate_topics(client, text):
    cache_key = "topics"
    if cache_key in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[cache_key]
    system = (
        "Eres un analizador de contenido experto. Analiza la transcripción y extrae:\n"
        "## Temas Principales\nLista los temas principales discutidos, con una breve descripción.\n\n"
        "## Palabras Clave\nLas 10-15 palabras o frases clave más relevantes.\n\n"
        "## Categoría del Contenido\nClasifica el tipo de contenido (conferencia, entrevista, reunión, etc.).\n\n"
        "Responde en español."
    )
    result = ai_generate(client, system, text[:12000])
    st.session_state.analysis_cache[cache_key] = result
    return result


def generate_action_items(client, text):
    cache_key = "actions"
    if cache_key in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[cache_key]
    system = (
        "Eres un asistente experto en extraer información accionable de transcripciones. "
        "Analiza el texto y extrae:\n"
        "## Tareas y Acciones Pendientes\nAcciones concretas mencionadas.\n\n"
        "## Decisiones Tomadas\nDecisiones que se tomaron o acordaron.\n\n"
        "## Preguntas Abiertas\nPreguntas que quedaron sin responder.\n\n"
        "## Compromisos\nCompromisos asumidos por algún participante.\n\n"
        "Si alguna sección no aplica, indícalo. Responde en español."
    )
    result = ai_generate(client, system, text[:12000])
    st.session_state.analysis_cache[cache_key] = result
    return result


def generate_sentiment(client, text):
    cache_key = "sentiment"
    if cache_key in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[cache_key]
    system = (
        "Eres un experto en análisis de sentimiento y tono. Analiza la transcripción:\n"
        "## Tono General\nDescribe el tono predominante.\n\n"
        "## Sentimiento\nSentimiento general: Positivo, Negativo, Neutro o Mixto.\n\n"
        "## Momentos Destacados\nFragmentos con carga emocional notable.\n\n"
        "## Nivel de Formalidad\nEscala del 1-10 con justificación.\n\n"
        "Responde en español."
    )
    result = ai_generate(client, system, text[:12000])
    st.session_state.analysis_cache[cache_key] = result
    return result


# --- PROCESO PRINCIPAL ---
def process_audio(client, uploaded, model, do_correct):
    size_mb = len(uploaded.getvalue()) / (1024 * 1024)

    reset_all()

    with st.status("Procesando audio...", expanded=True) as status:
        path = save_uploaded(uploaded)
        if not path:
            st.error("Error al guardar archivo")
            return False

        st.session_state.audio_path = path
        st.session_state.uploaded_filename = uploaded.name
        st.write(f"📁 {uploaded.name} — {size_mb:.1f} MB")

        # Transcripción completa con segmentación y verificación
        full_text, segments, duration_ms, coverage, gaps, chunks_used = transcribe_complete(
            client, path, model, progress_status=status
        )

        if not full_text or not segments:
            st.error("Error en la transcripción. Intenta con otro archivo o formato.")
            return False

        st.session_state.raw_transcript = full_text
        st.session_state.transcript_segments = segments
        st.session_state.audio_duration_ms = duration_ms
        st.session_state.coverage_pct = coverage
        st.session_state.transcript_gaps = gaps
        st.session_state.chunks_used = chunks_used

        # Corrección ortográfica
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

        st.session_state.audio_start_time = 0

        wc = len(full_text.split())
        sc = len(segments)

        # Resumen del estado
        coverage_icon = "✅" if coverage >= 95 else "⚠️" if coverage >= 80 else "❌"
        gap_info = f" · {len(gaps)} huecos" if gaps else ""
        chunk_info = f" · {chunks_used} chunks" if chunks_used > 1 else ""

        status.update(
            label=f"{coverage_icon} {wc:,} palabras · {sc} segmentos · {coverage:.0f}% cobertura{gap_info}{chunk_info}",
            state="complete", expanded=False
        )
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
        ctx_w = st.slider("Palabras contexto", 10, 60, 30, step=5)
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
                <div class="empty-state-text">MP3, WAV, M4A, OGG o MP4 — Sin límite de duración</div>
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
    segs = st.session_state.corrected_segments or []
    n_words = len(txt.split())
    n_segs = len(segs)
    duration = get_audio_duration(segs)
    coverage = st.session_state.coverage_pct
    gaps = st.session_state.transcript_gaps
    chunks_used = st.session_state.chunks_used

    corr_chip = "stat-chip stat-chip-ok" if st.session_state.correction_applied else "stat-chip"
    corr_text = "✓ Corregido" if st.session_state.correction_applied else "Original"

    # Chip de cobertura
    if coverage >= 95:
        cov_chip = "stat-chip stat-chip-ok"
        cov_icon = "✅"
    elif coverage >= 80:
        cov_chip = "stat-chip stat-chip-warn"
        cov_icon = "⚠️"
    else:
        cov_chip = "stat-chip"
        cov_icon = "❌"

    filename_display = st.session_state.uploaded_filename or "audio"
    chunk_html = f'<span class="stat-chip">✂️ <strong>{chunks_used}</strong> chunks</span>' if chunks_used > 1 else ""
    gap_html = f'<span class="stat-chip stat-chip-warn">🕳️ <strong>{len(gaps)}</strong> huecos</span>' if gaps else ""

    st.markdown(f"""
    <div class="stats-bar">
        <span class="stat-chip">📁 <strong>{filename_display}</strong></span>
        <span class="stat-chip">⏱️ <strong>{fmt_duration(duration)}</strong></span>
        <span class="stat-chip"><strong>{n_words:,}</strong> palabras</span>
        <span class="stat-chip"><strong>{n_segs}</strong> segmentos</span>
        <span class="{cov_chip}">{cov_icon} <strong>{coverage:.0f}%</strong> cobertura</span>
        <span class="{corr_chip}">{corr_text}</span>
        {chunk_html}
        {gap_html}
    </div>
    """, unsafe_allow_html=True)

    # Barra visual de cobertura
    if coverage < 100:
        cov_class = "coverage-ok" if coverage >= 95 else "coverage-warn" if coverage >= 80 else "coverage-bad"
        st.markdown(f"""
        <div class="coverage-bar-container">
            <div class="coverage-bar-fill {cov_class}" style="width:{coverage}%">{coverage:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    tab_search, tab_chat, tab_analysis, tab_export = st.tabs([
        "🔍 Búsqueda", "💬 Chat IA", "📊 Análisis", "📥 Exportar"
    ])

    # ===== BÚSQUEDA =====
    with tab_search:
        query = st.text_input(
            "q", placeholder="Buscar palabra o frase... (Enter para buscar)",
            label_visibility="collapsed", key="q_input",
            on_change=execute_search
        )

        if st.session_state.get("_search_pending"):
            sq = st.session_state.last_search_query
            st.session_state.search_results = search_segments(
                sq, st.session_state.transcript_segments,
                st.session_state.corrected_segments,
                context_words=ctx_w, fuzzy_thresh=fuzzy_t if use_fuzzy else 1.0
            )
            st.session_state._search_pending = False

        aq = st.session_state.last_search_query
        res = st.session_state.search_results

        if aq and res:
            total_occurrences = count_occurrences(txt, aq)
            st.caption(
                f"**{len(res)}** resultado{'s' if len(res) != 1 else ''} "
                f"({total_occurrences} ocurrencia{'s' if total_occurrences != 1 else ''}) "
                f"para \"{aq}\""
            )
            for i, r in enumerate(res):
                badge_cls = f"sr-badge-{r['confidence']}"
                bh = f"<span class='sr-ctx'>...{r['before']} </span>" if r['before'] else ""
                ah = f"<span class='sr-ctx'> {r['after']}...</span>" if r['after'] else ""

                expanded_ctx = ""
                if r.get('prev_segment') or r.get('next_segment'):
                    prev_hl = highlight_html(r['prev_segment'], aq) if r.get('prev_segment') else ""
                    next_hl = highlight_html(r['next_segment'], aq) if r.get('next_segment') else ""
                    ctx_parts = []
                    if prev_hl:
                        ctx_parts.append(f"<span class='sr-ctx'>↑ {prev_hl}</span>")
                    if next_hl:
                        ctx_parts.append(f"<span class='sr-ctx'>↓ {next_hl}</span>")
                    if ctx_parts:
                        expanded_ctx = f"<div class='sr-segment-full'>{'<br>'.join(ctx_parts)}</div>"

                rc1, rc2 = st.columns([0.6, 5])
                with rc1:
                    if st.button(f"▶ {r['time_label']}", key=f"p_{i}_{r['idx']}"):
                        st.session_state.audio_start_time = max(0, r["start_time"] - 2)
                        st.rerun()
                with rc2:
                    st.markdown(f"""
                    <div class="sr-card">
                        <div class="sr-head">
                            <span class="sr-time">{r['time_label']} → {r['end_label']}</span>
                            <span class="sr-badge {badge_cls}">{r['confidence']}</span>
                        </div>
                        <div class="sr-body">{bh}{r['match_hl']}{ah}</div>
                        {expanded_ctx}
                    </div>
                    """, unsafe_allow_html=True)

        elif aq and res is not None and len(res) == 0:
            st.markdown("""
            <div class="no-results-box">
                🔍 Sin resultados. Prueba con otras palabras o activa búsqueda aproximada.
            </div>
            """, unsafe_allow_html=True)

        # Texto completo siempre visible con resaltado
        st.markdown("---")
        st.markdown("##### 📄 Texto completo")

        if aq:
            total_in_text = count_occurrences(txt, aq)
            if total_in_text > 0:
                st.caption(f"🔶 {total_in_text} ocurrencia{'s' if total_in_text != 1 else ''} resaltada{'s' if total_in_text != 1 else ''}")
            hl_text = highlight_full_text(txt, aq)
        else:
            hl_text = txt

        st.markdown(f"<div class='full-text-box'>{hl_text}</div>", unsafe_allow_html=True)

        # Huecos detectados
        if gaps:
            st.markdown("---")
            with st.expander(f"⚠️ {len(gaps)} hueco{'s' if len(gaps) != 1 else ''} detectado{'s' if len(gaps) != 1 else ''} en la transcripción", expanded=False):
                st.caption("Secciones del audio donde no se detectó habla (posible silencio, música o ruido)")
                for gi, gap in enumerate(gaps):
                    st.markdown(
                        f"`{fmt_time(gap['start'])}` → `{fmt_time(gap['end'])}` "
                        f"— **{gap['duration']:.1f}s** sin transcripción"
                    )

        # Nuevo archivo
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
                    segs_for_ctx = st.session_state.corrected_segments or st.session_state.transcript_segments or []
                    timestamped_ctx = build_timestamped_transcript(segs_for_ctx)
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

        if st.session_state.chat_history:
            if st.button("🗑️ Limpiar conversación", use_container_width=False):
                st.session_state.chat_history = []
                st.rerun()

    # ===== ANÁLISIS =====
    with tab_analysis:
        st.markdown("##### 📊 Análisis Inteligente")

        chars = len(txt)
        sentences = len(re.split(r'[.!?]+', txt))
        avg_word_len = round(sum(len(w) for w in txt.split()) / max(n_words, 1), 1)
        wpm = round(n_words / max(duration / 60, 1))

        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-value">{n_words:,}</div><div class="kpi-label">Palabras</div></div>
            <div class="kpi-card"><div class="kpi-value">{sentences}</div><div class="kpi-label">Oraciones</div></div>
            <div class="kpi-card"><div class="kpi-value">{chars:,}</div><div class="kpi-label">Caracteres</div></div>
            <div class="kpi-card"><div class="kpi-value">{wpm}</div><div class="kpi-label">Palabras/min</div></div>
            <div class="kpi-card"><div class="kpi-value">{fmt_duration(duration)}</div><div class="kpi-label">Duración</div></div>
            <div class="kpi-card"><div class="kpi-value">{coverage:.0f}%</div><div class="kpi-label">Cobertura</div></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        an_col1, an_col2 = st.columns(2)

        with an_col1:
            if st.button("📝 Generar Resumen", use_container_width=True, type="primary"):
                with st.spinner("Generando resumen..."):
                    st.session_state.analysis_cache["summary"] = generate_summary(client, txt)
            if "summary" in st.session_state.analysis_cache:
                with st.expander("📝 Resumen", expanded=True):
                    st.markdown(st.session_state.analysis_cache["summary"])

        with an_col2:
            if st.button("🏷️ Extraer Temas", use_container_width=True, type="primary"):
                with st.spinner("Extrayendo temas..."):
                    st.session_state.analysis_cache["topics"] = generate_topics(client, txt)
            if "topics" in st.session_state.analysis_cache:
                with st.expander("🏷️ Temas", expanded=True):
                    st.markdown(st.session_state.analysis_cache["topics"])

        st.markdown("---")

        an_col3, an_col4 = st.columns(2)

        with an_col3:
            if st.button("✅ Tareas y Decisiones", use_container_width=True):
                with st.spinner("Extrayendo acciones..."):
                    st.session_state.analysis_cache["actions"] = generate_action_items(client, txt)
            if "actions" in st.session_state.analysis_cache:
                with st.expander("✅ Tareas y Decisiones", expanded=True):
                    st.markdown(st.session_state.analysis_cache["actions"])

        with an_col4:
            if st.button("🎭 Análisis de Tono", use_container_width=True):
                with st.spinner("Analizando tono..."):
                    st.session_state.analysis_cache["sentiment"] = generate_sentiment(client, txt)
            if "sentiment" in st.session_state.analysis_cache:
                with st.expander("🎭 Análisis de Tono", expanded=True):
                    st.markdown(st.session_state.analysis_cache["sentiment"])

        # Palabras frecuentes
        st.markdown("---")
        st.markdown("##### 📈 Palabras más frecuentes")

        stopwords_es = {
            'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por',
            'un', 'para', 'con', 'no', 'una', 'su', 'al', 'lo', 'como', 'más', 'pero',
            'sus', 'le', 'ya', 'o', 'este', 'sí', 'porque', 'esta', 'entre', 'cuando',
            'muy', 'sin', 'sobre', 'también', 'me', 'hasta', 'hay', 'donde', 'quien',
            'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra',
            'otros', 'ese', 'eso', 'ante', 'ellos', 'esto', 'antes', 'algunos',
            'qué', 'unos', 'yo', 'otro', 'otras', 'otra', 'él', 'tanto', 'esa', 'estos',
            'mucho', 'quienes', 'nada', 'muchos', 'cual', 'poco', 'ella', 'estar', 'estas',
            'algunas', 'algo', 'nosotros', 'mi', 'mis', 'tú', 'te', 'ti', 'tu', 'tus',
            'ellas', 'nosotras', 'vosotros', 'vosotras', 'os',
            'es', 'son', 'fue', 'ser', 'ha', 'han', 'era', 'sido', 'tiene',
            'puede', 'hacer', 'cada', 'hemos', 'vamos', 'va',
            'así', 'pues', 'bueno', 'entonces', 'después', 'ahora', 'aquí', 'bien',
            'sólo', 'solo', 'vez', 'esas', 'dos', 'tres', 'mas', 'sea',
            'si', 'he', 'tal', 'esos', 'tan',
        }

        words_clean = re.findall(r'\b[a-záéíóúñü]{3,}\b', txt.lower())
        word_freq = {}
        for w in words_clean:
            if w not in stopwords_es:
                word_freq[w] = word_freq.get(w, 0) + 1

        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:20]

        if top_words:
            max_freq = top_words[0][1]
            word_bars = []
            for word, freq in top_words:
                pct = (freq / max_freq) * 100
                word_bars.append(
                    f"<div style='display:flex;align-items:center;gap:8px;margin:3px 0;font-size:0.78rem'>"
                    f"<span style='width:100px;font-weight:500;color:var(--text)'>{word}</span>"
                    f"<div style='flex:1;background:var(--bg);border-radius:4px;height:18px;overflow:hidden'>"
                    f"<div style='width:{pct}%;background:linear-gradient(90deg,#fed7aa,#ea580c);height:100%;border-radius:4px'></div>"
                    f"</div>"
                    f"<span style='width:30px;text-align:right;color:var(--text-secondary);font-size:0.72rem'>{freq}</span>"
                    f"</div>"
                )
            st.markdown("".join(word_bars), unsafe_allow_html=True)

    # ===== EXPORTAR =====
    with tab_export:
        st.markdown("##### 📥 Exportar Transcripción")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                "📄 Texto plano (.txt)", data=txt, file_name="transcripcion.txt",
                mime="text/plain", use_container_width=True
            )
        with c2:
            srt = []
            for i, seg in enumerate(segs):
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
        with c3:
            ts_lines = []
            for seg in segs:
                t = fmt_time(float(seg.get("start", 0)))
                ts_lines.append(f"[{t}] {seg.get('text', '')}")
            st.download_button(
                "⏱️ Con timestamps (.txt)", data="\n".join(ts_lines),
                file_name="transcripcion_timestamps.txt", mime="text/plain", use_container_width=True
            )

        st.markdown("---")

        c4, c5 = st.columns(2)
        with c4:
            json_data = {
                "filename": st.session_state.uploaded_filename,
                "date": datetime.now().isoformat(),
                "duration_seconds": duration,
                "word_count": n_words,
                "coverage_percent": coverage,
                "chunks_used": chunks_used,
                "gaps": gaps,
                "correction_applied": st.session_state.correction_applied,
                "full_text": txt,
                "segments": segs,
            }
            st.download_button(
                "🗂️ Datos completos (.json)",
                data=json.dumps(json_data, ensure_ascii=False, indent=2),
                file_name="transcripcion.json", mime="application/json", use_container_width=True
            )
        with c5:
            if st.session_state.analysis_cache:
                analysis_export = {
                    "filename": st.session_state.uploaded_filename,
                    "date": datetime.now().isoformat(),
                    "analyses": st.session_state.analysis_cache,
                }
                st.download_button(
                    "📊 Exportar análisis (.json)",
                    data=json.dumps(analysis_export, ensure_ascii=False, indent=2),
                    file_name="analisis.json", mime="application/json", use_container_width=True
                )
            else:
                st.button("📊 Exportar análisis", disabled=True, use_container_width=True,
                          help="Genera al menos un análisis primero")

        st.markdown("---")
        show_ts = st.checkbox("Ver transcripción con timestamps", value=False, key="show_timestamps")
        if show_ts:
            for seg in segs:
                t_start = fmt_time(float(seg.get('start', 0)))
                sc1, sc2 = st.columns([0.8, 5])
                with sc1:
                    st.caption(f"`{t_start}`")
                with sc2:
                    recovered_tag = " 🔄" if seg.get("recovered") else ""
                    st.markdown(
                        f"<span style='font-size:0.83rem'>{seg.get('text','')}{recovered_tag}</span>",
                        unsafe_allow_html=True
                    )


if __name__ == "__main__":
    if check_password():
        main_app()
