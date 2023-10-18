import click
from pathlib import Path

ClickTypeReadableFile = click.Path(exists=True, file_okay=True, readable=True, path_type=Path)
ClickTypeReadableDirectory = click.Path(exists=True, file_okay=False, readable=True, path_type=Path)
ClickTypeWritableDirectory = click.Path(file_okay=False, writable=True, path_type=Path)
