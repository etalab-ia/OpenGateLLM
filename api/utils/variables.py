DEFAULT_APP_NAME = "OpenGateLLM"
DEFAULT_TIMEOUT = 300

PREFIX__REDIS_METRIC_GAUGE = "ogl_mg"
PREFIX__REDIS_METRIC_TIMESERIE = "ogl_ts"
PREFIX__REDIS_RATE_LIMIT = "ogl_rt"
REDIS__TIMESERIE_RETENTION_SECONDS = 120

ENDPOINT__ADMIN_ORGANIZATIONS = "/admin/organizations"
ENDPOINT__ADMIN_PROVIDERS = "/admin/providers"
ENDPOINT__ADMIN_ROLES = "/admin/roles"
ENDPOINT__ADMIN_ROUTERS = "/admin/routers"
ENDPOINT__ADMIN_TOKENS = "/admin/tokens"
ENDPOINT__ADMIN_USERS = "/admin/users"
ENDPOINT__AUDIO_TRANSCRIPTIONS = "/audio/transcriptions"
ENDPOINT__AUTH_CALLBACK = "/auth/callback"
ENDPOINT__AUTH_LOGIN = "/auth/login"
ENDPOINT__AUTH_LOGOUT = "/auth/logout"
ENDPOINT__CHAT_COMPLETIONS = "/chat/completions"
ENDPOINT__CHUNKS = "/chunks"
ENDPOINT__COLLECTIONS = "/collections"
ENDPOINT__DOCUMENTS = "/documents"
ENDPOINT__EMBEDDINGS = "/embeddings"
ENDPOINT__FILES = "/files"
ENDPOINT__ME_KEYS = "/me/keys"
ENDPOINT__ME_INFO = "/me/info"
ENDPOINT__MODELS = "/models"
ENDPOINT__MODELS_ALIAS = "/models/alias"
ENDPOINT__OCR = "/ocr-beta"
ENDPOINT__PARSE = "/parse-beta"
ENDPOINT__RERANK = "/rerank"
ENDPOINT__SEARCH = "/search"
ENDPOINT__USAGE = "/usage"

ENDPOINTS = [value for name, value in locals().items() if name.startswith("ENDPOINT__")]


ROUTER__ADMIN = "admin"
ROUTER__AUDIO = "audio"
ROUTER__AUTH = "auth"
ROUTER__CHAT = "chat"
ROUTER__CHUNKS = "chunks"
ROUTER__COLLECTIONS = "collections"
ROUTER__DOCUMENTS = "documents"
ROUTER__EMBEDDINGS = "embeddings"
ROUTER__FILES = "files"
ROUTER__MODELS = "models"
ROUTER__MONITORING = "monitoring"
ROUTER__OCR = "ocr"
ROUTER__PARSE = "parse"
ROUTER__RERANK = "rerank"
ROUTER__SEARCH = "search"
ROUTER__USAGE = "usage"
ROUTER__ME = "me"

ROUTERS = [value for name, value in locals().items() if name.startswith("ROUTER__")]

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
