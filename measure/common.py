from jsonpath_ng import parse
from pyvisa.resources import GPIBInstrument
from sqlalchemy.orm import Session, joinedload

from orm import Wafer, Chip
from utils import logger


def set_configs(instrument: GPIBInstrument, commands: list[str]):
    for command in commands:
        instrument.write(command)


def execute_command(instrument: GPIBInstrument, command: str, command_type: str):
    if command_type == 'query':
        return instrument.query(command)
    elif command_type == 'write':
        return instrument.write(command)
    elif command_type == 'query_ascii_values':
        return list(instrument.query_ascii_values(command))
    elif command_type == 'query_csv_values':
        return [float(value) for value in instrument.query(command).split(',')]
    else:
        raise ValueError(f'Invalid command type {command_type}')


def get_or_create_chips(session: Session, wafer_name: str, chip_names: list[str]) -> dict[str, Chip]:
    wafer = session.query(Wafer).filter(Wafer.name == wafer_name) \
        .options(joinedload(Wafer.chips)).one_or_none()
    if wafer is None:
        chips = [Chip(name=chip_name) for chip_name in chip_names]
        wafer = Wafer(name=wafer_name, chips=chips)
    else:
        existing_chip_names = [chip.name for chip in wafer.chips]
        new_chips = [Chip(name=chip_name) for chip_name in chip_names if
                     chip_name not in existing_chip_names]
        wafer.chips.extend(new_chips)

    session.add(wafer)
    session.commit()
    return {chip.name: chip for chip in wafer.chips if chip.name in chip_names}


def get_raw_measurements(instrument: GPIBInstrument, commands: dict) -> dict[str, list]:
    measurements: dict[str, list] = dict()
    for command in commands:
        value = execute_command(instrument, command['command'], command['type'])
        if 'name' in command:
            measurements[command['name']] = value
    return measurements


def validate_raw_measurements(measurements: dict[str, list],
                              configs: dict[str, dict[dict]]) -> bool:
    for value_name, config in configs.items():
        for validator_name, rules in config.items():
            path = parse(value_name)
            for ctx in path.find(measurements):
                value = ctx.value
                if rules.get('abs'):
                    value = abs(value)
                if validator_name == 'min':
                    if value < rules['value']:
                        logger.warning(rules['message'])
                        return False
                elif validator_name == 'max':
                    if value > rules['value']:
                        logger.warning(rules['message'])
                        return False
                else:
                    raise ValueError(f'Unknown validator {validator_name}')
    return True
