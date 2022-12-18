import re
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Union, Generator

import click
import pandas as pd
from sqlalchemy.orm import Session, joinedload

from orm import (
    IVMeasurement,
    CVMeasurement,
    ChipState,
    Wafer,
    Chip,
    Instrument,
    EqeConditions,
    EqeMeasurement,
    EqeSession,
    Carrier
)
from utils import logger, validate_wafer_name, remember_choice, validate_files_glob, select_one


@click.command(name='iv', help="Parse IV measurements")
@click.pass_context
@click.argument('file_paths', default="./*.dat", callback=validate_files_glob)
def parse_iv(ctx: click.Context, file_paths: tuple[Path]):
    session = ctx.obj['session']
    for file_path in file_paths:
        print_filename_title(file_path)

        try:
            wafer, chip = guess_chip_and_wafer(file_path.name, 'iv', session)
            chip_state = ask_chip_state(session)
            data = parse_epg_dat_file(file_path)
            measurements = create_iv_measurements(data['data'], data['timestamp'], chip, chip_state)
            session.add_all(measurements)
            session.commit()
            mark_file_as_parsed(file_path)
        except click.Abort:
            logger.info(f"Skipping file...")
            session.rollback()
        except Exception as e:
            logger.exception(f"Could not parse file {file_path} due to error: {e}")
            session.rollback()


@click.command(name='cv', help="Parse CV measurements")
@click.pass_context
@click.argument('file_paths', default="./*.dat", callback=validate_files_glob)
def parse_cv(ctx: click.Context, file_paths: tuple[Path]):
    session = ctx.obj['session']
    for file_path in file_paths:
        print_filename_title(file_path)
        try:
            wafer, chip = guess_chip_and_wafer(file_path.name, 'cv', session)
            chip_state = ask_chip_state(session)
            data = parse_epg_dat_file(file_path)
            measurements = create_cv_measurements(data['data'], data['timestamp'], chip, chip_state)
            session.add_all(measurements)
            session.commit()
            mark_file_as_parsed(file_path)
        except click.Abort:
            logger.info(f"Skipping file...")
            session.rollback()
        except Exception as e:
            logger.exception(f"Could not parse file {file_path} due to error: {e}")
            session.rollback()


@click.command(name='eqe', help="Parse EQE measurements")
@click.pass_context
@click.argument('file_paths', default="./*.dat", callback=validate_files_glob)
def parse_eqe(ctx: click.Context, file_paths: tuple[Path]):
    session: Session = ctx.obj['session']
    instrument_map: dict[str, Instrument] = {i.name: i for i in session.query(Instrument).all()}

    for file_path in file_paths:
        print_filename_title(file_path)
        try:
            data = parse_eqe_dat_file(file_path)
            conditions = create_eqe_conditions(
                data['conditions'], instrument_map, file_path, session)
            measurements = create_eqe_measurements(data['data'], conditions)
            wafer, chip = guess_chip_and_wafer(file_path.name, 'eqe', session)
            conditions.wafer = wafer
            conditions.chip = chip
            conditions.chip_state = ask_chip_state(session)
            conditions.carrier = ask_carrier(session)
            conditions.session = ask_session(conditions.datetime, session)

            session.add(conditions)
            session.add_all(measurements)
            session.commit()
            mark_file_as_parsed(file_path)
        except click.Abort:
            session.rollback()
            logger.info(f"Skipping file...")
        except Exception as e:
            logger.exception(f"Could not parse file {file_path} due to error: {e}")
            session.rollback()


@click.group(name='parse', help="Parse files with measurements and save to database",
             commands=[parse_iv, parse_cv, parse_eqe])
def parse():
    pass


def guess_chip_and_wafer(filename: str, prefix: str, session: Session) -> tuple[Chip, Wafer]:
    matcher = re.compile(rf'^{prefix}\s+(?P<wafer>[\w\d]+)\s+(?P<chip>[\w\d-]+)(\s.*)?\..*$', re.I)
    match = matcher.match(filename)

    if match is None:
        chip_name = None
        wafer_name = None
        logger.warn(f"Could not guess chip and wafer from filename")
    else:
        chip_name = match.group('chip').upper()
        wafer_name = match.group('wafer').upper()
        logger.info(f"Guessed from filename: wafer={wafer_name}, chip={chip_name}")
    wafer_name = ask_wafer_name(wafer_name)
    chip_name = ask_chip_name(chip_name)

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


