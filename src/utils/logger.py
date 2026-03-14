"""Logger utilities - Structured logging với trace_id"""

import logging
import os
import uuid
from datetime import datetime

# Named logger — không can thiệp root logger, tránh conflict với test/library
_LOGGER_NAME = "hoyolab"


# ==================== TRACE ID FILTER ====================
class TraceIdFilter(logging.Filter):
    """Filter thêm trace_id vào mỗi log record"""

    def __init__(self, trace_id: str):
        super().__init__()
        self.trace_id = trace_id

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = self.trace_id
        return True


class ForceFlushStreamHandler(logging.StreamHandler):
    """Handler tự động flush buffer sau mỗi dòng log (Tốt cho CI/CD)"""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


# ==================== EXECUTION CONTEXT ====================
class ExecutionContext:
    """Singleton chứa context cho 1 lần chạy"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.trace_id = uuid.uuid4().hex[:8]
            cls._instance.start_time = datetime.now()
            cls._instance._setup_logging()
        return cls._instance

    def _setup_logging(self) -> None:
        """Setup named logger với trace_id filter và force flush.

        Dùng named logger 'hoyolab' thay vì root logger để:
        - Tránh conflict với third-party libraries
        - Không clear handlers của test frameworks
        - Isolation tốt hơn khi testing
        """
        log_level = logging.DEBUG if os.environ.get("DEBUG") else logging.INFO

        handler = ForceFlushStreamHandler()
        handler.setLevel(log_level)
        handler.setFormatter(
            logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(message)s", datefmt="%d/%m/%Y %H:%M:%S")
        )

        named_logger = logging.getLogger(_LOGGER_NAME)
        named_logger.setLevel(log_level)
        named_logger.handlers.clear()
        named_logger.addHandler(handler)
        named_logger.addFilter(TraceIdFilter(self.trace_id))
        # Prevent propagation to root logger (avoid duplicate logs)
        named_logger.propagate = False

    def reset_timer(self) -> None:
        """Reset start_time về thời điểm hiện tại — gọi khi main() bắt đầu."""
        self.start_time = datetime.now()

    @property
    def elapsed_seconds(self) -> float:
        """Thời gian đã chạy (giây)"""
        return (datetime.now() - self.start_time).total_seconds()


# ==================== GLOBAL INSTANCES ====================
ctx = ExecutionContext()
logger = logging.getLogger(_LOGGER_NAME)


# ==================== LOG FUNCTIONS ====================
def log_info(account: str, message: str) -> None:
    """Log level INFO với prefix account"""
    logger.info(f"[{account}] {message}")


def log_error(account: str, message: str) -> None:
    """Log level ERROR với prefix account"""
    logger.error(f"[{account}] {message}")


def log_print(message: str = "") -> None:
    """Thay thế print() để đảm bảo output ordering nhất quán.

    Trong CI environments (GitHub Actions), stdout/stderr có thể bị
    buffer khác nhau. Dùng logger.info thay vì print để đảm bảo
    thứ tự output đúng. Multiline: mỗi dòng được log riêng.
    """
    if not message:
        logger.info("")
        return

    for line in message.split("\n"):
        logger.info(line)
