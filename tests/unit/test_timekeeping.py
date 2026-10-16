"""Tests grouped by their implementation owner."""

from src.utils.timekeeping import current_hour, rpc_weekday


class TestUtils:
    """Test cases cho các hàm tiện ích"""

    def test_helpers(self):
        """Test các hàm helper thời gian"""
        assert len(current_hour()) == 2
        assert rpc_weekday() in [str(i) for i in range(1, 8)]
