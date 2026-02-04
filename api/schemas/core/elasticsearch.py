from datetime import datetime
from enum import Enum

from pydantic import Field

from api.schemas.documents import InputChunkMetadata


class ElasticsearchIndexLanguage(str, Enum):
    """
    The language of the Elasticsearch index, composed by the value, the stopwords and the stemmer.
    For more information about stemmer, see https://www.elastic.co/docs/reference/text-analysis/analysis-stemmer-tokenfilter#analysis-stemmer-tokenfilter-configure-parms.
    """

    ENGLISH = ("english", "_english_", "light_english")
    FRENCH = ("french", "_french_", "light_french")
    GERMAN = ("german", "_german_", "light_german")
    ITALIAN = ("italian", "_italian_", "light_italian")
    PORTUGUESE = ("portuguese", "_portuguese_", "light_portuguese")
    SPANISH = ("spanish", "_spanish_", "light_spanish")
    SWEDISH = ("swedish", "_swedish_", "light_swedish")

    def __new__(cls, value, stopwords, stemmer):
        if not isinstance(value, str):
            raise TypeError(f"Enum values must be strings (got {type(value).__name__})")
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.stopwords = stopwords
        obj.stemmer = stemmer

        return obj


class ElasticsearchChunkFields(InputChunkMetadata):
    id: int = Field(default=..., description="The ID of the chunk.")  # fmt: off
    collection_id: int = Field(default=..., description="The ID of the collection the chunk belongs to.")  # fmt: off
    document_id: int = Field(default=..., description="The ID of the document the chunk belongs to.")  # fmt: off
    document_name: str = Field(default=..., description="The name of the document the chunk belongs to.")  # fmt: off
    embedding: list[float] = Field(default=[], description="The embedding of the chunk.")  # fmt: off
    content: str = Field(default=..., description="The content of the chunk.")  # fmt: off
    created: datetime = Field(default=..., description="The date of the chunk creation.")  # fmt: off
