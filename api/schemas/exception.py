from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, conint


class HTTPExceptionModel(BaseModel):
    status_code: conint(ge=100, le=599) = Field(description="HTTP status code to send to the client.")
    detail: Any = Field(description="Any data to be sent to the client in the `detail` key of the JSON response.")
    headers: Optional[Dict[str, str]] = Field(description="Any headers to send to the client in the response.")
