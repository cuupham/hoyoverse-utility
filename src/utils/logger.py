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
    """Lấy output mode từ LOG_LEVEL; fallback từ config nếu không set hoặc không hợp lệ."""
    from src.config import DEFAULT_LOG_LEVEL

    mode = (os.environ.get("LOG_LEVEL") or DEFAULT_LOG_LEVEL).lower()
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
        """Setup logging với trace_id filter và force flush
        
        Dùng custom handler để đảm bảo mỗi log được flush ngay,
        tránh interleave khi có nhiều async tasks log cùng lúc.
        """
        # Tạo custom handler với force flush
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%d/%m/%Y %H:%M:%S"
        ))
        
        # Override emit để force flush sau mỗi log
        original_emit = handler.emit
        def flush_emit(record):
            original_emit(record)
            handler.flush()
        handler.emit = flush_emit
        
        # Cấu hình root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG if os.environ.get("DEBUG") else logging.INFO)
        root_logger.handlers.clear()  # Xóa default handlers
        root_logger.addHandler(handler)
        root_logger.addFilter(TraceIdFilter(self.trace_id))
    
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
    
    Xử lý multiline: Mỗi dòng được log riêng để có prefix đầy đủ.
    """
    if not message:
        # Empty line
        logger.info("")
        return
    
    # Split by newline và log từng dòng riêng
    # Điều này đảm bảo mỗi dòng có prefix [trace_id][INFO]
    lines = message.split('\n')
    for line in lines:
        logger.info(line)
