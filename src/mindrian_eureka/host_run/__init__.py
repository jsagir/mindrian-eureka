"""Host-side pieces of the pair screen run.

The package holds the request rules, the refusal shape and the staging of a host
bundle as the folder input of the Phase 2 pipeline. It imports no numpy, pydantic
or mcp, so the host tools can load it fast. It makes no model call and no network call.
"""
