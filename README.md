<div align="center">

<br/>

```
████████╗██████╗  █████╗ ███╗   ██╗███████╗ ██████╗██████╗ ██╗██████╗ ████████╗ ██████╗ ██████╗ 
╚══██╔══╝██╔══██╗██╔══██╗████╗  ██║██╔════╝██╔════╝██╔══██╗██║██╔══██╗╚══██╔══╝██╔═══██╗██╔══██╗
   ██║   ██████╔╝███████║██╔██╗ ██║███████╗██║     ██████╔╝██║██████╔╝   ██║   ██║   ██║██████╔╝
   ██║   ██╔══██╗██╔══██║██║╚██╗██║╚════██║██║     ██╔══██╗██║██╔═══╝    ██║   ██║   ██║██╔══██╗
   ██║   ██║  ██║██║  ██║██║ ╚████║███████║╚██████╗██║  ██║██║██║        ██║   ╚██████╔╝██║  ██║
   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝╚═╝        ╚═╝    ╚═════╝ ╚═╝  ╚═╝
                                                                                              PRO
```

### 🎙️ Transcripción inteligente de audio con IA · Para periodistas y productores de contenido

<br/>

![Python](https://img.shields.io/badge/Python-3.10+-EA580C?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Whisper_V3-F97316?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PC9zdmc+&logoColor=white)
![LLaMA](https://img.shields.io/badge/LLaMA-3.3_70B-C2410C?style=for-the-badge&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-Activo-4CAF50?style=for-the-badge)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tj-criptor.streamlit.app/)

<br/>

> **Transcriptor Pro** convierte archivos de audio en texto, entidades, titulares, subtítulos y análisis periodístico — potenciado por **Whisper Large V3** para la transcripción y **LLaMA 3.3 70B** para el razonamiento. Diseñado para periodistas que necesitan ir de la grabación al artículo sin fricciones.

<br/>

</div>

---

## 🗺️ Tabla de contenidos

- [¿Qué hace?](#-qué-hace)
- [Demo y capturas](#-demo-y-capturas)
- [Arquitectura](#-arquitectura)
- [Instalación](#-instalación)
- [Configuración de secretos](#-configuración-de-secretos)
- [Uso](#-uso)
- [Funcionalidades detalladas](#-funcionalidades-detalladas)
- [Modelos y IA](#-modelos-y-ia)
- [Stack técnico](#-stack-técnico)
- [Autor](#-autor)

---

## ✨ ¿Qué hace?

Transcriptor Pro es una aplicación web full-stack que toma un archivo de audio y entrega **un flujo de trabajo periodístico completo**:

```
🎵 Audio (MP3/WAV/M4A/OGG/MP4)
        ↓
🔄 Conversión y normalización (ffmpeg)
        ↓
✂️ División en chunks con overlap (archivos largos)
        ↓
🎧 Transcripción con Whisper Large V3 (Groq)
        ↓
🕳️ Detección y recuperación de huecos de cobertura
        ↓
✨ Corrección ortográfica (LLaMA 3.3 70B)
        ↓
┌──────────────────────────────────────────┐
│  🔍 Búsqueda  ·  🏷️ Entidades           │
│  📰 Lead      ·  💬 Chat IA             │
│  📊 Análisis  ·  📥 Exportar            │
└──────────────────────────────────────────┘
```

---

## 🏗️ Arquitectura

```
app.py  (UI + orquestación)
│
├── AUTH          → check_password() — acceso por contraseña vía st.secrets
│
├── AUDIO PIPELINE
│   ├── save_uploaded()          — guarda el archivo en /tmp
│   ├── convert_to_mp3()         — ffmpeg: normaliza, mono, 16kHz, 64kbps
│   ├── split_audio_chunks()     — chunks de 10 min con 30s de overlap
│   ├── transcribe_single()      — llamada a Groq Whisper + retry logic
│   ├── merge_chunk_segments()   — fusiona segmentos con dedup por similitud
│   ├── find_coverage_gaps()     — detecta silencios > 5s sin transcripción
│   └── retranscribe_gaps()      — re-transcribe huecos con margen extra
│
├── POST-PROCESAMIENTO
│   ├── post_correct_with_vocabulary()  — aplica vocabulario personalizado
│   └── correct_and_align()             — corrección ortográfica + realineado
│
├── IA (Groq · LLaMA 3.3 70B)
│   ├── extract_entities()       — NER: personas, orgs, lugares, fechas
│   ├── generate_lead()          — titular + subtítulo + lead + contexto
│   ├── generate_summary()       — resumen ejecutivo + puntos clave
│   ├── generate_topics()        — temas + palabras clave + categoría
│   ├── generate_action_items()  — tareas, decisiones, compromisos
│   └── generate_sentiment()     — tono, sentimiento y formalidad
│
├── BÚSQUEDA
│   ├── search_segments()        — búsqueda exacta + substring + fuzzy
│   └── global_search()          — búsqueda cruzada entre múltiples audios
│
└── HISTORIAL
    ├── history_save_current()   — snapshot completo en session_state
    └── history_load()           — restaura estado de un audio anterior
```

---

## 🚀 Instalación

### Prerrequisitos

- Python **3.10+**
- `ffmpeg` instalado en el sistema
- Cuenta en [Groq](https://console.groq.com) (tier gratuito suficiente para pruebas)

### Instalar ffmpeg

```bash
# Ubuntu / Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows (via Chocolatey)
choco install ffmpeg
```

### Instalar la app

```bash
# 1. Clonar el repositorio
git clone https://github.com/tu-usuario/transcriptor-pro.git
cd transcriptor-pro

# 2. Entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows

# 3. Dependencias
pip install -r requirements.txt

# 4. Configurar secretos (ver sección siguiente)
mkdir -p .streamlit
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# → edita secrets.toml con tus claves

# 5. Lanzar
streamlit run app.py
```

---

## 🔐 Configuración de secretos

Crea el archivo `.streamlit/secrets.toml`:

```toml
[general]
app_password   = "tu_contraseña_aquí"
groq_api_key   = "gsk_xxxxxxxxxxxxxxxxxxxx"
```

| Variable | Descripción | Dónde obtenerla |
|----------|-------------|-----------------|
| `app_password` | Contraseña de acceso a la app | La defines tú |
| `groq_api_key` | API key de Groq (Whisper + LLaMA) | [console.groq.com](https://console.groq.com) |

> **Para despliegue en Streamlit Cloud:** configura estos valores en *Settings → Secrets* del dashboard de tu app, no subas el archivo `.toml` al repositorio.

---

## 📖 Uso

### Formatos de audio soportados

| Formato | Extensión | Notas |
|---------|-----------|-------|
| MP3 | `.mp3` | Nativo, sin conversión |
| WAV | `.wav` | Convertido a MP3 mono 16kHz |
| M4A | `.m4a` | Requiere ffmpeg |
| OGG | `.ogg` | Requiere ffmpeg |
| MP4 | `.mp4` | Extrae solo el audio |

### Flujo típico

```
1. Login con contraseña
         ↓
2. Subir archivo de audio
         ↓
3. (Opcional) Ingresar vocabulario personalizado
   Ej: nombres propios, términos técnicos, marcas
         ↓
4. ▶ Transcribir
   El progreso se muestra en tiempo real
         ↓
5. Explorar los resultados en las 6 pestañas:
   🔍 Búsqueda · 🏷️ Entidades · 🌐 Global
   💬 Chat IA  · 📊 Análisis  · 📥 Exportar
         ↓
6. Agregar más audios y búsqueda cruzada global
```

---

## 🔬 Funcionalidades detalladas

### 🔍 Búsqueda

Busca cualquier palabra o frase en la transcripción con tres niveles de precisión:

- **Exacta:** coincidencia directa de la cadena completa
- **Substring:** la palabra buscada aparece dentro de otra
- **Fuzzy:** similitud configurable (0.5–1.0) para errores de transcripción

Cada resultado muestra el contexto circundante, un botón `▶ MM:SS` que salta el reproductor a ese momento exacto, y badges de confianza (`high / medium / low`).

### 🏷️ Entidades (NER)

Extracción de entidades nombradas con LLaMA 3.3 70B, clasificadas en:

| Categoría | Ejemplos |
|-----------|---------|
| 👤 Personas | Nombres de entrevistados, fuentes |
| 🏛️ Organizaciones | Empresas, instituciones, medios |
| 📍 Lugares | Ciudades, países, direcciones |
| 📅 Fechas | Días, períodos, referencias temporales |
| 🏷️ Conceptos clave | Términos relevantes para la noticia |

El parser de JSON es robusto: maneja markdown fences, comillas simples, prefijos de texto y extracción por regex como último recurso.

### 📰 Lead periodístico

Genera automáticamente la estructura de una noticia a partir del audio:

```
TITULAR    → Máx. 12 palabras, impactante y preciso
SUBTÍTULO  → Amplía el titular (máx. 20 palabras)
LEAD       → Qué, Quién, Cuándo, Dónde, Por qué (máx. 60 palabras)
CONTEXTO   → Antecedentes relevantes (máx. 3 oraciones)
```

### 🌐 Búsqueda global

Con múltiples audios cargados en sesión, busca una palabra o frase **en todos los archivos simultáneamente**. Los resultados se agrupan por archivo con botones de salto directo.

### 💬 Chat IA

Conversación con LLaMA 3.3 70B anclada al contenido del audio. El modelo solo responde con información que existe en la transcripción, cita timestamps `[MM:SS]` y rechaza explícitamente preguntas fuera del contenido.

### 📊 Análisis automático

- Resumen ejecutivo + puntos clave
- Extracción de temas y palabras clave
- Tareas, decisiones y compromisos
- Análisis de tono y nivel de formalidad
- Frecuencia de palabras (top 20, sin stopwords)

### 📥 Exportación

| Formato | Contenido |
|---------|-----------|
| `.txt` | Texto limpio de la transcripción |
| `.srt` | Subtítulos con timestamps en formato estándar |
| `_timestamps.txt` | Transcripción con marca de tiempo por segmento |
| `.json` (completo) | Todo: texto, segmentos, entidades, lead, metadatos |
| `.json` (análisis) | Solo los análisis de IA generados |
| `sesion_completa.json` | Todos los audios de la sesión |

---

## 🧠 Modelos y IA

### Transcripción — Groq Whisper

| Modelo | Velocidad | Precisión | Uso recomendado |
|--------|-----------|-----------|-----------------|
| `whisper-large-v3` | Más lento | ⭐⭐⭐⭐⭐ | Entrevistas largas, terminología técnica |
| `whisper-large-v3-turbo` | Rápido | ⭐⭐⭐⭐ | Archivos cortos, pruebas rápidas |

### Manejo de archivos largos

Los audios superiores a 10 minutos se dividen en chunks con **30 segundos de overlap** para evitar cortes abruptos. Los segmentos se fusionan con deduplicación por similitud de texto (`SequenceMatcher > 0.65`).

### Recuperación de cobertura

Si tras la transcripción quedan huecos > 5 segundos sin texto, el sistema los detecta y los re-transcribe de forma automática con hasta 3 pasadas progresivas, reduciendo el umbral de gap en cada iteración.

### Vocabulario personalizado

El vocabulario ingresado por el usuario se inyecta como `prompt` en la llamada a Whisper (mejora la transcripción en tiempo real) y luego se aplica como post-corrección con LLaMA para corregir casos que Whisper haya malinterpretado.

---

## 🛠️ Stack técnico

| Capa | Tecnología |
|------|-----------|
| UI / Web | `streamlit` |
| Transcripción | `groq` SDK → Whisper Large V3 |
| Razonamiento IA | `groq` SDK → LLaMA 3.3 70B Versatile |
| Audio I/O | `pydub`, `ffmpeg` |
| Búsqueda fuzzy | `difflib.SequenceMatcher` |
| Procesamiento texto | `unicodedata`, `re` |
| Frontend embebido | `streamlit.components.v1` (JS para control de audio) |

### `requirements.txt` sugerido

```txt
streamlit>=1.32.0
groq>=0.9.0
pydub>=0.25.1
```

> `ffmpeg` debe estar instalado a nivel de sistema (no vía pip).

---

## 📁 Estructura del proyecto

```
transcriptor-pro/
│
├── app.py                        # App completa (UI + lógica)
│
├── .streamlit/
│   ├── secrets.toml              # 🔒 NO subir a git
│   └── secrets.toml.example     # Plantilla de ejemplo
│
├── requirements.txt
└── README.md
```

---

## 👤 Autor

<div align="center">

**Johnathan Cortés** 🕵️😼

_Analista de datos · Bogotá, Colombia_

[![GitHub](https://img.shields.io/badge/GitHub-johnathanacortesd-EA580C?style=flat-square&logo=github)](https://github.com/johnathanacortesd)

<br/>

> _"De la grabación al artículo, sin perder ni una cita."_

<br/>

---

<sub>Construido con ☕ ffmpeg y muchas transcripciones fallidas · 2026</sub>

</div>
