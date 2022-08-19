import pprint
import re
from time import sleep
from typing import Sequence

import click
import numpy as np
import yaml
from jsonpath_ng import parse
from pyvisa.resources import GPIBInstrument
from scipy.optimize import curve_fit
from sqlalchemy.orm import Session, joinedload
from yoctopuce.yocto_temperature import YAPI, YRefParam, YTemperature

from orm import IVMeasurement, Wafer, Chip
from utils import logger


def validate_chip_names(ctx, param, chip_names: Sequence[str]):
    chip_types = ['C', 'E', 'F', 'G', 'U', 'V', 'X', 'Y']
    matcher = re.compile(rf'^[{"".join(chip_types)}]\d{{4}}$')
    valid_chip_names = []
    for chip_name in map(lambda name: name.upper(), chip_names):
        if not matcher.match(chip_name):
            raise click.BadParameter(
                f'{chip_name} is not valid chip name. It must be in format LXXXX where L is a letter ({", ".join(chip_types)}) and XXXX is a number.')
        valid_chip_names.append(chip_name)
    return valid_chip_names


def validate_wafer_name(ctx, param, wafer_name: str):
    wafer_name = wafer_name.upper()
    if wafer_name == 'TEST':
        return wafer_name
    matcher = re.compile(r'^\w{2,3}\d{1,2}$')
    if not matcher.match(wafer_name):
        raise click.BadParameter(
            f'{wafer_name} is not valid wafer name. It must be in format LLX(X) where L is a letter and X is a number.')
    return wafer_name


@click.command(name='iv', help='Measure IV data of the current chip.')
@click.pass_context
@click.option("-c", "--config", "config_path", prompt="Config file path",
              type=click.Path(exists=True))
@click.option("-n", "--chip-name", "chip_names", help="Chip name.", callback=validate_chip_names,
              multiple=True, default=[])
@click.option("-w", "--wafer", "wafer_name", prompt=f"Input wafer name",
              callback=validate_wafer_name, help="Wafer name.")
@click.option("-s", "--chip-state", "chip_state", prompt="Input chip state",
              help="State of the chips.")
def iv(ctx: click.Context, config_path: str, chip_names: list[str], wafer_name: str,
       chip_state: str):
    with click.open_file(config_path) as config_file:
        configs = yaml.safe_load(config_file)

    instrument: GPIBInstrument = ctx.obj['instrument']
    session: Session = ctx.obj['session']

    if ctx.obj['simulate']:
        temperature = np.random.rand() * 100
    else:
        temperature = get_temperature()

    wafer = session.query(Wafer).filter(Wafer.name == wafer_name) \
        .options(joinedload(Wafer.chips)).one_or_none()

    if len(configs['chips']) != len(chip_names):
        if len(chip_names) > 0:
            logger.warning(
                f"Number of chip names does not match number of chips in config file. {len(configs['chips'])} chip names expected")
        for i in range(len(configs['chips']) - len(chip_names)):
            chip_name = click.prompt(f"Input chip name {i + 1}", type=str)

            chip_names.extend(validate_chip_names(ctx, ..., [chip_name]))

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

    for measurement_config in configs['measurements']:
        logger.info(f'Executing measurement {measurement_config["name"]}')
        set_configs(instrument, measurement_config['instrument'])

        if measurement_config['program'].get('minimum'):
            raw_measurements = get_minimal_measurements(instrument, configs['queries'])
        else:
            raw_measurements = get_raw_measurements(instrument, configs['queries'])

        if measurement_config['program'].get('validation'):
            validation_config = measurement_config['program']['validation']
            if not validate_raw_measurements(raw_measurements, validation_config):
                logger.info('\n' + pprint.pformat(raw_measurements, compact=True, indent=4))
                click.confirm("Do you want to save these measurements?", abort=True, default=True)

        for chip_name, chip_config in zip(chip_names, configs['chips'], strict=True):
            chip_id = next(chip.id for chip in wafer.chips if chip.name == chip_name)
            measurements_kwargs = dict(
                chip_state_id=int(chip_state),
                chip_id=chip_id,
                **measurement_config['program']['chip_kwargs'],
            )
            measurements = create_measurements(raw_measurements, temperature, chip_config,
                                               **measurements_kwargs)
            session.add_all(measurements)
    session.commit()
    logger.info('Measurements saved')


def set_configs(instrument: GPIBInstrument, configs: list[dict]):
    instrument.write('*CLS')  # clears the Error Queue
    instrument.write('*RST')  # performs an instrument reset

    for config in configs:
        config_name, config_value = next(iter(config.items()))
        instrument.write(f"{config_name} {config_value}")


def get_raw_measurements(instrument: GPIBInstrument, configs: list[dict]) -> dict[str, list]:
    # starts the single measurement operation
    instrument.write(":PAGE:SCON:SING")
    # starts monitoring pending operations and sets/clears the Operation complete
    instrument.query("*OPC?")
    # specifies the data format as ASCII
    instrument.write('FORM:DATA ASC')

    measurements: dict[str, list] = dict()
    for config in configs:
        value = list(instrument.query_ascii_values(config['query']))
        measurements[config['name']] = value
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


def create_measurements(measurements: dict[str, list], temperature: float, chip_config: dict,
                        **kwargs) -> list[IVMeasurement]:
    chip_measurements = zip(measurements[chip_config['voltage']],
                            measurements[chip_config['anode_current']],
                            measurements[chip_config['cathode_current']],
                            strict=True)

    measurements = []
    for voltage, anode_current, cathode_current in chip_measurements:
        measurements.append(IVMeasurement(
            voltage_input=voltage,
            anode_current=anode_current,
            cathode_current=cathode_current,
            anode_current_corrected=compute_corrected_current(temperature, anode_current),
            temperature=temperature,
            **kwargs
        ))
    return measurements


def get_minimal_measurements(instrument: GPIBInstrument, configs: list[dict]):
    def linear(x, a, b):
        return a + b * x

    prev_measurements: dict[str, list] = dict()
    while True:
        raw_measurements = get_raw_measurements(instrument, configs)
        xdata = raw_measurements['voltage']
        if 'anode_current' in raw_measurements:
            ydata = raw_measurements['anode_current']
        elif 'cathode_current' in raw_measurements:
            ydata = raw_measurements['cathode_current']
        else:
            raise ValueError('No current measurement found')
        popt, pcov = curve_fit(f=linear, xdata=xdata, ydata=ydata, p0=[0, 0],
                               bounds=(-np.inf, np.inf))
        offset = abs(popt[0])
        if prev_measurements and offset >= prev_measurements['offset']:
            prev_measurements.pop('offset')
            return prev_measurements
        prev_measurements = dict(offset=offset, **raw_measurements)
        sleep(0.5)


def compute_corrected_current(temp: float, current: float):
    target_temperature = 25
    return 1.15 ** (target_temperature - temp) * current


def get_temperature() -> float:
    errmsg = YRefParam()
    if YAPI.RegisterHub("usb", errmsg) != YAPI.SUCCESS:
        raise RuntimeError("RegisterHub (temperature sensor) error: " + errmsg.value)

    sensor: YTemperature = YTemperature.FindTemperature('PT100MK1-14A17C.temperature')
    if not (sensor.isOnline()):
        raise RuntimeError('Temperature sensor is not connected')

    temperature = sensor.get_currentValue()
    YAPI.FreeAPI()
    return temperature