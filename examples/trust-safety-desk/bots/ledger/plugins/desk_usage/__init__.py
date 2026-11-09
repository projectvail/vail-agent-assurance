"""Ledger's usage tools: read-only, answered from desk_data.json (see desk_core.py)."""
from .desk_core import GET_ORG_SCHEMA, GET_USAGE_SCHEMA, get_org, get_usage

TOOLSET = "desk_usage"
_TOOLS = [(get_usage, GET_USAGE_SCHEMA), (get_org, GET_ORG_SCHEMA)]


def register(ctx):
    for handler, schema in _TOOLS:
        ctx.register_tool(name=schema["name"], toolset=TOOLSET, schema=schema, handler=handler, emoji="📊")
