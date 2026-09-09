"""Build the environment a sandbox run hands to yeaboi.

The subtle part is not what to set, it is what to *unset*.

``config.load_user_config()`` reads ``~/.yeaboi/.env`` with ``override=False``,
and ``config.get_config_dir()`` computes ``Path.home()/".yeaboi"`` live — it
does not consult ``YEABOI_HOME``. So a connector the sandbox failed to supply a
value for silently falls back to the developer's real credential and the run
hits a production tenant while reporting green.

:func:`build` therefore starts from an allowlist and sets **every** env var
every connector declares, using the empty string for the ones the sandbox does
not provide. ``isolate_home`` additionally moves ``HOME``, so ``~/.yeaboi/.env``
is not on disk for the child at all.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

#: What a child process keeps from the parent. Everything else is dropped so a
#: stray export cannot reach a vendor.
PASSTHROUGH = (
    "PATH",
    "HOME",
    "SHELL",
    "TERM",
    "LANG",
    "LC_ALL",
    "TMPDIR",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "UV_CACHE_DIR",
    "XDG_CACHE_HOME",
    "VIRTUAL_ENV",
)


class IsolationError(RuntimeError):
    """A run that would have reached the developer's real configuration."""


def declared_envs() -> tuple[str, ...]:
    """Every env var any connector reads, from yeaboi's own descriptors.

    Read live rather than copied, so a connector that grows a credential is
    covered without an edit here.
    """
    from yeaboi.connectors import legacy, registry

    return tuple(dict.fromkeys(registry.all_envs() + legacy.all_envs()))


def real_config_file() -> Path:
    """The developer's real credential file, resolved against the real HOME."""
    return Path(os.path.expanduser("~")) / ".yeaboi" / ".env"


def fingerprint(path: Path) -> str:
    """A cheap tamper check: size, mtime and digest, or "" when absent."""
    if not path.exists():
        return ""
    raw = path.read_bytes()
    stat = path.stat()
    return f"{stat.st_size}:{int(stat.st_mtime)}:{hashlib.sha256(raw).hexdigest()[:16]}"


@dataclass(frozen=True)
class Block:
    """The environment for one sandbox run, and where its data will land."""

    env: dict[str, str]
    yeaboi_home: Path
    #: The declared envs the sandbox had no value for. Every one is exported as
    #: "" rather than left unset — that is the guard, not a diagnostic.
    blanked: tuple[str, ...]

    def exports(self) -> str:
        """The block as shell, for ``eval "$(sbx env)"``."""
        lines = []
        for key in sorted(self.env):
            value = self.env[key].replace("'", "'\\''")
            lines.append(f"export {key}='{value}'")
        return "\n".join(lines)


def build(
    values: dict[str, str],
    *,
    yeaboi_home: Path,
    isolate_home: bool = True,
    parent: dict[str, str] | None = None,
) -> Block:
    """The environment for a sandbox run.

    ``values`` is what the stack produced. Anything a connector declares and the
    stack did not produce is set to "", which is what stops the fall-through to
    ``~/.yeaboi/.env``.
    """
    source = dict(os.environ if parent is None else parent)
    env = {k: source[k] for k in PASSTHROUGH if k in source}

    declared = declared_envs()
    unknown = sorted(set(values) - set(declared))
    if unknown:
        raise IsolationError(
            f"the stack produced env vars no connector declares: {unknown}. "
            "Either the name is wrong or yeaboi dropped the field."
        )

    blanked = []
    for name in declared:
        value = str(values.get(name, "") or "").strip()
        env[name] = value
        if not value:
            blanked.append(name)

    yeaboi_home = Path(yeaboi_home).resolve()
    if yeaboi_home == (Path(os.path.expanduser("~")) / ".yeaboi").resolve():
        raise IsolationError("YEABOI_HOME must not be the developer's real ~/.yeaboi")
    env["YEABOI_HOME"] = str(yeaboi_home)

    # Nothing in a sandbox run should phone home or ask about updates.
    env["YEABOI_TELEMETRY"] = ""
    env["YEABOI_UPDATE_CHECK"] = "0"
    env["TZ"] = "UTC"

    if isolate_home:
        sandbox_home = yeaboi_home / "home"
        env["HOME"] = str(sandbox_home)

    return Block(env=env, yeaboi_home=yeaboi_home, blanked=tuple(blanked))
