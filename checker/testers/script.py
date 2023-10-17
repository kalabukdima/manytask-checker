from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ..exceptions import ExecutionFailedError, TestsFailedError
from ..utils.files import copy_files
from ..utils.print import print_info
from .tester import Tester


class ScriptTester(Tester):
    """Simplest possible tester that runs custom command from the task config

    On the build stage it copies public, private tests and solution files to the same directory
    and runs @param build_cmd command in the task directory.
    This command is expected to create files needed for testing inside the $BUILD_DIR. Its execution
    should not be controlled by the solution contents.

    On the test stage it runs @param test_cmd in the isolated sandbox inside the build directory
    limiting its run time to @test_timeout seconds.

    If you need to run more than one command consider using shell operators: `<command1> && <command2>`
    """

    @dataclass
    class TaskTestConfig(Tester.TaskTestConfig):
        test_timeout: int = 60  # seconds

        allow_change: list[str] = field(default_factory=list)
        build_cmd: str = ''
        test_cmd: str = ''

    def __init__(
            self,
            cleanup: bool = True,
            dry_run: bool = False,
            default_build_cmd: str | None = None,
            default_test_cmd: str | None = None,
    ):
        super(ScriptTester, self).__init__(cleanup=cleanup, dry_run=dry_run)
        self.default_build_cmd = default_build_cmd
        self.default_test_cmd = default_test_cmd

    def _gen_build(  # type: ignore[override]
            self,
            test_config: TaskTestConfig,
            build_dir: Path,
            source_dir: Path,
            public_tests_dir: Path | None,
            private_tests_dir: Path | None,
            tests_root_dir: Path,
            sandbox: bool = True,
            verbose: bool = False,
            normalize_output: bool = False,
    ) -> None:
        build_cmd = test_config.build_cmd or self.default_build_cmd
        if build_cmd is None:
            return
        assert public_tests_dir

        print_info('Building...', color='orange')

        if private_tests_dir is not None:
            self._executor(
                copy_files,
                source=private_tests_dir,
                target=public_tests_dir,
                verbose=verbose,
            )

        self._executor(
            copy_files,
            source=source_dir,
            target=public_tests_dir,
            patterns=test_config.allow_change,
            verbose=verbose,
        )

        if not self.dry_run:
            env = {
                "PATH": os.environ["PATH"],
                "BUILD_DIR": str(build_dir.absolute()),
                "ROOT_DIR": str(tests_root_dir.absolute()),
            }
            self._executor(
                ["sh", "-ec" + ("x" if verbose else ""), build_cmd],
                cwd=public_tests_dir,
                env=env,
                verbose=verbose,
            )

    def _clean_build(  # type: ignore[override]
            self,
            test_config: TaskTestConfig,
            build_dir: Path,
            verbose: bool = False,
    ) -> None:
        self._executor(
            ['rm', '-rf', str(build_dir)],
            check=False,
            verbose=verbose,
        )

    def _run_tests(  # type: ignore[override]
            self,
            test_config: TaskTestConfig,
            build_dir: Path,
            public_tests_dir: Path | None,
            sandbox: bool = False,
            verbose: bool = False,
            normalize_output: bool = False,
    ) -> float:
        test_cmd = test_config.test_cmd or self.default_test_cmd
        if test_cmd is None:
            return
        assert public_tests_dir

        tests_err = None
        try:
            print_info('Running tests...', color='orange')
            if not self.dry_run:
                env = {
                    "PATH": os.environ["PATH"],
                    "BUILD_DIR": str(build_dir.absolute()),
                }
                output = self._executor(
                    ["sh", "-ec" + ("x" if verbose else ""), test_cmd],
                    sandbox=sandbox,
                    cwd=str(public_tests_dir.absolute()),
                    env=env,
                    timeout=test_config.test_timeout,
                    verbose=verbose,
                    capture_output=True,
                )
                print_info(output, end='')
                print_info('OK', color='green')
        except ExecutionFailedError as e:
            tests_err = e
            print_info(e.output, end='')
            print_info('ERROR', color='red')

        if tests_err is not None:
            raise TestsFailedError('Tests error', output=tests_err.output) from tests_err

        return 1.