def ask_chip_name(default: str = None) -> str:
    chip_name = None
    while chip_name is None:
        chip_name = click.prompt(
            f"Input chip name ({'leave empty to accept default, ' if default is not None else ''}'skip' to skip entirely)",
            type=str,
            default=default,
            show_default=True).upper()
        if chip_name == 'SKIP':
            raise click.Abort()
    return chip_name


def ask_wafer_name(default: str = None) -> str:
    wafer_name = None
    while wafer_name is None:
        wafer_name = click.prompt(
            f"Input wafer name ({'leave empty to accept default, ' if default is not None else ''}'skip' to skip entirely)",
            type=str,
            default=default,
            show_default=True).upper()
        if wafer_name == 'SKIP':
            raise click.Abort()
        try:
            wafer_name = validate_wafer_name(None, None, wafer_name)
        except click.BadParameter as e:
            logger.warn(e)
            wafer_name = None
    return wafer_name


def ask_session(timestamp: datetime, session: Session) -> EqeSession:
    found_eqe_sessions: list[EqeSession] = session.query(EqeSession).filter(
        EqeSession.date == timestamp.date()).all()
    if len(found_eqe_sessions) == 0:
        logger.info(f"No sessions were found for measurement date {timestamp.date()}")
        eqe_session = EqeSession(date=timestamp.date())
        session.add(eqe_session)
        session.flush([eqe_session])
        logger.info(f"New eqe session was created: {eqe_session.__repr__()}")
    elif len(found_eqe_sessions) == 1:
        eqe_session = found_eqe_sessions.pop()
        logger.info(f"Existing eqe session will be used: {eqe_session.__repr__()}")
    else:
        eqe_session = select_one(found_eqe_sessions, "Select eqe session", lambda s: (s.id, s.date))
    return eqe_session


@remember_choice("Use {} for all parsed measurements")
def ask_carrier(session: Session) -> Carrier:
    carriers = session.query(Carrier).order_by(Carrier.id).all()
    carrier = select_one(carriers, "Select carrier")
    return carrier


@remember_choice("Apply {} to all parsed measurements")
def ask_chip_state(session: Session) -> ChipState:
    chip_states = session.query(ChipState).order_by(ChipState.id).all()
    chip_state = select_one(chip_states, "Select chip state")
    return chip_state


def parse_eqe_dat_file(file_path: Path) -> dict:
    patterns = (
        ('datetime', '^(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2})$',
         lambda m: datetime.strptime(m, '%d/%m/%Y %H:%M')),
        ('bias', '^Bias \(V\):\s+([\d.-]+)$', float),
        ('averaging', '^Averaging:\s+(\d+)$', int),
        ('dark_current', '^Dark current \(A\):\s+([\d\.+-E]+)$', float),
        ('temperature', '^Temperature \(C\):\s+([\d\.]+)$', float),
        ('calibration_file', '^Used reference calibration file:\s+(.*)$', str),
        ('instrument', '^Chosen SMU device:\s+(.+)$', str),
        ('ddc', '^Sent DDC:\s+(.+)$', str),
        ###### LEGACY ###### FIXME: remove later
        ('datetime', '^(\d{2}/\d{2}/\d{4}\s\d{2}\.\d{2})$',  # FOR OLD FILES WITH WRONG DATE FORMAT
         lambda m: datetime.strptime(m, '%d/%m/%Y %H.%M')),
    )
    conditions = {}
    contents = file_path.read_text()
    for prop, pattern, factory in patterns:
        match = re.compile(pattern, re.MULTILINE).search(contents)
        if match:
            conditions[prop] = factory(match.group(1))

    table_matcher = re.compile(r'^.*$[\r\n](^(([\d.E+-]+|NaN)\t?){2,}$[\r\n]){2,}',
                               re.M | re.I)
    match = table_matcher.search(contents)
    data = pd.read_csv(StringIO(match.group()), sep='\t').replace(float('nan'), None)
    return {'conditions': conditions, 'data': data}


