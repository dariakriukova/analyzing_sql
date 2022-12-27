import pprint

import click
from pyvisa.resources import GPIBInstrument
from sqlalchemy.orm import Session

from orm import CVMeasurement
from utils import logger, validate_chip_names, validate_wafer_name
from .common import set_configs, get_or_create_chips, get_raw_measurements, \
    validate_raw_measurements


@click.command(name='cv', help='Measure CV data of the current chip.')
@click.pass_context
@click.option("-n", "--chip-name", "chip_names", help="Chip name.", callback=validate_chip_names,
              multiple=True, default=[])
@click.option("-w", "--wafer", "wafer_name", prompt=f"Input wafer name",
              callback=validate_wafer_name, help="Wafer name.")
@click.option("-s", "--chip-state", "chip_state_id", prompt="Input chip state",
              help="State of the chips.")
@click.option("--auto", "automatic_mode", is_flag=True,
              help="Automatic measurement mode. Invalid measurements will be skipped.")
def cv(ctx: click.Context, chip_names: list[str], wafer_name: str, chip_state_id: str,
       automatic_mode: bool):
    instrument: GPIBInstrument = ctx.obj['instrument']
    session: Session = ctx.obj['session']
    configs: dict = ctx.obj['configs']

    if len(configs['chips']) != len(chip_names):
        if len(chip_names) > 0:
            logger.warning(
                f"Number of chip names does not match number of chips in config file. {len(configs['chips'])} chip names expected")
        for i in range(len(configs['chips']) - len(chip_names)):
            chip_name = click.prompt(f"Input chip name {i + 1}", type=str)
            chip_names.extend(validate_chip_names(ctx, ..., [chip_name]))

    chips_dict = get_or_create_chips(session, wafer_name, chip_names)

    for measurement_config in configs['measurements']:
        logger.info(f'Executing measurement {measurement_config["name"]}')
        set_configs(instrument, measurement_config['instrument'])
        raw_measurements = get_raw_measurements(instrument, configs['measure'])

        if measurement_config['program'].get('validation'):
            validation_config = measurement_config['program']['validation']
            if not validate_raw_measurements(raw_measurements, validation_config):
                if automatic_mode:
                    raise RuntimeError('Measurement is invalid')
                logger.info('\n' + pprint.pformat(raw_measurements, compact=True, indent=4))
                click.confirm("Do you want to save these measurements?", abort=True, default=True)

        for chip_name, chip_config in zip(chip_names, configs['chips'], strict=True):
            chip_id = chips_dict[chip_name].id
            measurements_kwargs = dict(
                chip_state_id=int(chip_state_id),
                chip_id=chip_id,
                **measurement_config['program']['measurements_kwargs'],
            )
            measurements = create_measurements(raw_measurements, chip_config, **measurements_kwargs)
            session.add_all(measurements)
    session.commit()
    logger.info('Measurements saved')


def create_measurements(raw_measurements: dict[str, list], chip_config: dict, **kwargs) \
        -> list[CVMeasurement]:
    print(raw_measurements)
    raw_measurements.get('voltage')
    kwarg_keys = list(chip_config.keys())

    grouped_numbers = []
    for key in kwarg_keys:
        s = slice(*chip_config[key].get('slice', [None]))
        p = chip_config[key].get('prop', None)
        grouped_numbers.append(raw_measurements[p][s])
    measurements = []

    for data in zip(*grouped_numbers, strict=True):
        measurement_kwargs = dict(zip(kwarg_keys, data, strict=True))
        measurements.append(CVMeasurement(
            **measurement_kwargs,
            **kwargs
        ))
    return measurements
