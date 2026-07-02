"""
MCP Server demo — with the MCP client living *inside your app*.

This is the runnable-script version of 12_mcp_server.ipynb. It demonstrates the
pattern where YOUR application hosts the MCP client and connects to a local MCP
server over stdio (launched as a subprocess), rather than using Anthropic's
cloud MCP connector.

Why a script instead of the notebook?
-------------------------------------
Launching an MCP stdio server means spawning a subprocess. On Windows, asyncio
can only spawn subprocesses on the *Proactor* event loop, but Jupyter/ipykernel
runs on the *Selector* loop -- so the notebook raises NotImplementedError, then
trips again on ipykernel's fake stderr (UnsupportedOperation: fileno).

As a standalone script we control the event loop, so we simply select the
Proactor loop on Windows (see `main()` at the bottom) and both problems vanish.

Flow recap
----------
    your app  ── tool schemas ─────────────▶  Claude API
       │  ▲                                       │
       │  └──────── "call get_weather(...)" ──────┘   (tool_use request)
       ▼  your MCP CLIENT makes the call
    mcp_server.py (local subprocess) ── result ──▶ back to Claude as tool_result

Claude never touches the MCP server. Your app is the bridge: it sends the tool
schemas to Claude, and when Claude issues a `tool_use` request, YOUR code
executes it against the local server and returns the `tool_result`.

Prerequisites
-------------
    - ANTHROPIC_API_KEY in a .env file (in this folder or a parent)
    - pip install "anthropic[mcp]" python-dotenv mcp
    - mcp_server.py present in this same folder (the notebook's %%writefile cell
      creates it; it is already here).

Run
---
    python mcp_client_app.py
"""

import asyncio
import sys

from dotenv import load_dotenv
from anthropic import AsyncAnthropic

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


# --------------------------------------------------------------------------- #
# Setup
# --------------------------------------------------------------------------- #
# We use the ASYNC Anthropic client because MCP sessions are async.
load_dotenv()
client = AsyncAnthropic()
model = "claude-haiku-4-5"

# How to launch the server: run `python mcp_server.py` using the SAME Python
# interpreter as this script (sys.executable), so the subprocess sees the same
# installed packages. This is just a recipe -- the process starts when
# stdio_client() actually opens it.
server_params = StdioServerParameters(command=sys.executable, args=["mcp_server.py"])


# --------------------------------------------------------------------------- #
# The in-app bridge: this one helper is the whole pattern
# --------------------------------------------------------------------------- #
async def run_with_mcp(session: ClientSession, user_message: str, verbose: bool = True) -> str:
    """Bridge a local MCP session into a Claude tool-use loop, in-process.

    Given an already-initialized MCP `session`, this:
      1. Lists the server's tools and converts them to Claude's schema -- this
         is exactly what gets sent across to Claude.
      2. Runs the tool-use loop: Claude requests a tool, OUR app calls it on the
         MCP server via `session.call_tool(...)`, and we return the result.
    """
    # 1) Discover the server's tools and translate to Claude's schema.
    #    These schemas are what we send across to Claude.
    mcp_tools = (await session.list_tools()).tools
    tools = [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in mcp_tools
    ]

    messages = [{"role": "user", "content": user_message}]

    while True:
        response = await client.messages.create(
            model=model, max_tokens=512, tools=tools, messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        # Claude is done thinking / answering.
        if response.stop_reason != "tool_use":
            break

        # 2) Claude asked for one or more tools. OUR app executes each call
        #    against the MCP server and hands the results back.
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if verbose:
                    print(f"  [app] Claude requested {block.name}({block.input}) -> calling MCP server")
                result = await session.call_tool(block.name, block.input)
                text = "".join(p.text for p in result.content if p.type == "text")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": text,
                })
        messages.append({"role": "user", "content": tool_results})

    return "".join(b.text for b in response.content if b.type == "text")


# --------------------------------------------------------------------------- #
# Step 1: Inspect the tool schemas our app will send to Claude
# --------------------------------------------------------------------------- #
async def show_tool_schemas() -> None:
    """Launch the server over stdio and print the tool schemas it exposes.

    `stdio_client(server_params)` is where the server subprocess actually
    starts; it hands us (read, write) pipes. `ClientSession` speaks the MCP
    protocol over those pipes, and `initialize()` performs the handshake.
    """
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            print("Tool schemas our app will send to Claude:\n")
            for t in tools:
                print(f"- {t.name}: {t.description}")
                print(f"    input_schema: {t.inputSchema}\n")


# --------------------------------------------------------------------------- #
# Step 2: Run a real request through the bridge
# --------------------------------------------------------------------------- #
async def run_weather_request() -> None:
    """Ask Claude a question that requires the get_weather tool.

    Watch the `[app]` line in the output -- that is OUR code making the tool
    call against the local server, not Claude.
    """
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            answer = await run_with_mcp(session, "What's the weather in Tokyo?")
            print("\nClaude:", answer)


# --------------------------------------------------------------------------- #
# Bonus: Resources & Prompts (pulled by your app, not driven by Claude)
# --------------------------------------------------------------------------- #
async def get_resource(session: ClientSession) -> str:
    """Read a RESOURCE from the MCP server and return its text.

    A RESOURCE is data your app reads directly and decides how to use --
    Claude does NOT drive this.
    """
    config = await session.read_resource("config://app")
    return config.contents[0].text


async def get_prompt(session: ClientSession) -> list[dict]:
    """Fetch a PROMPT template from the MCP server and return it as Claude messages.

    A PROMPT is a template your app fetches and fills in; here we ask the
    server's "summarize" prompt for the topic "climate change". Sending the
    filled messages to Claude is the caller's job -- Claude does NOT drive this.
    """
    prompt = await session.get_prompt("summarize", {"topic": "climate change"})
    return [{"role": m.role, "content": m.content.text} for m in prompt.messages]


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
async def main() -> None:
    # print("=" * 70)
    # print("Step 1: Tool schemas")
    # print("=" * 70)
    # await show_tool_schemas()

    print("=" * 70)
    print("Step 2: Weather request through the bridge")
    print("=" * 70)
    await run_weather_request()

    print("\n" + "=" * 70)
    print("Bonus: Resources & Prompts")
    print("=" * 70)
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # RESOURCE: our app reads it directly.
            config = await get_resource(session)
            print("Resource config://app ->", config)

            # PROMPT: our app fetches the filled template, then WE send it to Claude.
            messages = await get_prompt(session)
            response = await client.messages.create(model=model, max_tokens=256, messages=messages)
            print("\nSummary:", "".join(b.text for b in response.content if b.type == "text"))


if __name__ == "__main__":
    # On Windows, asyncio can only spawn subprocesses on the Proactor event
    # loop. Selecting it here is what lets stdio_client launch mcp_server.py --
    # this is precisely the step Jupyter cannot do, which is why the notebook
    # version raised NotImplementedError / UnsupportedOperation: fileno.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(main())
