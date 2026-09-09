"""What this repo's README GIF shows: the registry, offline.

A terminal demo rather than a page: this repo has no browser surface, and the
thing worth showing is the roster — every connector, its tier, and how much of
it is built. Deliberately the *offline* verbs, so the recording needs no AWS
account, no vendor tenant and no credential, and anyone can reproduce it.
"""

SPEC = {
    "kind": "tty",
    "gif": "demo-sandbox.gif",
    "cmd": ["bash", "--norc", "--noprofile", "-i"],
    "cols": 100,
    "rows": 36,
    "title": "yeaboi-sandbox",
    # `sbx` prints to a normal scrollback; it is not a full-screen TUI.
    "require_alt_screen": False,
    "cwd": ".",
    "env": {"PS1": "$ ", "TERM": "xterm-256color", "COLUMNS": "100"},
    "steps": [
        ("pause", 0.8),
        ("type", "sbx tiers --tier A\n", 22),
        ("await", ["built,", "pending"], 30),
        ("pause", 2.4),
        ("type", "sbx tiers --tier C\n", 22),
        ("await", ["apple_music"], 30),
        ("pause", 2.4),
        ("type", "make test\n", 22),
        ("await", ["passed", "failed"], 180),
        ("pause", 2.6),
    ],
    "verify": {
        "duration_s": (6.0, 60.0),
    },
}
