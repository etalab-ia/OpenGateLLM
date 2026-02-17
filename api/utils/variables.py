from enum import StrEnum

DEFAULT_APP_NAME = "OpenGateLLM"
DEFAULT_TIMEOUT = 300

PREFIX__CELERY_QUEUE_ROUTING = "ogl_qr"
PREFIX__REDIS_METRIC_GAUGE = "ogl_mg"
PREFIX__REDIS_METRIC_TIMESERIE = "ogl_ts"
PREFIX__REDIS_RATE_LIMIT = "ogl_rt"
REDIS__TIMESERIE_RETENTION_SECONDS = 120


class RouterName(StrEnum):
    ADMIN = "admin"
    AUDIO = "audio"
    AUTH = "auth"
    CHAT = "chat"
    CHUNKS = "chunks"
    COLLECTIONS = "collections"
    DOCUMENTS = "documents"
    EMBEDDINGS = "embeddings"
    FILES = "files"  # Inutile
    MODELS = "models"
    MONITORING = "monitoring"
    OCR = "ocr"
    PARSE = "parse"
    RERANK = "rerank"
    SEARCH = "search"
    ME = "me"


class EndpointRoute(StrEnum):
    ADMIN_ORGANIZATIONS = f"/{RouterName.ADMIN}/organizations"
    ADMIN_PROVIDERS = f"/{RouterName.ADMIN}/providers"
    ADMIN_ROLES = f"/{RouterName.ADMIN}/roles"
    ADMIN_ROUTERS = f"/{RouterName.ADMIN}/routers"
    ADMIN_TOKENS = f"/{RouterName.ADMIN}/tokens"
    ADMIN_USERS = f"/{RouterName.ADMIN}/users"
    AUDIO_TRANSCRIPTIONS = f"/{RouterName.AUDIO}/transcriptions"
    AUTH_LOGIN = f"/{RouterName.AUTH}/login"
    CHAT_COMPLETIONS = f"/{RouterName.CHAT}/completions"
    CHUNKS = f"/{RouterName.CHUNKS}"
    COLLECTIONS = f"/{RouterName.COLLECTIONS}"
    DOCUMENTS = f"/{RouterName.DOCUMENTS}"
    EMBEDDINGS = f"/{RouterName.EMBEDDINGS}"
    FILES = f"/{RouterName.FILES}"
    ME_INFO = f"/{RouterName.ME}/info"
    ME_KEYS = f"/{RouterName.ME}/keys"
    ME_USAGE = f"/{RouterName.ME}/usage"
    MODELS = f"/{RouterName.MODELS}"
    OCR = f"/{RouterName.OCR}"
    OCR_BETA = f"/{RouterName.OCR}-beta"
    PARSE = f"/{RouterName.PARSE}-beta"
    RERANK = f"/{RouterName.RERANK}"
    SEARCH = f"/{RouterName.SEARCH}"


# Supported language from https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/tokenization_whisper.py
SUPPORTED_LANGUAGES = {
    "afrikaans": "af",
    "albanian": "sq",
    "amharic": "am",
    "arabic": "ar",
    "armenian": "hy",
    "assamese": "as",
    "azerbaijani": "az",
    "bashkir": "ba",
    "basque": "eu",
    "belarusian": "be",
    "bengali": "bn",
    "bosnian": "bs",
    "breton": "br",
    "bulgarian": "bg",
    "burmese": "my",
    "cantonese": "yue",
    "castilian": "es",
    "catalan": "ca",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "faroese": "fo",
    "finnish": "fi",
    "flemish": "nl",
    "french": "fr",
    "galician": "gl",
    "georgian": "ka",
    "german": "de",
    "greek": "el",
    "gujarati": "gu",
    "haitian": "ht",
    "haitian creole": "ht",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "kannada": "kn",
    "kazakh": "kk",
    "khmer": "km",
    "korean": "ko",
    "lao": "lo",
    "latin": "la",
    "latvian": "lv",
    "letzeburgesch": "lb",
    "lingala": "ln",
    "lithuanian": "lt",
    "luxembourgish": "lb",
    "macedonian": "mk",
    "malagasy": "mg",
    "malay": "ms",
    "malayalam": "ml",
    "maltese": "mt",
    "mandarin": "zh",
    "maori": "mi",
    "marathi": "mr",
    "moldavian": "ro",
    "moldovan": "ro",
    "mongolian": "mn",
    "myanmar": "my",
    "nepali": "ne",
    "norwegian": "no",
    "nynorsk": "nn",
    "occitan": "oc",
    "panjabi": "pa",
    "pashto": "ps",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "punjabi": "pa",
    "pushto": "ps",
    "romanian": "ro",
    "russian": "ru",
    "sanskrit": "sa",
    "serbian": "sr",
    "shona": "sn",
    "sindhi": "sd",
    "sinhala": "si",
    "sinhalese": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "somali": "so",
    "spanish": "es",
    "sundanese": "su",
    "swahili": "sw",
    "swedish": "sv",
    "tagalog": "tl",
    "tajik": "tg",
    "tamil": "ta",
    "tatar": "tt",
    "telugu": "te",
    "thai": "th",
    "tibetan": "bo",
    "turkish": "tr",
    "turkmen": "tk",
    "ukrainian": "uk",
    "urdu": "ur",
    "uzbek": "uz",
    "valencian": "ca",
    "vietnamese": "vi",
    "welsh": "cy",
    "yiddish": "yi",
    "yoruba": "yo",
}

SUPPORTED_LANGUAGES_VALUES = sorted(set(SUPPORTED_LANGUAGES.values())) + sorted(set(SUPPORTED_LANGUAGES.keys()))
