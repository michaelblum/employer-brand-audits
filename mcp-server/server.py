"""Employer-brand-audit MCP server — mechanical image utilities (Plan 1).

Exposes stitch_images / crop_image / make_rendition over stdio. Tools take
explicit file paths; audit/manifest coupling arrives in Plan 2.
"""
import asyncio
import json

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from imaging import stitch_with_overlap, crop_to_rect, make_rendition

app = Server("employer-brand-audit")

_TOOLS = {
    "stitch_images": {
        "description": "Stitch viewport tiles into a full-page image; derives scale from the first tile.",
        "inputSchema": {
            "type": "object",
            "required": ["tiles", "viewport", "output_path"],
            "properties": {
                "tiles": {"type": "array", "items": {
                    "type": "object", "required": ["path", "scroll_top"],
                    "properties": {"path": {"type": "string"},
                                   "scroll_top": {"type": "number"}}}},
                "viewport": {
                    "type": "object",
                    "required": ["inner_width", "inner_height", "client_height"],
                    "properties": {"inner_width": {"type": "number"},
                                   "inner_height": {"type": "number"},
                                   "client_height": {"type": "number"}},
                },
                "output_path": {"type": "string"},
            },
        },
    },
    "crop_image": {
        "description": "Crop an image to a CSS rect (scaled), with optional trim and solid matte.",
        "inputSchema": {
            "type": "object",
            "required": ["source_path", "css_rect", "inner_width", "output_path"],
            "properties": {
                "source_path": {"type": "string"},
                "css_rect": {"type": "object"},
                "inner_width": {"type": "number"},
                "output_path": {"type": "string"},
                "trim": {"type": "object"},
                "matte": {"type": "object"},
            },
        },
    },
    "make_rendition": {
        "description": "Downscale an image to a max long edge as JPEG (analysis/archival rendition).",
        "inputSchema": {
            "type": "object",
            "required": ["source_path", "max_edge", "output_path"],
            "properties": {
                "source_path": {"type": "string"},
                "max_edge": {"type": "number"},
                "output_path": {"type": "string"},
                "quality": {"type": "number"},
            },
        },
    },
}


def list_tool_names():
    return list(_TOOLS.keys())


async def handle_call_tool(name, arguments):
    if name == "stitch_images":
        # returns {"output_path", "scale"}
        return stitch_with_overlap(
            arguments["tiles"], arguments["viewport"], arguments["output_path"],
        )
    if name == "crop_image":
        path = crop_to_rect(
            arguments["source_path"], arguments["css_rect"], arguments["inner_width"],
            arguments["output_path"], arguments.get("trim"), arguments.get("matte"),
        )
        return {"output_path": path}
    if name == "make_rendition":
        path = make_rendition(
            arguments["source_path"], arguments["max_edge"],
            arguments["output_path"], arguments.get("quality", 80),
        )
        return {"output_path": path}
    raise ValueError(f"unknown tool: {name}")


@app.list_tools()
async def _list_tools():
    return [Tool(name=n, description=t["description"], inputSchema=t["inputSchema"])
            for n, t in _TOOLS.items()]


def _serialize(result):
    """Serialize a tool result dict to MCP TextContent (preserves all fields, e.g. stitch's scale)."""
    return [TextContent(type="text", text=json.dumps(result))]


@app.call_tool()
async def _call_tool(name, arguments):
    result = await handle_call_tool(name, arguments)
    return _serialize(result)


async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
