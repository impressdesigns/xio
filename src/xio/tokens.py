"""Access tokens, from the Azure CLI's signed-in account.

The only module that knows where a token comes from. Xio keeps no token on disk.
"""

import base64
import json
import shutil
import subprocess
from datetime import UTC, datetime
from typing import Any

from xio.services import TENANT, Service

LOGIN_COMMAND = ("az", "login", "--tenant", TENANT, "--allow-no-subscriptions")


class TokenError(RuntimeError):
    """No token could be had."""


def azure_cli() -> str | None:
    """Return the path of the Azure CLI, if it is installed."""
    return shutil.which("az")


def _run(*arguments: str) -> str:
    executable = azure_cli()
    if executable is None:
        message = "The Azure CLI (az) is not installed."
        raise TokenError(message)
    result = subprocess.run([executable, *arguments], check=False, capture_output=True, text=True)  # noqa: S603 -- az, with fixed arguments
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1:] or ["no detail"]
        message = f"az {arguments[0]} failed ({detail[0]}). Sign in with: xio auth login"
        raise TokenError(message)
    return result.stdout


def get_token(service: Service) -> str:
    """Return a bearer token for ``service``."""
    output = _run("account", "get-access-token", "--tenant", TENANT, "--scope", service.scope, "--output", "json")
    token = json.loads(output).get("accessToken")
    if not isinstance(token, str):
        message = "az returned no access token."
        raise TokenError(message)
    return token


def account() -> str:
    """Return the name of the account the Azure CLI is signed in as."""
    name = json.loads(_run("account", "show", "--output", "json")).get("user", {}).get("name")
    if not isinstance(name, str):
        message = "az is not signed in. Sign in with: xio auth login"
        raise TokenError(message)
    return name


def login() -> int:
    """Run the Azure CLI's sign-in at the terminal and return its exit code."""
    executable = azure_cli()
    if executable is None:
        message = "The Azure CLI (az) is not installed."
        raise TokenError(message)
    return subprocess.run([executable, *LOGIN_COMMAND[1:]], check=False).returncode  # noqa: S603 -- az, with fixed arguments


def claims(token: str) -> dict[str, Any]:
    """Return a token's claims, unverified: for display only."""
    try:
        payload = token.split(".")[1]
        decoded = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError) as error:
        message = "The token is not a JWT."
        raise TokenError(message) from error
    if not isinstance(decoded, dict):
        message = "The token is not a JWT."
        raise TokenError(message)
    return decoded


def expiry(token: str) -> datetime:
    """Return when a token stops working."""
    return datetime.fromtimestamp(claims(token)["exp"], UTC)
