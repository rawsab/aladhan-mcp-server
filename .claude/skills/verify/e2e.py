import asyncio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CALLS = [
    ("list_calculation_methods", {}),
    ("convert_gregorian_to_hijri", {"date": "23-11-2026"}),
    ("convert_gregorian_to_hijri", {"date": "2026-11-23"}),
    ("convert_hijri_to_gregorian", {"date": "01-09-1447"}),
    ("get_prayer_times", {"lat": 43.65, "lon": -79.38, "method": 2}),
    ("get_prayer_times_by_city", {"city": "Toronto", "country": "Canada"}),
    ("get_next_prayer", {"lat": 43.65, "lon": -79.38}),
    ("get_qibla", {"lat": 43.65, "lon": -79.38}),
    ("get_hijri_calendar", {"lat": 43.65, "lon": -79.38, "month": 9, "year": 1447}),
    ("get_hijri_calendar_by_city", {"city": "Toronto", "country": "Canada", "month": 9, "year": 1447}),
    ("get_monthly_calendar", {"lat": 43.65, "lon": -79.38, "month": 11, "year": 2026}),
    ("get_monthly_calendar_by_city", {"city": "Toronto", "country": "Canada", "month": 11, "year": 2026}),
]

async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "aladhan_mcp.server"])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name: t for t in (await s.list_tools()).tools}
            print("tools:", sorted(tools))
            for name, args in CALLS:
                if name not in tools:
                    print(f"MISSING {name}"); continue
                try:
                    res = await s.call_tool(name, args)
                    txt = res.content[0].text if res.content else ""
                    print(f"{'ERR ' if res.isError else 'OK  '}{name}: {txt[:160]!r}")
                except Exception as e:
                    print(f"EXC {name}: {e!r}")
asyncio.run(main())
