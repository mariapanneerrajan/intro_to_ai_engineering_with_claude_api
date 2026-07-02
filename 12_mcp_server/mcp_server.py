import sys

from mcp.server.fastmcp import FastMCP

# host/port only matter for the HTTP transport; they are harmless for stdio.
mcp = FastMCP("demo", host="127.0.0.1", port=8000)

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city."""
    return f"The weather in {city} is sunny and 22°C."

@mcp.resource("config://app")
def get_config() -> str:
    """Return app configuration."""
    return '{"version": "1.0", "theme": "dark", "language": "en"}'

@mcp.prompt()
def summarize(topic: str) -> str:
    """Generate a summarization prompt for a topic."""
    return f"Please give me a concise 3-sentence summary of: {topic}"

if __name__ == "__main__":
    mcp.run()
