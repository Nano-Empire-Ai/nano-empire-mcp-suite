import asyncio
import os
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

os.environ["TOLLBOOTH_PAPER_MODE"] = "true"

async def run():
    p = StdioServerParameters(
        command='uv',
        args=['run', 'python', 'src/run_server.py'],
        cwd='C:/Users/robla/empire/nano-empire-mcp-suite'
    )
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(
                'sterile_browser_extract', 
                {'url': 'https://defillama.com', 'extract_prompt': 'TVL ranking array'}
            )
            print(res.content[0].text)

if __name__ == '__main__':
    asyncio.run(run())
