"""End-to-end tool tests over an in-memory MCP session with mocked Aladhan HTTP."""

import json

import httpx
import pytest
from mcp.server.fastmcp import FastMCP
from mcp.shared.memory import create_connected_server_and_client_session

from aladhan_mcp import utils
from aladhan_mcp.tools.calendars import register_calendar_tools
from aladhan_mcp.tools.date_conversion import register_date_conversion_tools
from aladhan_mcp.tools.prayer_times import register_prayer_times_tools
from aladhan_mcp.tools.qibla import register_qibla_tools

TIMINGS = {"Fajr": "05:58", "Dhuhr": "12:04", "Maghrib": "16:46"}
CALENDAR = [{"timings": TIMINGS, "date": {"readable": "01 Nov 2026"}}]
METHODS = {"ISNA": {"id": 2, "name": "Islamic Society of North America"}}
HIJRI = {"hijri": {"date": "13-06-1448"}, "gregorian": {"date": "23-11-2026"}}

# Path (after /v1) -> response "data". Unknown paths return 404, so a tool
# that builds the wrong URL fails its test.
ROUTES = {
    "/methods": METHODS,
    "/gToH/23-11-2026": HIJRI,
    "/hToG/13-06-1448": HIJRI,
    "/timings/23-11-2026": {"timings": TIMINGS},
    "/timingsByCity/23-11-2026": {"timings": TIMINGS},
    "/nextPrayer/23-11-2026": {"timings": {"Fajr": "05:58"}},
    "/qibla/43.65/-79.38": {"latitude": 43.65, "direction": 54.58},
    "/hijriCalendar/1447/9": CALENDAR,
    "/hijriCalendarByCity/1447/9": CALENDAR,
    "/calendar/2026/11": CALENDAR,
    "/calendarByCity/2026/11": CALENDAR,
}

LAT_LON = {"lat": 43.65, "lon": -79.38}
CITY = {"city": "Toronto", "country": "Canada"}


@pytest.fixture
def aladhan(monkeypatch):
    """Route every httpx.AsyncClient through a mock Aladhan API; yield the requests."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path.removeprefix("/v1")
        if path not in ROUTES:
            return httpx.Response(404, json={"code": 404, "data": "Not found"})
        return httpx.Response(200, json={"code": 200, "data": ROUTES[path]})

    real_client = httpx.AsyncClient

    class MockClient(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    monkeypatch.setattr(utils, "_CACHE", {})
    yield requests


@pytest.fixture
def server():
    server = FastMCP("test-server")
    register_date_conversion_tools(server)
    register_prayer_times_tools(server)
    register_qibla_tools(server)
    register_calendar_tools(server)
    return server


async def call(server, name, args):
    async with create_connected_server_and_client_session(server) as client:
        return await client.call_tool(name, args)


async def test_lists_all_tools(server):
    async with create_connected_server_and_client_session(server) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
    assert tools == {
        "list_calculation_methods",
        "convert_gregorian_to_hijri",
        "convert_hijri_to_gregorian",
        "get_prayer_times",
        "get_prayer_times_by_city",
        "get_next_prayer",
        "get_qibla",
        "get_hijri_calendar",
        "get_hijri_calendar_by_city",
        "get_monthly_calendar",
        "get_monthly_calendar_by_city",
    }


@pytest.mark.parametrize(
    "name, args, expected, expected_params",
    [
        ("list_calculation_methods", {}, METHODS, {}),
        ("convert_gregorian_to_hijri", {"date": "23-11-2026"}, HIJRI, {}),
        ("convert_hijri_to_gregorian", {"date": "13-06-1448"}, HIJRI, {}),
        (
            "get_prayer_times",
            {**LAT_LON, "date": "23-11-2026", "method": 2, "school": 1},
            TIMINGS,
            {"latitude": "43.65", "longitude": "-79.38", "method": "2", "school": "1"},
        ),
        (
            "get_prayer_times_by_city",
            {**CITY, "date": "23-11-2026", "timezone": "America/Toronto"},
            TIMINGS,
            {**CITY, "timezonestring": "America/Toronto"},
        ),
        (
            "get_next_prayer",
            {**LAT_LON, "date": "23-11-2026", "iso8601": True},
            {"timings": {"Fajr": "05:58"}},
            {"latitude": "43.65", "longitude": "-79.38", "iso8601": "true"},
        ),
        ("get_qibla", LAT_LON, {"direction": 54.58}, {}),
        (
            "get_hijri_calendar",
            {**LAT_LON, "year": 1447, "month": 9},
            CALENDAR,
            {"latitude": "43.65", "longitude": "-79.38"},
        ),
        (
            "get_hijri_calendar_by_city",
            {**CITY, "year": 1447, "month": 9, "calendarMethod": "UAQ"},
            CALENDAR,
            {**CITY, "calendarMethod": "UAQ"},
        ),
        (
            "get_monthly_calendar",
            {**LAT_LON, "year": 2026, "month": 11},
            CALENDAR,
            {"latitude": "43.65", "longitude": "-79.38"},
        ),
        (
            "get_monthly_calendar_by_city",
            {**CITY, "year": 2026, "month": 11},
            CALENDAR,
            CITY,
        ),
    ],
)
async def test_tool_call(server, aladhan, name, args, expected, expected_params):
    result = await call(server, name, args)

    assert not result.isError, result.content[0].text
    assert json.loads(result.content[0].text) == expected
    assert len(aladhan) == 1
    assert dict(aladhan[0].url.params) == expected_params


async def test_calculation_methods_are_cached(server, aladhan):
    await call(server, "list_calculation_methods", {})
    await call(server, "list_calculation_methods", {})
    assert len(aladhan) == 1


@pytest.mark.parametrize(
    "name, args, message",
    [
        ("get_prayer_times", {**LAT_LON, "school": 2}, "school must be 0"),
        ("get_next_prayer", {**LAT_LON, "school": 2}, "school must be 0"),
        ("get_prayer_times_by_city", {"city": " ", "country": "CA"}, "required"),
        (
            "get_hijri_calendar_by_city",
            {**CITY, "year": 1447, "month": 9, "calendarMethod": "BAD"},
            "calendarMethod must be",
        ),
        ("convert_gregorian_to_hijri", {"date": ""}, "DD-MM-YYYY"),
    ],
)
async def test_invalid_args_return_error(server, aladhan, name, args, message):
    result = await call(server, name, args)

    assert result.isError
    assert message in result.content[0].text
    assert aladhan == []


async def test_http_error_returns_error(server, aladhan):
    result = await call(server, "convert_gregorian_to_hijri", {"date": "2026-11-23"})

    assert result.isError
    assert "404" in result.content[0].text
