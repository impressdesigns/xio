"""Settings. Each one is overridden by an environment variable of the same name prefixed ``XIO_``."""

from pydantic_settings import BaseSettings


class _Config(BaseSettings, env_prefix="xio_", extra="ignore", frozen=True):
    """Xio's settings, read from the environment only: never from a ``.env`` file."""

    tenant: str = "0bfaee50-a856-4466-8122-c331879d0dba"
    default_service: str = "core"
    timeout_seconds: float = 60

    core_url: str = "https://core.impressdesigns.com"
    core_scope: str = "https://core.impressdesigns.com/.default"
    graph_url: str = "https://graph.microsoft.com"
    graph_scope: str = "https://graph.microsoft.com/.default"


Config = _Config()
