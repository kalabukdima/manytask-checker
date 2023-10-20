from __future__ import annotations

import shutil
from pathlib import Path
import glob

from ..course import CourseConfig, CourseDriver
from ..course.schedule import CourseSchedule
from ..utils.files import filename_match_patterns
from ..utils.git import commit_push_all_repo, setup_repo_in_dir
from ..utils.print import print_info


def _find_files(
    root_dir: Path,
    patterns: list[str],
):
    matches = []
    for pattern in patterns:
        matches.extend(glob.glob(pattern, root_dir=root_dir, recursive=True, include_hidden=False))
    return [Path(path) for path in matches if Path(path).is_file()]

def _get_enabled_files_and_dirs_private_to_public(
        course_config: CourseConfig,
        course_schedule: CourseSchedule,
        public_course_driver: CourseDriver,
        private_course_driver: CourseDriver,
) -> dict[Path, Path]:
    patterns = course_config.public_patterns
    files = {
        path: public_course_driver.root_dir / path
        for path in _find_files(str(private_course_driver.root_dir), patterns)
        if path.is_file()
    }
    return files


def export_public_files(
        course_config: CourseConfig,
        course_schedule: CourseSchedule,
        public_course_driver: CourseDriver,
        private_course_driver: CourseDriver,
        export_dir: Path,
        *,
        dry_run: bool = False,
) -> None:
    export_dir.mkdir(exist_ok=True, parents=True)

    if dry_run:
        print_info('Dry run. No repo setup, only copy in export_dir dir.', color='orange')

    files_and_dirs_to_add_map: dict[Path, Path] = _get_enabled_files_and_dirs_private_to_public(
        course_config,
        course_schedule,
        public_course_driver,
        private_course_driver,
    )

    if not dry_run:
        if not course_config.gitlab_service_token:
            raise Exception('Unable to find service_token')  # TODO: set exception correct type

        print_info('Setting up public repo...', color='orange')
        print_info(f'  Copy {course_config.gitlab_url}/{course_config.public_repo} repo in {export_dir}')
        print_info(
            f'  username {course_config.gitlab_service_username} \n'
            f'  name {course_config.gitlab_service_name} \n'
            f'  branch {course_config.default_branch} \n',
            color='grey'
        )
        setup_repo_in_dir(
            export_dir,
            f'{course_config.gitlab_url}/{course_config.public_repo}',
            service_username=course_config.gitlab_service_username,
            service_token=course_config.gitlab_service_token,
            git_user_email=course_config.gitlab_service_email,
            git_user_name=course_config.gitlab_service_name,
            branch=course_config.default_branch,
        )

    # remove all files from export_dir (to delete deleted files)
    print_info('Delete all files from old export_dir (keep .git)...', color='orange')
    deleted_files: set[str] = set()
    for path in export_dir.glob('*'):
        if path.name == '.git':
            continue

        if path.is_file() or path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        else:
            print(f'wtf. {path}')

        deleted_files.add(str(path.as_posix()))

    # copy updated files
    print_info('Copy updated files...', color='orange')
    for filename_private, filename_public in sorted(files_and_dirs_to_add_map.items()):
        relative_private_filename = str(filename_private.relative_to(private_course_driver.root_dir))
        relative_public_filename = str(filename_public.relative_to(public_course_driver.root_dir))
        print_info(f'  {relative_private_filename}', color='grey')
        print_info(f'  \t-> {relative_public_filename}', color='grey')

        if filename_private.is_dir():
            shutil.copytree(filename_private, export_dir / relative_public_filename, dirs_exist_ok=True)
        else:
            (export_dir / relative_public_filename).parent.mkdir(exist_ok=True, parents=True)
            shutil.copy(filename_private, export_dir / relative_public_filename)

    if not dry_run:
        # files for git add
        commit_push_all_repo(
            export_dir,
            branch=course_config.default_branch,
        )
