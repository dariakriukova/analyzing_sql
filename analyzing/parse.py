import glob
import os
import re
from datetime import datetime
from io import StringIO
from os import path
from typing import Union, Generator

import click
import pandas as pd
from sqlalchemy.orm import Session, joinedload

from orm import IVMeasurement, ChipState, Wafer, Chip
from utils import logger


@click.command(name='parse', help="Parse .dat files with IV measurements and save to database")
@click.pass_context
@click.argument('path_or_glob', type=click.Path(dir_okay=False), default="./*.dat")
def parse(ctx: click.Context, path_or_glob: str):
    session = ctx.obj['session']
    chip_states = ctx.obj['chip_states']

    file_paths = [path_or_glob] if path.isfile(path_or_glob) else glob.iglob(path_or_glob)
    for file_path in file_paths:
        wafer, chip = ask_chip_and_wafer(file_path, session)
        chip_state = ask_chip_state(chip_states)
        data = parse_file(file_path)
        measurements = create_measurements(data['data'], data['timestamp'], chip, chip_state)
        session.add_all(measurements)
        session.commit()
        new_file_name = f'{file_path}.parsed'
        os.rename(file_path, new_file_name)
        logger.info(f"{file_path} was renamed to {new_file_name} and saved to database")


def ask_chip_and_wafer(file_path: str, session: Session) -> (Wafer, Chip):
    matcher = re.compile(r'^IV\s+(?P<wafer>[\w\d]+)\s+(?P<chip>[\w\d]+)\..*$')
    filename = path.basename(file_path)
    match = matcher.match(filename)
    if match is None:
        logger.warn(f"Could not guess chip and wafer from filename ({filename})")
        chip_name = click.prompt("Input chip name", type=str)
        wafer_name = click.prompt("Input wafer name", type=str)
    else:
        chip_name = match.group('chip')
        wafer_name = match.group('wafer')
        confirm = click.confirm(
            f"Guessed from filename ({filename}): wafer={wafer_name}, chip={chip_name}",
            default=True)
        if not confirm:
            chip_name = click.prompt("Input chip name", type=str, default=chip_name,
                                     show_default=True)
            wafer_name = click.prompt("Input wafer name", type=str, default=wafer_name,
                                      show_default=True)

    wafer = session.query(Wafer).filter(Wafer.name == wafer_name) \
        .options(joinedload(Wafer.chips)).one_or_none()
    if wafer is None:
        wafer = Wafer(name=wafer_name)
        session.add(wafer)
    chip = next((chip for chip in wafer.chips if chip.name == chip_name), None)
    if chip is None:
        chip = Chip(name=chip_name, wafer=wafer)
        session.add(chip)

    return wafer, chip


def ask_chip_state(chip_states: list[ChipState]) -> ChipState:
    try:
        if ask_chip_state.apply_to_all is not None:
            return ask_chip_state.apply_to_all
    except AttributeError:
        ask_chip_state.apply_to_all = None
    option_type = click.Choice([str(state.id) for state in chip_states])
    option_help = "\n".join(["{} - {};".format(state.id, state.name) for state in chip_states])
    chip_state_id = click.prompt(f"Input chip state\n{option_help}", type=option_type,
                                 show_choices=False, prompt_suffix='\n')
    chip_state = next(state for state in chip_states if str(state.id) == chip_state_id)
    apply_to_all = click.confirm(f"Apply chip state \"{chip_state.name}\" to all files",
                                 default=False)
    if apply_to_all:
        ask_chip_state.apply_to_all = chip_state
    return chip_state


def parse_file(file_path: str) -> dict[str, Union[datetime, pd.DataFrame]]:
    with click.open_file(file_path) as file:
        content = file.read()

    date_matcher = re.compile(r'^Date:\s*(?P<date>[\d/]+)\s*$', re.M | re.I)
    date_match = date_matcher.search(content)

    if date_match is None:
        logger.warn(f"Could not guess date from file ({file_path})")
        date = click.prompt("Input date", type=click.DateTime(formats=['%Y-%m-%d']),
                            default=datetime.now(), show_default=True)
    else:
        date = datetime.strptime(date_match.group('date'), '%m/%d/%Y')

    time_matcher = re.compile(r'^Time:\s*(?P<time>[\d:]+)\s*$', re.M | re.I)
    time_match = time_matcher.search(content)
    if time_match is None:
        logger.warn(f"Could not guess time from file ({file_path})")
        time = click.prompt("Input time", type=click.DateTime(formats=['%H:%M:%S']),
                            default=datetime.now(), show_default=True)
    else:
        time = datetime.strptime(time_match.group('time'), '%H:%M:%S')

    timestamp = datetime.combine(date, datetime.time(time))
    table_matcher = re.compile(r'^(?P<table>([VIRGNCA]{3}\s?){3,4}$\n[\s\d.E+-]*?)[\n\r]{2}',
                               re.M | re.I)
    data = pd.DataFrame()
    for match in table_matcher.finditer(content):
        data = pd.concat([data, pd.read_csv(StringIO(match.group('table')), sep='\t')], copy=False)

    return {'timestamp': timestamp, 'data': data}


def create_measurements(data: pd.DataFrame, timestamp: datetime, chip: Chip,
                        chip_state: ChipState) -> Generator[IVMeasurement, None, None]:
    for idx, row in data.iterrows():
        yield IVMeasurement(
            chip=chip,
            int_time='MED',
            chip_state=chip_state,
            voltage_input=row['VCA'],
            anode_current=row['IAN'],
            cathode_current=row['ICA'],
            datetime=timestamp)
