WLK_WS_URL = "ws://localhost:8000/asr?language=auto&mode=diff"
WLK_HEALTH_URL = "http://localhost:8000/health"

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.25

NLLB_MODEL = "facebook/nllb-200-1.3B"
TARGET_LANGUAGE = "deu_Latn"
NLLB_BEAM_SIZE = 4
NLLB_MAX_NEW_TOKENS = 256

WHISPER_TO_NLLB = {
    "ru": "rus_Cyrl",
    "en": "eng_Latn",
    "fr": "fra_Latn",
    "es": "spa_Latn",
    "uk": "ukr_Cyrl",
    "th": "tha_Thai",
    "vi": "vie_Latn",
    "zh": "zho_Hans",
    "ko": "kor_Hang",
    "ja": "jpn_Jpan",
}

LANGUAGE_NAMES = {
    "ru": "Russisch",
    "en": "Englisch",
    "fr": "Französisch",
    "es": "Spanisch",
    "uk": "Ukrainisch",
    "th": "Thai",
    "vi": "Vietnamesisch",
    "zh": "Chinesisch",
    "ko": "Koreanisch",
    "ja": "Japanisch",
}

MAX_PENDING_CHARACTERS = 220
MAX_PENDING_SECONDS = 3.0

SUBTITLE_HISTORY = 50
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 340
MIN_WINDOW_WIDTH = 600
MIN_WINDOW_HEIGHT = 220


# Audio-Diagnose
AUDIO_LEVEL_STATUS_INTERVAL = 1.0
AUDIO_SILENCE_WARNING_SECONDS = 5.0
AUDIO_ACTIVE_RMS_THRESHOLD = 0.0002


# Segmentierung und Kontext
SEGMENT_MIN_CHARACTERS = 24
SEGMENT_MAX_CHARACTERS = 280
SEGMENT_MAX_SENTENCES = 3
SEGMENT_FLUSH_SECONDS = 2.0

# Übersetzungs-Vorbereitung
TRANSLATION_BATCH_SIZE = 4
TRANSLATION_BATCH_WAIT_SECONDS = 0.20


# Integrierter WhisperLiveKit-Server
WLK_HOST = "127.0.0.1"
WLK_PORT = 8000
WLK_MODEL = "large-v3"
WLK_LANGUAGE = "auto"
WLK_BACKEND = "faster-whisper"
WLK_POLICY = "simulstreaming"


# Bewährte WhisperLiveKit-Serverkonfiguration
# Referenzlauf: 97 % Wort- und 92 % Zeichenabdeckung.
WLK_AUDIO_MAX_LEN = 45
WLK_BUFFER_TRIMMING = "segment"
WLK_BUFFER_TRIMMING_SEC = 15
WLK_MAX_CONTEXT_TOKENS = 0
WLK_LOG_LEVEL = "INFO"

# CUDA-DLL-Ordner aus der bestehenden funktionierenden Umgebung
TORCH_DLL_PATH = (
    r"E:\KI\LiveTranslate\venv\Lib\site-packages\torch\lib"
)

SERVER_START_TIMEOUT_SECONDS = 120
SERVER_STOP_TIMEOUT_SECONDS = 8


SOURCE_LANGUAGE_OPTIONS = {
    "auto": "Automatisch",
    "ru": "Russisch",
    "en": "Englisch",
    "fr": "Französisch",
    "es": "Spanisch",
    "uk": "Ukrainisch",
    "th": "Thai",
    "vi": "Vietnamesisch",
    "zh": "Chinesisch",
    "ko": "Koreanisch",
    "ja": "Japanisch",
}

DEFAULT_SOURCE_LANGUAGE = "auto"


# Oberfläche / Diagnose
DEBUG_MODE_DEFAULT = False
SHOW_SERVER_LOG_DEFAULT = False


# Konservative Kontextübersetzung
CONTEXT_MAX_SENTENCES = 3
CONTEXT_MAX_CHARACTERS = 420
CONTEXT_FLUSH_SECONDS = 2.5


# Verbesserte Transkript-Zusammenführung
ASR_OVERLAP_MAX_WORDS = 80
ASR_FUZZY_WORD_SIMILARITY = 0.86
ASR_DUPLICATE_SIMILARITY = 0.94
ASR_RECENT_LINE_CACHE = 80
ASR_MIN_TEXT_CHARACTERS = 2


# Pipeline-Diagnose
PIPELINE_DEBUG_ENABLED = False
PIPELINE_DEBUG_FILE = "logs/pipeline_debug.log"
PIPELINE_DEBUG_GUI_TEXT_LIMIT = 320


# Ein Kontextblock wird auch bei durchgehender Sprache spätestens
# nach dieser Zeit ausgegeben.
CONTEXT_MAX_WAIT_SECONDS = 6.0


# Offline-Referenzvergleich
REFERENCE_OUTPUT_DIR = "logs/reference"
REFERENCE_MODEL = "large-v3"
REFERENCE_BEAM_SIZE = 5
REFERENCE_COMPUTE_TYPE = "float16"


WLK_DRAIN_TIMEOUT_SECONDS = 30.0


# Robustheit: Audio
AUDIO_GAIN_ENABLED = True
AUDIO_GAIN_TARGET_RMS = 0.035
AUDIO_GAIN_MAX = 12.0
AUDIO_GAIN_MIN_INPUT_RMS = 0.00008
AUDIO_GAIN_SMOOTHING = 0.20
AUDIO_CLIP_LIMIT = 0.98

# Ein RMS-Ausschlag oberhalb dieser Grenze gilt sicher als Systemton.
AUDIO_SIGNAL_PRESENT_RMS = 0.00012

# Robustheit: ASR / WebSocket
WLK_CONNECT_RETRIES = 8
WLK_CONNECT_RETRY_SECONDS = 1.0
WLK_ASR_WATCHDOG_SECONDS = 12.0

# Solange die automatische Sprache noch nicht sicher erkannt ist,
# werden übersetzbare Kontextblöcke nicht verworfen.
PENDING_LANGUAGE_SEGMENTS_MAX = 32


# LiveLineTracker
ASR_LINE_STALE_SECONDS = 1.8
ASR_LINE_MAX_SECONDS = 12.0
