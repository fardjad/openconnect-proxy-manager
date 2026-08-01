"""Configuration from environment variables."""
import os
import sys
from dataclasses import dataclass


@dataclass
class Config:
    user: str
    password: str
    url: str
    options: str
    heartbeat_url: str
    heartbeat_interval: int
    has_creds: bool
    auto_connect: bool

    @classmethod
    def from_env(cls) -> "Config":
        errors = []

        url = os.environ.get("OPENCONNECT_URL", "")
        if not url:
            errors.append("OPENCONNECT_URL is required")

        user = os.environ.get("OPENCONNECT_USER", "")
        password = os.environ.get("OPENCONNECT_PASSWORD", "")
        has_creds = bool(user and password)

        auto_connect = (
            has_creds
            and os.environ.get("AUTO_CONNECT", "").lower() in ("1", "true", "yes")
        )

        if errors:
            sys.exit("Configuration errors:\n  " + "\n  ".join(errors))

        return cls(
            user=user,
            password=password,
            url=url,
            options=os.environ.get("OPENCONNECT_OPTIONS", ""),
            heartbeat_url=os.environ.get("HEARTBEAT_URL", ""),
            heartbeat_interval=int(os.environ.get("HEARTBEAT_INTERVAL", "30")),
            has_creds=has_creds,
            auto_connect=auto_connect,
        )