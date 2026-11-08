"""Herald's email tools, answered from desk_data.json; send_email only writes to a local outbox."""
from .desk_core import (DRAFT_SCHEMA, GET_ORG_SCHEMA, OUTBOX_SCHEMA, SEND_SCHEMA, draft_email, get_org,
                        list_outbox, send_email)

TOOLSET = "desk_mail"
_TOOLS = [(get_org, GET_ORG_SCHEMA), (draft_email, DRAFT_SCHEMA), (send_email, SEND_SCHEMA),
          (list_outbox, OUTBOX_SCHEMA)]


def register(ctx):
    for handler, schema in _TOOLS:
        ctx.register_tool(name=schema["name"], toolset=TOOLSET, schema=schema, handler=handler, emoji="✉️")
