import re
from pathlib import Path
from typing import Sequence

from .logger import logger

import click


def validate_chip_names(ctx, param, chip_names: Sequence[str]):
    chip_types = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'J', 'U', 'V', 'X', 'Y']
    matcher = re.compile(rf'^[{"".join(chip_types)}]\d{{4}}$')
    valid_chip_names = []
    for chip_name in map(lambda name: name.upper(), chip_names):
        if not matcher.match(chip_name):
            raise click.BadParameter(
                f'{chip_name} is not valid chip name. It must be in format LXXXX where L is a letter ({", ".join(chip_types)}) and XXXX is a number.')
        valid_chip_names.append(chip_name)
    return valid_chip_names


def validate_wafer_name(ctx, param, wafer_name: str):
    special_wafer_names = {'TEST', 'REF'}

    wafer_name = wafer_name.upper()
    if wafer_name in special_wafer_names:
        return wafer_name
    matcher = re.compile(r'^\w{2,3}\d{1,2}(-\w\d{4})?$')
    if not matcher.match(wafer_name):
        raise click.BadParameter(
            f'{wafer_name} is not valid wafer name. It must be in format LL[L]X[X][-LXXXX] where L is a letter and X is a number.'
            f' [] denotes optional symbols.'
            f'\nAlso you can use one of the special wafer names: {", ".join(special_wafer_names)}')
    return wafer_name


def validate_files_glob(ctx, param, value: str):
    if Path(value).is_dir():
        raise click.BadParameter(
            "Directories are not allowed. Please provide a pattern to find files to parse.")
    file_paths = tuple(Path('.').glob(value))
    logger.info(f"Found {len(file_paths)} files matching pattern {value}")
    if len(file_paths) == 0:
        ctx.exit()
    return tuple(Path('.').glob(value))
