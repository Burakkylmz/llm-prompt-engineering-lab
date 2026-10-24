"""Root CLI entry point.

Each lab module exposes `LAB_ID: str` and `register(subparsers) -> None`, mirroring the
`llm-token-economics-lab` reference pattern (see docs/decisions.md): labs are discovered by
an explicit hardcoded list of module paths, never by scanning the filesystem, so a
half-written lab directory can never be picked up accidentally.
"""

from __future__ import annotations

import argparse
import importlib
from pathlib import Path
from types import ModuleType

from lab_core.datasets import DatasetError
from lab_core.reporting import write_full_report
from lab_core.results_writer import ResultsWriter

# Populated here, one entry per completed lab (see docs/tasks.md for build order).
LAB_MODULES: list[str] = [
    "labs.lab01_prompt_anatomy.cli",
]


def _discover_labs() -> list[tuple[str, ModuleType]]:
    registry: list[tuple[str, ModuleType]] = []
    for module_path in LAB_MODULES:
        module = importlib.import_module(module_path)
        registry.append((module.LAB_ID, module))
    return registry


def _cmd_list(args: argparse.Namespace) -> None:
    labs = _discover_labs()
    if not labs:
        print("No labs registered yet.")
        return
    print("Available labs:")
    for lab_id, _module in labs:
        print(f"  {lab_id}")


def _cmd_validate_data(args: argparse.Namespace) -> None:
    labs = _discover_labs()
    if not labs:
        print("No labs registered yet.")
        return
    any_failed = False
    for lab_id, module in labs:
        validate_fn = getattr(module, "validate_dataset", None)
        if validate_fn is None:
            print(f"{lab_id}: SKIP (no validate_dataset() exposed)")
            continue
        try:
            validate_fn()
        except DatasetError as exc:
            print(f"{lab_id}: FAIL - {exc}")
            any_failed = True
        else:
            print(f"{lab_id}: OK")
    if any_failed:
        raise SystemExit(1)


def _cmd_report(args: argparse.Namespace) -> None:
    run_dir: Path = args.run_dir
    handle = ResultsWriter.load_run(run_dir)
    module = next((m for lab_id, m in _discover_labs() if lab_id == handle.lab_id), None)
    if module is None:
        print(f"No registered lab module found for lab_id={handle.lab_id!r}")
        raise SystemExit(1)

    observations = handle.read_observations()
    write_full_report(
        run_dir,
        observations,
        module.CONDITION_ORDER,
        module.BASELINE_CONDITION_ID,
        handle.execution_mode,
        labels=getattr(module, "LABELS", None),
    )
    print(f"Report regenerated for {run_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lab-runner",
        description="LLM Prompt & Context Engineering training labs (Groq API).",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")

    list_parser = subparsers.add_parser("list", help="List all available labs")
    list_parser.set_defaults(func=_cmd_list)

    validate_parser = subparsers.add_parser(
        "validate-data", help="Validate every registered lab's dataset against its JSON schema"
    )
    validate_parser.set_defaults(func=_cmd_validate_data)

    report_parser = subparsers.add_parser(
        "report", help="Regenerate summary.json/comparison.md/charts from an existing run directory"
    )
    report_parser.add_argument("run_dir", type=Path)
    report_parser.set_defaults(func=_cmd_report)

    for _lab_id, module in _discover_labs():
        module.register(subparsers)

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
