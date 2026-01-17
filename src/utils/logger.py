"""Logger utilities - Structured logging với trace_id"""
import json
import logging
import os
import uuid
from datetime import datetime
from enum import Enum


# ==================== OUTPUT MODE ====================
class OutputMode(Enum):
    HUMAN = "human"
    JSON = "json"
    BOTH = "both"


def get_output_mode() -> OutputMode:
    """Get output mode với fallback an toàn"""
    mode = os.environ.get("LOG_LEVEL", "human").lower()
    try:
        return OutputMode(mode)
    except ValueError:
        return OutputMode.HUMAN


OUTPUT_MODE = get_output_mode()


# ==================== TRACE ID FILTER ====================
class TraceIdFilter(logging.Filter):
    """Filter thêm trace_id vào mỗi log record"""
    def __init__(self, trace_id: str):
        super().__init__()
        self.trace_id = trace_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = self.trace_id
        return True


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
        """Setup logging với trace_id filter"""
        logging.basicConfig(
            level=logging.DEBUG if os.environ.get("DEBUG") else logging.INFO,
            format="%(asctime)s [%(trace_id)s][%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        logging.getLogger().addFilter(TraceIdFilter(self.trace_id))
    
    @property
    def elapsed_seconds(self) -> float:
        """Thời gian đã chạy (giây)"""
        return (datetime.now() - self.start_time).total_seconds()


# ==================== GLOBAL INSTANCES ====================
ctx = ExecutionContext()
logger = logging.getLogger()  # Root logger - đã có TraceIdFilter


# ==================== LOG FUNCTIONS ====================
def log_info(account: str, message: str) -> None:
    """Log level INFO"""
    logger.info(f"[{account}] {message}")


def log_error(account: str, message: str) -> None:
    """Log level ERROR"""
    logger.error(f"[{account}] {message}")


def log_warning(account: str, message: str) -> None:
    """Log level WARNING"""
    logger.warning(f"[{account}] {message}")


def log_debug(account: str, message: str) -> None:
    """Log level DEBUG"""
    logger.debug(f"[{account}] {message}")


def log_result(data: dict, human_msg: str) -> None:
    """Output theo OUTPUT_MODE setting"""
    if OUTPUT_MODE in (OutputMode.HUMAN, OutputMode.BOTH):
        logger.info(human_msg)
    
    if OUTPUT_MODE in (OutputMode.JSON, OutputMode.BOTH):
        print(json.dumps({
            **data,
            "trace_id": ctx.trace_id,
            "timestamp": datetime.now().isoformat(),
        }), flush=True)


def log_print(message: str = "") -> None:
    """Thay thế print() để đảm bảo output ordering nhất quán
    
    Trong CI environments (GitHub Actions), stdout/stderr có thể bị 
    buffer khác nhau. Dùng logger.info thay vì print để đảm bảo
    thứ tự output đúng.
    """
    if message:
        # Dùng empty prefix để không có [account] format
        logger.info(message)
    else:
        # Empty line - vẫn dùng logger để giữ ordering
        logger.info("")
