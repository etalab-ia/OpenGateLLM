from enum import StrEnum

DEFAULT_APP_NAME: str = "OpenGateLLM"
DEFAULT_TIMEOUT: int = 300
SYSTEM_PLAYGROUND_KEY_NAME: str = "_system_playground_key"
MIN_PASSWORD_LENGTH: int = 6
MAX_PASSWORD_LENGTH: int = 72


PREFIX__CELERY_QUEUE_ROUTING: str = "ogl_qr"
PREFIX__REDIS_METRIC_GAUGE: str = "ogl_mg"
PREFIX__REDIS_METRIC_TIMESERIE: str = "ogl_ts"
PREFIX__REDIS_RATE_LIMIT: str = "ogl_rt"
METRICS__TIMESERIE_RETENTION_SECONDS: int = 60 * 30  # 30 minutes


class RouterName(StrEnum):
    ADMIN = ("admin", "api.infrastructure.fastapi.endpoints.admin")
    AUDIO = ("audio", "api.infrastructure.fastapi.endpoints.audio")
    AUTH = ("auth", "api.infrastructure.fastapi.endpoints.auth")
    CHAT = ("chat", "api.endpoints.chat")
    EMBEDDINGS = ("embeddings", "api.infrastructure.fastapi.endpoints.embeddings")
    HEALTH = ("health", "api.infrastructure.fastapi.endpoints.health")
    KEYS = ("keys", "api.infrastructure.fastapi.endpoints.keys")
    ME = ("me", "api.infrastructure.fastapi.endpoints.me")
    MODELS = ("models", "api.infrastructure.fastapi.endpoints.models")
    MONITORING = ("monitoring", "api.infrastructure.fastapi.endpoints.health")
    OCR = ("ocr", "api.infrastructure.fastapi.endpoints.ocr")
    RERANK = ("rerank", "api.infrastructure.fastapi.endpoints.rerank")
    USAGE = ("usage", "api.infrastructure.fastapi.endpoints.usage")

    def __new__(cls, value: str, module_path: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.module_path = module_path

        return obj


class EndpointRoute(StrEnum):
    def __new__(cls, value: str, module_path: str | None = None):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.module_path = module_path

        return obj

    ADMIN_ORGANIZATIONS = f"/{RouterName.ADMIN}/organizations"
    ADMIN_PROVIDERS = f"/{RouterName.ADMIN}/providers"
    ADMIN_ROLES = f"/{RouterName.ADMIN}/roles"
    ADMIN_ROUTERS = f"/{RouterName.ADMIN}/routers"
    ADMIN_KEYS = f"/{RouterName.ADMIN}/keys"
    ADMIN_USERS = f"/{RouterName.ADMIN}/users"
    AUDIO_TRANSCRIPTIONS = f"/{RouterName.AUDIO}/transcriptions"
    AUTH_LOGIN = f"/{RouterName.AUTH}/login"
    AUTH_SSO_LOGIN = f"/{RouterName.AUTH}/sso/login"
    CHAT_COMPLETIONS = f"/{RouterName.CHAT}/completions"
    EMBEDDINGS = f"/{RouterName.EMBEDDINGS}"
    HEALTH = f"/{RouterName.HEALTH}"
    HEALTH_MODELS = f"/{RouterName.HEALTH}/models"
    KEYS = f"/{RouterName.KEYS}"
    METRICS = "/metrics"
    ME = f"/{RouterName.ME}"
    ME_USAGE = f"/{RouterName.ME}/usage"
    MODELS = f"/{RouterName.MODELS}"
    OCR = f"/{RouterName.OCR}"
    RERANK = f"/{RouterName.RERANK}"
    USAGE = f"/{RouterName.USAGE}"


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
