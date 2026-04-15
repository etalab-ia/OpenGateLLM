from httpx import ConnectError, HTTPStatusError, Response, TimeoutException
import reflex as rx


def _format_field_name(loc: list) -> str:
    parts = [str(value) for value in loc if value != "body"]
    if not parts:
        return "Field"
    return parts[-1].replace("_", " ").capitalize()


def _format_validation_error(error: dict) -> tuple[str, str]:
    field = _format_field_name(error.get("loc", []))
    msg = error.get("msg", "Validation error")
    if msg.startswith("Value error, "):
        msg = msg[len("Value error, ") :]
    return field, msg


def httpx_error_toast(exception: Exception, response: Response | None = None) -> list:
    if type(exception) is TimeoutException:
        return [rx.toast.error("Request timeout", position="bottom-right")]
    if type(exception) is ConnectError:
        return [rx.toast.error("Cannot connect to API", position="bottom-right")]
    if type(exception) is HTTPStatusError:
        try:
            error_data = response.json()
            detail = error_data.get("detail", response.text)

            if isinstance(detail, list):  # 422 validation errors enter this statement
                toasts = []
                for error in detail:
                    if isinstance(error, dict):
                        field, msg = _format_validation_error(error)
                        toasts.append(rx.toast.error(f"{field}: {msg}", position="bottom-right"))
                    else:
                        toasts.append(rx.toast.error(str(error), position="bottom-right"))
                return toasts if toasts else [rx.toast.error("Validation error", position="bottom-right")]
            if isinstance(detail, str):
                return [rx.toast.error(detail, position="bottom-right")]
            return [rx.toast.error(str(detail), position="bottom-right")]
        except Exception:
            return [rx.toast.error(response.text, position="bottom-right")]
    return [rx.toast.error(f"{type(exception).__name__}: {exception}", position="bottom-right")]
