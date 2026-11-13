"""Martin's signup tools: read-only, answered from desk_data.json (see desk_core.py)."""
from .desk_core import GET_ORG_SCHEMA, LIST_PENDING_SCHEMA, get_org, list_pending_orgs

TOOLSET = "desk_signups"
_TOOLS = [(list_pending_orgs, LIST_PENDING_SCHEMA), (get_org, GET_ORG_SCHEMA)]


def register(ctx):
    for handler, schema in _TOOLS:
        ctx.register_tool(name=schema["name"], toolset=TOOLSET, schema=schema, handler=handler, emoji="🛂")
