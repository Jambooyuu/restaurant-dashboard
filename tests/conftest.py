"""pytest 配置：确保后端服务可用"""
import pytest
import httpx


@pytest.fixture(scope="session", autouse=True)
def check_server():
    """在运行测试前检查后端是否启动"""
    try:
        resp = httpx.get("http://localhost:8000/", timeout=5)
        assert resp.status_code == 200
    except Exception as e:
        pytest.skip(f"后端服务未启动，请先执行: python -m uvicorn backend.app:app --port 8000\n错误: {e}")
