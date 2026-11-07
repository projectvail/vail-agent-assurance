"""VAIL Assurance panel: the agent half registers nothing.

Everything this plugin does is in its Desktop page (desktop/plugin.js) and the backend routes that
page calls (dashboard/plugin_api.py). Hermes requires a register() for a native plugin package.
"""


def register(ctx):  # noqa: ARG001 - required entry point, intentionally empty
    return None
