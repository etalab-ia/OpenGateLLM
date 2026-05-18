from httpx import ConnectError, HTTPStatusError, Response, TimeoutException
import reflex as rx


def httpx_error_toast(exception: Exception, response: Response | None = None) -> rx.toast:
    if type(exception) is TimeoutException:
        message = "Request timeout"
    elif type(exception) is ConnectError:
        message = "Cannot connect to API"
    elif type(exception) is HTTPStatusError:
        try:
            error_data = response.json()
            detail = error_data.get("detail", response.text)

            if isinstance(detail, list):
                messages = []
                for error in detail:
                    if isinstance(error, dict):
                        loc = error.get("loc", [])
                        msg = error.get("msg", "Validation error")
                        loc_str = " > ".join(str(value) for value in loc if value != "body")  # Format location (skip "body" prefix if present)
                        if loc_str:
                            messages.append(f"{loc_str}: {msg}")
                        else:
                            messages.append(msg)
                message = "\n".join(messages) if messages else "Validation error"
            elif isinstance(detail, str):
                message = detail
            else:
                message = str(detail)
        except Exception:
            message = response.text
    else:
        message = type(exception).__name__ + ": " + str(exception)
    return rx.toast.error(message=message, position="bottom-right")
