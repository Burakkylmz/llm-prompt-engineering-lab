"""Root CLI entry point.

Each lab module exposes `LAB_ID: str` and `register(subparsers) -> None`, mirroring the
`llm-token-economics-lab` reference pattern (see docs/decisions.md): labs are discovered by
an explicit hardcoded list of module paths, never by scanning the filesystem, so a
half-written lab directory can never be picked up accidentally.
"""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Callable

LabRegisterFn = Callable[[argparse._SubParsersAction], None]

# Populated here, one entry per completed lab (see docs/tasks.md for build order).
# Empty at the end of M1 (no lab is built yet); Lab 01 is added in M2.
LAB_MODULES: list[str] = []


def _discover_labs() -> list[tuple[str, LabRegisterFn]]:
    registry: list[tuple[str, LabRegisterFn]] = []
    for module_path in LAB_MODULES:
        module = importlib.import_module(module_path)
        registry.append((module.LAB_ID, module.register))
    return registry


def _cmd_list(args: argparse.Namespace) -> None:
    labs = _discover_labs()
    if not labs:
        print("No labs registered yet.")
        return
    print("Available labs:")
    for lab_id, _register_fn in labs:
        print(f"  {lab_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lab-runner",
        description="LLM Prompt & Context Engineering training labs (Groq API).",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    list_parser = subparsers.add_parser("list", help="List all available labs")
    list_parser.set_defaults(func=_cmd_list)

    for _lab_id, register_fn in _discover_labs():
        register_fn(subparsers)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
