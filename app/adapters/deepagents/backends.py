"""Backend builders — convert BackendConfig to DeepAgents backend instances."""

from __future__ import annotations

from typing import Any

from app.adapters.types import BackendConfig

__all__ = ["build_backend"]


def build_backend(config: BackendConfig) -> Any:
    """Build a DeepAgents backend from config.

    - 'state': Ephemeral in-memory backend (default)
    - 'filesystem': Persistent file-based backend scoped to root_dir
    """
    from deepagents.backends import FilesystemBackend, StateBackend

    if config.type == "filesystem":
        if not config.root_dir:
            raise ValueError("FilesystemBackend requires root_dir to be set")
        return FilesystemBackend(
            root_dir=config.root_dir,
            max_file_size_mb=config.max_file_size_mb,
        )

    return StateBackend()
