"""Tests for message dedup and bargain tracker modules."""

import tempfile
from pathlib import Path

import pytest


class TestMessageDedup:
    def _make(self, tmp_path):
        from src.modules.messages.dedup import MessageDedup
        return MessageDedup(db_path=str(tmp_path / "dedup.db"))

    def test_not_duplicate_initially(self, tmp_path):
        d = self._make(tmp_path)
        assert d.is_duplicate("chat1", 1000, "你好") is False
        assert d.is_content_duplicate("chat1", "你好") is False
        assert d.is_replied("chat1", 1000, "你好") is False

    def test_mark_replied_then_duplicate(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "你好", reply="在的")
        assert d.is_duplicate("chat1", 1000, "你好") is True
        assert d.is_content_duplicate("chat1", "你好") is True
        assert d.is_replied("chat1", 1000, "你好") is True

    def test_different_chat_not_duplicate(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "你好", reply="在的")
        assert d.is_duplicate("chat2", 1000, "你好") is False
        assert d.is_content_duplicate("chat2", "你好") is False

    def test_same_content_different_time_is_content_dup(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "你好", reply="在的")
        assert d.is_duplicate("chat1", 2000, "你好") is False
        assert d.is_content_duplicate("chat1", "你好") is True
        assert d.is_replied("chat1", 2000, "你好") is True

    def test_normalization(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "  你好  世界  ", reply="ok")
        assert d.is_content_duplicate("chat1", "你好 世界") is True

    def test_mark_replied_increments_count(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "你好", reply="v1")
        d.mark_replied("chat1", 2000, "你好", reply="v2")
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "dedup.db"))
        row = conn.execute("SELECT count FROM content_replies LIMIT 1").fetchone()
        conn.close()
        assert row[0] == 2

    def test_cleanup(self, tmp_path):
        d = self._make(tmp_path)
        d.mark_replied("chat1", 1000, "old msg", reply="ok")
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "dedup.db"))
        conn.execute("UPDATE message_replies SET replied_at = datetime('now', '-2 days')")
        conn.execute("UPDATE content_replies SET last_at = datetime('now', '-2 days')")
        conn.commit()
        conn.close()
        removed = d.cleanup(days=1)
        assert removed >= 1
        assert d.is_replied("chat1", 1000, "old msg") is False


class TestBargainTracker:
    def _make(self, tmp_path):
        from src.modules.messages.bargain_tracker import BargainTracker
        return BargainTracker(db_path=str(tmp_path / "bargain.db"))

    def test_initial_count_zero(self, tmp_path):
        t = self._make(tmp_path)
        assert t.get_count("chat1") == 0

    def test_is_bargain_message(self, tmp_path):
        from src.modules.messages.bargain_tracker import BargainTracker
        assert BargainTracker.is_bargain_message("能便宜点吗")
        assert BargainTracker.is_bargain_message("最低多少钱")
        assert not BargainTracker.is_bargain_message("这个怎么用")

    def test_increment(self, tmp_path):
        t = self._make(tmp_path)
        assert t.increment("chat1") == 1
        assert t.increment("chat1") == 2
        assert t.get_count("chat1") == 2

    def test_record_if_bargain(self, tmp_path):
        t = self._make(tmp_path)
        count = t.record_if_bargain("chat1", "能便宜点吗")
        assert count == 1
        count = t.record_if_bargain("chat1", "怎么使用")
        assert count == 1
        count = t.record_if_bargain("chat1", "最低多少")
        assert count == 2

    def test_context_hint(self, tmp_path):
        t = self._make(tmp_path)
        assert t.get_context_hint("chat1") is None
        t.increment("chat1")
        hint = t.get_context_hint("chat1")
        assert hint is not None
        assert "第1次" in hint

    def test_context_hint_escalation(self, tmp_path):
        t = self._make(tmp_path)
        for _ in range(5):
            t.increment("chat1")
        hint = t.get_context_hint("chat1")
        assert "5次" in hint
        assert "底价" in hint

    def test_reset(self, tmp_path):
        t = self._make(tmp_path)
        t.increment("chat1")
        t.increment("chat1")
        t.reset("chat1")
        assert t.get_count("chat1") == 0

    def test_cleanup(self, tmp_path):
        t = self._make(tmp_path)
        t.increment("chat1")
        import sqlite3
        conn = sqlite3.connect(str(tmp_path / "bargain.db"))
        conn.execute("UPDATE bargain_counts SET last_updated = datetime('now', '-2 days')")
        conn.commit()
        conn.close()
        removed = t.cleanup(days=1)
        assert removed >= 1
        assert t.get_count("chat1") == 0


class TestReplyEngineProcessMessage:
    def _make_engine(self):
        from src.modules.messages.reply_engine import ReplyStrategyEngine
        return ReplyStrategyEngine(
            default_reply="默认回复",
            virtual_default_reply="虚拟商品回复",
            dedup_enabled=False,
            bargain_tracking_enabled=False,
        )

    def test_process_message_basic(self, tmp_path):
        from src.modules.messages.reply_engine import ReplyStrategyEngine
        engine = ReplyStrategyEngine(
            default_reply="默认回复",
            virtual_default_reply="虚拟商品回复",
            dedup_enabled=True,
            bargain_tracking_enabled=True,
        )
        engine._dedup = None
        engine._bargain_tracker = None
        try:
            from src.modules.messages.dedup import MessageDedup
            from src.modules.messages.bargain_tracker import BargainTracker
            engine._dedup = MessageDedup(db_path=str(tmp_path / "d.db"))
            engine._bargain_tracker = BargainTracker(db_path=str(tmp_path / "b.db"))
        except Exception:
            pytest.skip("dedup/bargain modules not importable")

        r1 = engine.process_message("chat1", "在吗", 1000)
        assert r1["skipped"] is False
        assert r1["reply"] != ""

        r2 = engine.process_message("chat1", "在吗", 1000)
        assert r2["skipped"] is True
        assert r2["skip_reason"] == "duplicate"

    def test_process_message_bargain_count(self, tmp_path):
        from src.modules.messages.reply_engine import ReplyStrategyEngine
        from src.modules.messages.bargain_tracker import BargainTracker
        engine = ReplyStrategyEngine(
            default_reply="默认回复",
            virtual_default_reply="虚拟商品回复",
            dedup_enabled=False,
            bargain_tracking_enabled=True,
        )
        engine._bargain_tracker = BargainTracker(db_path=str(tmp_path / "b.db"))
        r = engine.process_message("chat1", "能便宜点吗", 1000)
        assert r["bargain_count"] == 1
        assert r["bargain_hint"] is not None
