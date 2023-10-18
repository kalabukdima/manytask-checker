from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
from .click_helpers import ClickTypeReadableFile, ClickTypeWritableDirectory

from checker.exceptions import (
    BuildFailedError,
    ExecutionFailedError,
    RunFailedError,
    StylecheckFailedError,
    TestsFailedError,
    TimeoutExpiredError,
)
from checker.executors.sandbox import Sandbox
from checker.testers import Tester
from checker.utils.files import check_files_contains_regexp
from checker.utils.print import print_info


# TODO(@kalabukdima): reuse code across testers

@dataclass
class TaskTestConfig(Tester.TaskTestConfig):
    allow_change: list[str] = field(default_factory=list)
    forbidden_regexp: list[str] = field(default_factory=list)
    copy_to_build: list[str] = field(default_factory=list)

    clang_format_enabled: bool = True
    clang_tidy_enabled: bool = True
    build_type: str = 'Asan'

    tests: list[str] = field(default_factory=list)
    timeout: float = 60.

def run_check_regexp(
    executor: Sandbox,
    config: TaskTestConfig,
    task_dir: Path,
    **kwargs: Any,
) -> None:
    check_files_contains_regexp(
        task_dir,
        regexps=config.forbidden_regexp,
        patterns=config.allow_change,
        raise_on_found=True,
    )

def run_bazel_build(
    executor: Sandbox,
    config: TaskTestConfig,
    *,
    root_dir: Path,
    build_dir: Path,
    task_dir: Path,
    verbose: bool,
    **kwargs: Any,
) -> None:
    try:
        print_info('Building tests...', color='orange')
        executor(
            ['bazel', 'build', ':all'],
            cwd=task_dir,
            verbose=verbose,
        )
    except ExecutionFailedError:
        print_info('ERROR', color='red')
        raise BuildFailedError('Bazel build failed')

def run_linter(
    executor: Sandbox,
    config: TaskTestConfig,
    *,
    run_clang_format_script: Path,
    task_dir: Path,
    verbose: bool,
    **kwargs: Any,
) -> None:
    if config.clang_format_enabled:
        try:
            print_info('Running clang format...', color='orange')
            executor(
                [str(run_clang_format_script), '-r', '.'],
                verbose=verbose,
            )
            print_info('[No issues]')
            print_info('OK', color='green')
        except ExecutionFailedError:
            print_info('ERROR', color='red')
            raise StylecheckFailedError('Style error (clang format)')

    if config.clang_tidy_enabled:
        try:
            print_info('Generating compile_commands.json...', color='orange')
            executor(
                ['bazel', 'run', '@hedron_compile_commands//:refresh_all'],
                verbose=verbose,
            )

            print_info('Running clang tidy...', color='orange')
            files = [str(file) for file in task_dir.rglob('*.cpp')]
            executor(
                ['clang-tidy', *files],
                verbose=verbose,
            )

            print_info('[No issues]')
            print_info('OK', color='green')
        except ExecutionFailedError:
            print_info('ERROR', color='red')
            raise StylecheckFailedError('Style error (clang tidy)')

def run_tests(
    executor: Sandbox,
    config: TaskTestConfig,
    *,
    task_dir: Path,
    verbose: bool,
    **kwargs: Any,
) -> None:
    try:
        print_info(f'Running tests...', color='orange')
        executor(
            ['bazel', 'test', ':all', '--color=yes'],
            sandbox=False,
            cwd=task_dir,
            verbose=verbose,
            timeout=config.timeout,
        )
        print_info('OK', color='green')
    except TimeoutExpiredError:
        print_info('ERROR', color='red')
        message = f'Your solution exceeded time limit: {config.timeout} seconds'
        raise TestsFailedError(message)
    except ExecutionFailedError:
        print_info('ERROR', color='red')
        raise TestsFailedError("Test failed (wrong answer or sanitizer error)")
    print_info('All tests passed', color='green')

def run_all(
    *,
    dry_run: bool,
    **kwargs: Any,
) -> None:
    executor = Sandbox(dry_run=dry_run)

    run_check_regexp(executor, **kwargs)
    run_bazel_build(executor, **kwargs)
    run_linter(executor, **kwargs)
    run_tests(executor, **kwargs)


@click.command
@click.option('--root-dir', envvar='ROOT_DIR', type=ClickTypeWritableDirectory, required=True, help='Project root')
@click.option('--build-dir', envvar='BUILD_DIR', type=ClickTypeWritableDirectory, required=True,
    help='Temporary build directory')
@click.option('--task-config', type=ClickTypeReadableFile, default=".tester.json", help='Task specific config file')
@click.option('--run-clang-format-script', type=ClickTypeReadableFile, default=None, help='Task specific config file')
@click.option('--verbose', is_flag=True)
@click.option('--dry-run', is_flag=True)
def main(
    root_dir: Path,
    build_dir: Path,
    task_config: Path,
    run_clang_format_script: Path | None,
    **kwargs: Any,
) -> None:
    root_dir = root_dir.resolve()
    build_dir = build_dir.resolve()
    task_dir = Path().resolve()
    assert task_config.resolve().is_relative_to(root_dir)

    config = TaskTestConfig.from_json(task_config)

    if run_clang_format_script is None:
        run_clang_format_script = root_dir / "run-clang-format.py"

    try:
        run_all(
            config=config,
            root_dir=root_dir,
            build_dir=build_dir,
            task_dir=task_dir,
            run_clang_format_script=run_clang_format_script,
            **kwargs,
        )
    except RunFailedError as e:
        print_info('\Bazel tester error: ' + e.msg + (e.output or ''), color='red')
        exit(1)

if __name__ == '__main__':  # pragma: nocover
    main()