def parse_epg_dat_file(file_path: Path) -> dict[str, Union[datetime, pd.DataFrame]]:
    content = file_path.read_text()

    date_matcher = re.compile(r'^Date:\s*(?P<date>[\d/]+)\s*$', re.M | re.I)
    date_match = date_matcher.search(content)

    if date_match is None:
        logger.warn(f"Could not guess date from file")
        date = click.prompt("Input date", type=click.DateTime(formats=['%Y-%m-%d']),
                            default=datetime.now(), show_default=True)
    else:
        date = datetime.strptime(date_match.group('date'), '%m/%d/%Y')

    time_matcher = re.compile(r'^Time:\s*(?P<time>[\d:]+)\s*$', re.M | re.I)
    time_match = time_matcher.search(content)
    if time_match is None:
        logger.warn(f"Could not guess time from file")
        time = click.prompt("Input time", type=click.DateTime(formats=['%H:%M:%S']),
                            default=datetime.now(), show_default=True)
    else:
        time = datetime.strptime(time_match.group('time'), '%H:%M:%S')

    timestamp = datetime.combine(date, datetime.time(time))
    table_matcher = re.compile(r'^(?P<table>([\w]{1,10}\s?){4}$\n[\s\d.E+-]*?)[\n\r]{2}',
                               re.M | re.I)
    data = pd.DataFrame()
    for match in table_matcher.finditer(content):
        data = pd.concat([data, pd.read_csv(StringIO(match.group('table')), sep='\t')], copy=False)

    return {'timestamp': timestamp, 'data': data}


def create_iv_measurements(data: pd.DataFrame, timestamp: datetime, chip: Chip,
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


def create_cv_measurements(data: pd.DataFrame, timestamp: datetime, chip: Chip,
                           chip_state: ChipState) -> Generator[CVMeasurement, None, None]:
    for idx, row in data.iterrows():
        yield CVMeasurement(
            chip=chip,
            chip_state=chip_state,
            voltage_input=row['BIAS'],
            capacitance=row['C'],
            datetime=timestamp)


def create_eqe_measurements(data: pd.DataFrame, conditions: EqeConditions) \
        -> Generator[EqeMeasurement, None, None]:
    header_to_prop_map = {
        'Wavelength (nm)': 'wavelength',
        'EQE (%)': 'eqe',
        'Current (A)': 'light_current',
        'Current Light (A)': 'light_current',
        'Current Dark (A)': 'dark_current',
        'Standard deviation (A)': 'std',
        'Responsivity (A/W)': 'responsivity',
    }

    for idx, row in data.iterrows():
        yield EqeMeasurement(
            conditions=conditions,
            **{header_to_prop_map[header]: row[header] for header in data.columns},
        )


def create_eqe_conditions(
        raw_data: dict, instrument_map: dict[str, Instrument], file_path: Path, session: Session):
    existing = session.query(EqeConditions).filter_by(datetime=raw_data['datetime']).all()
    if existing:
        existing_str = "\n".join([f"{i}. {c.__repr__()}" for i, c in enumerate(existing, start=1)])
        logger.info(
            f"Found existing eqe measurements at {raw_data['datetime']}:\n{existing_str}")
        click.confirm("Are you sure you want to add new measurements?", abort=True)
    instrument = instrument_map.get(raw_data.pop('instrument'), None)
    if instrument is None:
        logger.warn(f"Could not find instrument in provided file")
        instrument = select_one(list(instrument_map.values()), "Select instrument")
    comment = f"Parsed file: {file_path.name}\n" + click.prompt(
        f"Add comments for measurements",
        default='',
        show_default=False)
    conditions = EqeConditions(
        instrument=instrument,
        comment=comment or None,
        **raw_data,
    )
    return conditions


def print_filename_title(path: Path, top_margin: int = 2, bottom_margin: int = 1):
    if top_margin:
        click.echo("\n" * top_margin, nl=False)
    logger.debug(f"Processing file: {path.name}")
    click.echo("╔" + "═" * (len(path.name) + 2) + "╗")
    click.echo("║ " + path.name + " ║")
    click.echo("╚" + "═" * (len(path.name) + 2) + "╝")
    if bottom_margin:
        click.echo("\n" * bottom_margin, nl=False)


def mark_file_as_parsed(file_path: Path):
    file_path = file_path.rename(file_path.with_suffix(file_path.suffix + '.parsed'))
    logger.info(f"File was saved to database and renamed to '{file_path.name}'")
