from datetime import datetime

log_messages = []


def configure_logger(shared_log_messages) -> None:
    global log_messages
    log_messages = shared_log_messages


def add_log(message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_messages.insert(0, f"{timestamp} - {message}")

    if len(log_messages) > 100:
        log_messages.pop()


def get_logs_as_text() -> str:
    return "\n".join(log_messages)


def get_logs() -> list[str]:
    return list(log_messages)