"""``sbx`` — drive a sandbox environment and assert yeaboi against it.

Only the offline verbs are implemented so far: ``tiers`` and ``doctor
--offline`` read the registry, and ``env`` renders an environment block from
values passed in. ``up``/``down``/``assert`` arrive with the first provisioned
vendor and are refused rather than faked until then.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from yeaboi_sandbox import envblock, envid
from yeaboi_sandbox.tiers.registry import SANDBOX_ROWS, by_key

NOT_YET = "not built yet — see docs/runbook.md for the phase this lands in"


def _slot(stack: str) -> int:
    """The slot named by a stack, e.g. ``sbx-17`` -> 17."""
    slot = envid.owned_slot(stack or "")
    if slot is None:
        raise SystemExit(f"'{stack}' is not a sandbox stack name — expected sbx-<n>")
    return slot


def _cmd_tiers(args: argparse.Namespace) -> int:
    rows = [r for r in SANDBOX_ROWS if not args.tier or r.tier == args.tier]
    if args.format == "json":
        print(json.dumps([r.__dict__ for r in rows], indent=2, default=str))
        return 0
    print(f"{'connector':16} {'tier':4} {'status':8} provisioner")
    for row in rows:
        print(f"{row.key:16} {row.tier:4} {row.status:8} {row.provisioner}")
    pending = sum(1 for r in SANDBOX_ROWS if r.status == "pending")
    print(f"\n{len(SANDBOX_ROWS) - pending} built, {pending} pending, {len(SANDBOX_ROWS)} total")
    return 0


def _cmd_env(args: argparse.Namespace) -> int:
    slot = _slot(args.stack)
    home = Path(args.home) if args.home else Path.home() / ".yeaboi-sandbox" / envid.env_id(slot)
    values = json.loads(Path(args.values).read_text()) if args.values else {}
    block = envblock.build(values, yeaboi_home=home, isolate_home=not args.keep_home)
    print(block.exports())
    if block.blanked:
        print(f"# {len(block.blanked)} declared env(s) blanked — no sandbox value", file=sys.stderr)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    """Offline: the registry's own invariants. Online adds the tenant fence."""
    problems = []
    for row in SANDBOX_ROWS:
        if row.tier in ("B", "C") and not row.reason:
            problems.append(f"{row.key}: tier {row.tier} with no stated reason")
        if row.tier == "A" and row.status == "built" and not row.expects:
            problems.append(f"{row.key}: built tier A with no assertion")
    if not args.offline:
        print(f"the tenant fence is {NOT_YET}", file=sys.stderr)
        return 2
    for line in problems:
        print(f"FAIL {line}")
    print(f"{len(SANDBOX_ROWS)} rows checked, {len(problems)} problem(s)")
    return 1 if problems else 0


def _refuse(args: argparse.Namespace) -> int:
    print(f"sbx {args.command}: {NOT_YET}", file=sys.stderr)
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sbx", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    tiers = sub.add_parser("tiers", help="What every connector's sandbox story is")
    tiers.add_argument("--tier", choices=["A", "B", "C"], default="")
    tiers.add_argument("--format", choices=["text", "json"], default="text")
    tiers.set_defaults(func=_cmd_tiers)

    env = sub.add_parser("env", help="Print the environment block as shell exports")
    env.add_argument("--stack", required=True, help="sbx-<n>")
    env.add_argument("--values", default="", help="JSON file of stack outputs")
    env.add_argument("--home", default="", help="Override YEABOI_HOME")
    env.add_argument("--keep-home", action="store_true", help="Do not move HOME (weaker isolation)")
    env.set_defaults(func=_cmd_env)

    doctor = sub.add_parser("doctor", help="Check the registry, and the tenants when online")
    doctor.add_argument("--stack", default="")
    doctor.add_argument("--offline", action="store_true", help="Registry invariants only")
    doctor.set_defaults(func=_cmd_doctor)

    for name, help_text in (
        ("up", "Provision and seed an environment"),
        ("down", "Destroy an environment and sweep its prefix"),
        ("seed", "Re-seed an environment"),
        ("assert", "Run the assertions against an environment"),
        ("sweep", "Delete resources whose environment is gone"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--stack", default="")
        p.add_argument("--only", default="")
        p.add_argument("--apply", action="store_true")
        p.set_defaults(func=_refuse)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in ("up", "down", "seed", "assert") and args.__dict__.get("only"):
        if by_key(args.only) is None:
            raise SystemExit(f"unknown connector '{args.only}' — try `sbx tiers`")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
