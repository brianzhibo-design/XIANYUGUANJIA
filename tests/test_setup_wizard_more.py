from pathlib import Path

import pytest

import src.setup_wizard as sw


def test_prompt_and_choose(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert sw._prompt("x", default="d") == "d"

    vals = iter(["", "ok"])
    monkeypatch.setattr("builtins.input", lambda _: next(vals))
    assert sw._prompt("x", required=True) == "ok"

    monkeypatch.setattr("getpass.getpass", lambda _: "sec")
    assert sw._prompt("x", secret=True) == "sec"

    vals3 = iter(["0", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(vals3))
    cp = sw._choose_content_provider()
    assert cp.id == sw.CONTENT_PROVIDERS[0].id


def test_env_read(monkeypatch, tmp_path):
    env = tmp_path / ".env"
    env.write_text("A=1\nB=\n", encoding="utf-8")
    out = sw._read_existing_env(env)
    assert out["A"] == "1"
    assert sw._read_existing_env(tmp_path / "none") == {}




def test_run_setup_paths(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(sw, "_choose_content_provider", lambda: sw.CONTENT_PROVIDERS[0])

    def prompt_no_start(text, default=None, required=False, secret=False):
        if "DEEPSEEK_API_KEY" in text:
            return "ck"
        if "XGJ_APP_KEY" in text:
            return "appkey"
        if "XGJ_APP_SECRET" in text:
            return "appsecret"
        if "XGJ_BASE_URL" in text:
            return ""
        if "XIANYU_COOKIE_1" in text:
            return "c1"
        if "XIANYU_COOKIE_2" in text:
            return ""
        if "请选择" in text:
            return "2"  # 稍后手动启动
        return ""

    monkeypatch.setattr(sw, "_prompt", prompt_no_start)
    rc = sw.run_setup()
    assert rc == 0
    assert (tmp_path / ".env").exists()

    # 测试选项 1 本地启动：若 start.sh 不存在，应提示并返回 0
    def prompt_local_start(text, default=None, required=False, secret=False):
        if "请选择" in text:
            return "1"
        return prompt_no_start(text, default, required, secret)

    monkeypatch.setattr(sw, "_prompt", prompt_local_start)
    rc = sw.run_setup()
    assert rc == 0


def test_setup_main_exit(monkeypatch):
    monkeypatch.setattr(sw, "run_setup", lambda: 7)
    with pytest.raises(SystemExit) as e:
        sw.main()
    assert e.value.code == 7


