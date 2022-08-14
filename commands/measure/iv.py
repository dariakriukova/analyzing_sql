import re
from time import sleep

import click
import numpy as np
import yaml
from pyvisa.resources import GPIBInstrument
from scipy.optimize import curve_fit
from sqlalchemy.orm import Session, joinedload
from yoctopuce.yocto_temperature import YAPI, YRefParam, YTemperature

from orm import IVMeasurement, Wafer, Chip
from utils import logger


def validate_chip_name(ctx, param, value):
    chip_types = ['C', 'E', 'F', 'G', 'U', 'V', 'X', 'Y']
    matcher = re.compile(rf'[{"".join(chip_types)}]\d{{4}}')
    for chip_name in value:
        if not matcher.match(chip_name):
            raise click.BadParameter(
                f'{chip_name} is not valid chip name. It must be in format LXXXX where L is a letter ({", ".join(chip_types)}) and XXXX is a number.')
    return value


# 2 mods of measurements
#   1. with get_minimal_measurements() to wait stable values, if chip has some capasitance etc
#   2. simple get_measures() to get the values immediately


@click.command(name='iv', help='Measure IV data of the current chip.')
@click.pass_context
@click.option("-c", "--config", "config_path", prompt="Config file path",
              type=click.Path(exists=True))
@click.option("-n", "--chip-name", "chip_names", help="Chip name.", callback=validate_chip_name,
              multiple=True, default=[])
@click.option("-w", "--wafer", "wafer_name", prompt=f"Input wafer name", help="Wafer name.")
@click.option("-s", "--chip-state", "chip_state", prompt="Input chip state",
              help="State of the chips.")
def iv(ctx: click.Context, config_path: str, chip_names: tuple[str], wafer_name: str,
       chip_state: str):
    with click.open_file(config_path) as config_file:
        configs = yaml.safe_load(config_file)['configs']

    instrument: GPIBInstrument = ctx.obj['instrument']
    session: Session = ctx.obj['session']

    if ctx.obj['simulate']:
        temperature = np.random.rand() * 100
    else:
        temperature = get_temperature()

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

    for config in configs:
        logger.info(f'Executing config {config["name"]}')
        set_configs(instrument, config['instrument'])

        if config['program']['mode'] == 'minimum':
            raw_measurements = get_minimal_measurements(instrument, config['measurements'])
        elif config['program']['mode'] == 'normal':
            raw_measurements = get_measurements(instrument, config['measurements'])

        if len(config['chips']) != len(chip_names):
            chip_names = list(chip_names)
            if len(chip_names) > 0:
                logger.warning(
                    f"Number of chip names does not match number of chips in config file. {len(config['chips'])} chip names expected")
            for i in range(len(config['chips']) - len(chip_names)):
                chip_name = click.prompt(f"Input chip name {i + 1}", type=str)
                chip_names.append(chip_name)
        for chip_name, chip_config in zip(chip_names, config['chips'], strict=True):
            chip_id = next(chip.id for chip in wafer.chips if chip.name == chip_name)
            measurements_kwargs = dict(
                chip_state_id=int(chip_state),
                chip_id=chip_id,
                **config['program']['chip_kwargs'],
            )
            measurements = create_measurements(raw_measurements, temperature, chip_config,
                                               **measurements_kwargs)
            session.add_all(measurements)
        session.commit()


TARGET_TEMPERATURE = 25


def set_configs(instrument: GPIBInstrument, configs: list[dict]):
    instrument.write('*CLS')  # clears the Error Queue
    instrument.write('*RST')  # performs an instrument reset

    for config in configs:
        config_name, config_value = next(iter(config.items()))
        instrument.write(f":{config_name} {config_value}")


def get_measurements(instrument: GPIBInstrument, configs: list[dict]) -> dict[str, list]:
    # starts the single measurement operation
    instrument.write(":PAGE:SCON:SING")
    # starts monitoring pending operations and sets/clears the Operation complete
    instrument.query("*OPC?")
    # specifies the data format as ASCII
    instrument.write('FORM:DATA ASC')

    measurements: dict[str, list] = dict()
    for config in configs:
        value: list = list(instrument.query_ascii_values(config['query']))
        measurements[config['name']] = value
    return measurements


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
    linear_fun = lambda x, a, b: a + b * x

    prev_measurements: dict[str, list] = dict()
    while True:
        raw_measurements = get_measurements(instrument, configs)
        xdata = raw_measurements['voltage']
        if 'anode_current' in raw_measurements:
            ydata = raw_measurements['anode_current']
        elif 'cathode_current' in raw_measurements:
            ydata = raw_measurements['cathode_current']
        else:
            raise ValueError('No current measurement found')
        popt, pcov = curve_fit(f=linear_fun, xdata=xdata, ydata=ydata, p0=[0, 0],
                               bounds=(-np.inf, np.inf))
        # print('popt::', popt, '; pcov::', pcov)
        # print('zero::', i_3[10])
        # Voffset = -popt[0] / popt[1]
        # print('Voffset:', Voffset)
        offset = abs(popt[0])
        if prev_measurements and offset >= prev_measurements['offset']:
            return prev_measurements
        prev_measurements = dict(offset=offset, **raw_measurements)
        sleep(1)


def compute_corrected_current(temp: float, current: float):
    return 1.15 ** (TARGET_TEMPERATURE - temp) * current


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