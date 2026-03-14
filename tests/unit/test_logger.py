"""Tests cho logger.py - Structured logging, trace_id, multiline, elapsed"""

import logging
import time
from unittest.mock import patch

from src.utils.logger import (
    ExecutionContext,
    ForceFlushStreamHandler,
    TraceIdFilter,
    ctx,
    log_error,
    log_info,
    log_print,
)


class TestTraceIdFilter:
    def test_adds_trace_id_to_record(self):
        """Filter phải thêm trace_id vào log record"""
        f = TraceIdFilter("abc12345")
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        assert f.filter(record) is True
        assert record.trace_id == "abc12345"


class TestForceFlushStreamHandler:
    def test_flush_called_after_emit(self):
        """Handler phải flush sau mỗi emit (có thể nhiều lần do super().emit cũng flush)"""
        handler = ForceFlushStreamHandler()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        with patch.object(handler, "flush") as mock_flush:
            handler.emit(record)
            assert mock_flush.call_count >= 1


class TestExecutionContext:
    def test_singleton_pattern(self):
        """Chỉ 1 instance duy nhất"""
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        assert ctx1 is ctx2

    def test_has_trace_id(self):
        """trace_id phải là 8 hex chars"""
        assert len(ctx.trace_id) == 8
        assert all(c in "0123456789abcdef" for c in ctx.trace_id)

    def test_elapsed_seconds(self):
        """elapsed_seconds tăng theo thời gian"""
        t1 = ctx.elapsed_seconds
        time.sleep(0.05)
        t2 = ctx.elapsed_seconds
        assert t2 > t1

    def test_reset_timer(self):
        """reset_timer() resets start_time, elapsed_seconds giảm về ~0"""
        time.sleep(0.05)
        before_reset = ctx.elapsed_seconds
        ctx.reset_timer()
        after_reset = ctx.elapsed_seconds
        assert after_reset < before_reset
        assert after_reset < 0.1

    def test_uses_named_logger(self):
        """Logger phải dùng named logger 'hoyolab', không phải root"""
        named_logger = logging.getLogger("hoyolab")
        assert named_logger.propagate is False
        assert len(named_logger.handlers) >= 1
        assert isinstance(named_logger.handlers[0], ForceFlushStreamHandler)


class TestLogFunctions:
    def test_log_info_format(self):
        """log_info format: [account] message"""
        with patch("src.utils.logger.logger") as mock_logger:
            log_info("ACC_1", "test message")
            mock_logger.info.assert_called_once_with("[ACC_1] test message")

    def test_log_error_format(self):
        """log_error format: [account] message"""
        with patch("src.utils.logger.logger") as mock_logger:
            log_error("ACC_2", "error occurred")
            mock_logger.error.assert_called_once_with("[ACC_2] error occurred")

    def test_log_print_empty(self):
        """log_print('') gọi logger.info với empty string"""
        with patch("src.utils.logger.logger") as mock_logger:
            log_print()
            mock_logger.info.assert_called_once_with("")

    def test_log_print_single_line(self):
        """log_print single line"""
        with patch("src.utils.logger.logger") as mock_logger:
            log_print("hello world")
            mock_logger.info.assert_called_once_with("hello world")

    def test_log_print_multiline_splits(self):
        """log_print multiline → mỗi dòng log riêng"""
        with patch("src.utils.logger.logger") as mock_logger:
            log_print("line1\nline2\nline3")
            assert mock_logger.info.call_count == 3
            calls = [c[0][0] for c in mock_logger.info.call_args_list]
            assert calls == ["line1", "line2", "line3"]
