#!/usr/bin/env python3
"""
wechat_cli 渠道驱动单元测试
"""
import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import channels.drivers.wechat_cli as _wecom_mod

# 测试环境不依赖 requests：通过 patch 标记为可用
_wecom_mod.REQUESTS_AVAILABLE = True

from channels.drivers.wechat_cli import WeChatCliDriver


# ── 工具：一个简单的 HTTP session mock ──────────────────────────────


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class FakeSession:
    """可记录调用 / 返回的 requests.Session 替身"""

    def __init__(self):
        self.calls: list[tuple[str, str, dict | None, float | None]] = []
        self.responses: list[FakeResponse] = []
        self.exceptions: list[Exception] = []

    def queue(self, response: FakeResponse):
        self.responses.append(response)

    def raise_on(self, exc: Exception):
        self.exceptions.append(exc)

    def get(self, url, timeout=None):
        self.calls.append(("GET", url, None, timeout))
        if self.exceptions:
            raise self.exceptions.pop(0)
        if not self.responses:
            raise AssertionError("no fake response queued")
        return self.responses.pop(0)

    def post(self, url, json=None, timeout=None):
        self.calls.append(("POST", url, json, timeout))
        if self.exceptions:
            raise self.exceptions.pop(0)
        if not self.responses:
            raise AssertionError("no fake response queued")
        return self.responses.pop(0)


def make_driver(cfg: dict | None = None) -> WeChatCliDriver:
    base = {"enabled": True, "host": "127.0.0.1", "port": 9999, "timeout": 5}
    base.update(cfg or {})
    drv = WeChatCliDriver(base)
    return drv


# ── 基础能力 ────────────────────────────────────────────────


class TestWeChatCliDriverBasics:
    def test_channel_name(self):
        drv = make_driver()
        assert drv.channel_name == "wechat_cli"

    def test_disabled_not_available(self):
        drv = make_driver({"enabled": False})
        # 即便不注入 session，禁用时也不该访问 RPC
        assert drv.is_available() is False

    def test_is_available_login_success_dict(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, {"success": True, "wxid": "wxid_me"}))
        drv._session = session
        assert drv.is_available() is True

    def test_is_available_login_code_0(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, {"code": 0}))
        drv._session = session
        assert drv.is_available() is True

    def test_is_available_http_error(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(500, text="boom"))
        drv._session = session
        assert drv.is_available() is False

    def test_is_available_network_error(self):
        drv = make_driver()
        session = FakeSession()
        session.raise_on(ConnectionError("rpc down"))
        drv._session = session
        assert drv.is_available() is False


# ── 通讯录缓存 ──────────────────────────────────────────────


class TestFriendCache:
    def _sample_friends(self):
        return [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "Alice", "remark": ""},
            {"wxid": "wxid_b", "phone": "+86 138 0013 8001", "nickname": "Bob", "remark": ""},
        ]

    def test_load_friend_cache_list(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, self._sample_friends()))
        drv._session = session
        count = drv.load_friend_cache(force=True)
        assert count == 2
        assert drv.get_friend_count() == 2

    def test_load_friend_cache_dict_wrapper(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, {"data": self._sample_friends()}))
        drv._session = session
        assert drv.load_friend_cache(force=True) == 2

    def test_load_friend_cache_handles_optional_fields(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, [
            {"userName": "wxid_c", "mobile": "13800138002", "nickName": "Carol", "displayName": ""}
        ]))
        drv._session = session
        drv.load_friend_cache(force=True)
        assert drv.find_wxid_by_phone("13800138002") == "wxid_c"

    def test_find_wxid_by_phone_normalizes(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, self._sample_friends()))
        drv._session = session
        drv.load_friend_cache(force=True)
        # 手机号带 +86 和空格也能命中
        assert drv.find_wxid_by_phone("13800138001") == "wxid_b"

    def test_find_wxid_missing(self):
        drv = make_driver()
        session = FakeSession()
        session.queue(FakeResponse(200, self._sample_friends()))
        drv._session = session
        drv.load_friend_cache(force=True)
        assert drv.find_wxid_by_phone("13900000000") is None

    def test_cache_ttl_does_not_refetch(self):
        drv = make_driver({"phone_cache_ttl_min": 60})
        session = FakeSession()
        session.queue(FakeResponse(200, self._sample_friends()))
        drv._session = session
        drv.load_friend_cache(force=True)
        # 缓存有效，find_wxid_by_phone 不应触发新的 HTTP 调用
        session.calls.clear()
        drv.find_wxid_by_phone("13800138000")
        assert session.calls == []

    def test_cache_expired_triggers_reload(self):
        drv = make_driver({"phone_cache_ttl_min": 60})
        session = FakeSession()
        session.queue(FakeResponse(200, self._sample_friends()))
        session.queue(FakeResponse(200, self._sample_friends()))
        drv._session = session
        drv.load_friend_cache(force=True)
        # 让缓存过期
        drv._cache_loaded_at = datetime.now() - timedelta(minutes=120)
        drv.find_wxid_by_phone("13800138000")
        # 触发了 GET /friends
        assert any(call[0] == "GET" and "/friends" in call[1] for call in session.calls)


