import os

# Set required keys before any app module is imported so pydantic-settings
# validation passes at import time.
os.environ.setdefault("LUMAAI_API_KEY", "test-luma-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
