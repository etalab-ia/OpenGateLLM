from enum import Enum


class IndexLanguage(str, Enum):
    DUTCH = ("dutch", "_dutch_", "dutch")
    ENGLISH = ("english", "_english_", "english")
    FRENCH = ("french", "_french_", "french")
    GERMAN = ("german", "_german_", "german")
    ITALIAN = ("italian", "_italian_", "italian")
    PORTUGUESE = ("portuguese", "_portuguese_", "portuguese")
    SPANISH = ("spanish", "_spanish_", "spanish")
    SWEDISH = ("swedish", "_swedish_", "swedish")

    def __new__(cls, value, stopwords, stemmer):
        if not isinstance(value, str):
            raise TypeError(f"Enum values must be strings (got {type(value).__name__})")
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.stopwords = stopwords
        obj.stemmer = stemmer

        return obj