# ── 发送行为 ────────────────────────────────────────────────


class TestSend:
    def _boot_cache(self, drv, friends):
        session = FakeSession()
        session.queue(FakeResponse(200, friends))
        drv._session = session
        drv.load_friend_cache(force=True)
        return session

    def test_send_disabled(self):
        drv = make_driver({"enabled": False})
        result = drv.send("13800138000", "hello")
        assert result.success is False
        assert "未启用" in result.error

    def test_send_empty_recipient(self):
        drv = make_driver()
        result = drv.send("", "hello")
        assert result.success is False
        assert "recipient" in result.error

    def test_send_empty_content(self):
        drv = make_driver()
        result = drv.send("13800138000", "")
        assert result.success is False
        assert "content" in result.error

    def test_send_friend_not_found(self):
        drv = make_driver()
        self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        result = drv.send("13900000000", "hi")
        assert result.success is False
        assert "未找到手机号" in result.error

    def test_send_dry_run_does_not_call_rpc(self):
        drv = make_driver({"dry_run": True})
        session = self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        result = drv.send("13800138000", "hello", client_name="张三")
        assert result.success is True
        # 没有任何 POST 调用
        assert all(call[0] != "POST" for call in session.calls)

    def test_send_success_with_msg_id(self):
        drv = make_driver()
        session = self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        session.queue(FakeResponse(200, {"success": True, "msg_id": "abc123"}))
        result = drv.send("13800138000", "hello", client_name="张三")
        assert result.success is True
        assert result.external_id == "abc123"
        # 校验调用了 /send-text 并传了 wxid/msg
        post = [c for c in session.calls if c[0] == "POST"][0]
        assert post[1].endswith("/send-text")
        assert post[2] == {"wxid": "wxid_a", "msg": "hello"}

    def test_send_rpc_returns_failure(self):
        drv = make_driver()
        session = self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        session.queue(FakeResponse(200, {"success": False, "message": "not friend"}))
        result = drv.send("13800138000", "hello")
        assert result.success is False
        assert "not friend" in result.error

    def test_send_http_error(self):
        drv = make_driver()
        session = self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        session.queue(FakeResponse(502, text="bad gateway"))
        result = drv.send("13800138000", "hello")
        assert result.success is False
        assert "502" in result.error

    def test_send_rpc_exception(self):
        drv = make_driver()
        session = self._boot_cache(drv, [
            {"wxid": "wxid_a", "phone": "13800138000", "nickname": "", "remark": ""}
        ])
        session.raise_on(ConnectionError("rpc down"))
        result = drv.send("13800138000", "hello")
        assert result.success is False
        assert "RPC 调用失败" in result.error
