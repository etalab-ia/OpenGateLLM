from httpx import ConnectError, HTTPStatusError, Response, TimeoutException
import reflex as rx


def httpx_error_toast(exception: Exception, response: Response | None = None) -> rx.toast:
    if type(exception) is TimeoutException:
        message = "Request timeout"
    elif type(exception) is ConnectError:
        message = "Cannot connect to API"
    elif type(exception) is HTTPStatusError:
        try:
            message = response.json().get("detail", response.text)
        except Exception:
            message = response.text
    else:
        message = str(exception)
    return rx.toast.error(message=message, position="bottom-right")
