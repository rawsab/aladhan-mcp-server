import httpx
import pytest

from aladhan_mcp import utils
from aladhan_mcp.utils import (
    ALADHAN_BASE,
    cache_get,
    cache_put,
    get_json,
    text_content,
    text_json,
)


class TestUtils:
    def test_text_json(self):
        """Test text_json function returns TextContent with JSON string"""
        data = {"test": "data"}
        result = text_json(data)
        assert result.type == "text"
        assert result.text == '{"test": "data"}'

    def test_text_content(self):
        """Test text_content function returns TextContent"""
        text = "test string"
        result = text_content(text)
        assert result.type == "text"
        assert result.text == text

    def test_cache_operations(self):
        """Test cache get and put operations"""
        # Test cache put
        cache_put("test_key", {"test": "data"})

        # Test cache get
        result = cache_get("test_key")
        assert result == {"test": "data"}

        # Test cache get with non-existent key
        result = cache_get("non_existent")
        assert result is None

    @pytest.fixture
    def mock_http(self, monkeypatch):
        """Serve queued responses to every httpx.AsyncClient; yield (requests, queue)."""
        requests: list[httpx.Request] = []
        responses: list[httpx.Response] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return responses.pop(0)

        real_client = httpx.AsyncClient

        class MockClient(real_client):
            def __init__(self, *args, **kwargs):
                kwargs["transport"] = httpx.MockTransport(handler)
                super().__init__(*args, **kwargs)

        async def no_sleep(_):
            pass

        monkeypatch.setattr(httpx, "AsyncClient", MockClient)
        monkeypatch.setattr(utils.asyncio, "sleep", no_sleep)
        yield requests, responses

    async def test_get_json_success(self, mock_http):
        """Test get_json returns the decoded JSON body"""
        requests, responses = mock_http
        responses.append(httpx.Response(200, json={"data": "ok"}))

        assert await get_json(f"{ALADHAN_BASE}/methods") == {"data": "ok"}
        assert len(requests) == 1

    async def test_get_json_with_params(self, mock_http):
        """Test get_json sends query parameters"""
        requests, responses = mock_http
        responses.append(httpx.Response(200, json={}))

        await get_json(f"{ALADHAN_BASE}/timings", params={"method": 2})
        assert requests[0].url.params["method"] == "2"

    async def test_get_json_retries_then_succeeds(self, mock_http):
        """Test get_json retries transient HTTP errors"""
        requests, responses = mock_http
        responses.extend(
            [httpx.Response(500), httpx.Response(503), httpx.Response(200, json={})]
        )

        assert await get_json(f"{ALADHAN_BASE}/methods") == {}
        assert len(requests) == 3

    async def test_get_json_raises_after_three_failures(self, mock_http):
        """Test get_json gives up after three attempts"""
        requests, responses = mock_http
        responses.extend([httpx.Response(500)] * 3)

        with pytest.raises(httpx.HTTPStatusError):
            await get_json(f"{ALADHAN_BASE}/methods")
        assert len(requests) == 3

    def test_aladhan_base_constant(self):
        """Test ALADHAN_BASE constant"""
        assert ALADHAN_BASE == "https://api.aladhan.com/v1"
