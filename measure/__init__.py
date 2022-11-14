import logging
import sys
from typing import Union

import click
import keyring
import pyvisa
import sentry_sdk
import yaml
from pyvisa import Error
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import ChipState
from utils import logger, get_db_url
from .iv import iv
from .cv import cv


@click.group(commands=[iv, cv])
@click.pass_context
@click.option("-c", "--config", "config_path", required=True, type=click.Path(exists=True),
              help="Path to config file. See ./measure/configs/*.yaml")
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False))
@click.option("--db-url", help="Database URL.")
@click.option('--simulate', is_flag=True, help="Simulate pyvisa instrument.", default=False)
@click.option("--dry-run", is_flag=True, default=False,
              help="Don't save measurements to the database.")
def measure(ctx: click.Context, config_path: str, log_level: str, db_url: Union[str, None],
            simulate: bool, dry_run: bool):
    logger.setLevel(log_level)

    with click.open_file(config_path) as config_file:
        configs = yaml.safe_load(config_file)

    ctx.obj = {
        'simulate': simulate,
        'configs': configs
    }

    try:
        if db_url is None:
            db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                                password=keyring.get_password("ELFYS_DB", "PASSWORD"))
        engine = create_engine(db_url,
                               echo="debug" if logger.getEffectiveLevel() == logging.DEBUG else False)
        session = Session(bind=engine)

        if dry_run:
            session.commit = lambda: None
            session.flush = lambda: None

        ctx.with_resource(session)
        chip_states = session.query(ChipState).all()

    except OperationalError as e:
        if 'Access denied' in str(e):
            logger.warn(
                f"Access denied to database. Try again or run set-db command to set new credentials.")
        else:
            logger.error(f"Error connecting to database: {e}")
            sentry_sdk.capture_exception(e)
        sys.exit()

    active_command = measure.commands[ctx.invoked_subcommand]
    chip_state_option = next((o for o in active_command.params if o.name == 'chip_state_id'))
    chip_state_option.type = click.Choice([str(state.id) for state in chip_states])
    chip_state_option.help = chip_state_option.help + "\n\n" + "\n".join(
        ["{} - {};".format(state.id, state.name) for state in chip_states])
    ctx.obj['session'] = session
    ctx.obj['chip_states'] = chip_states

    try:
        if simulate:
            rm = pyvisa.ResourceManager('measure/simulation.yaml@sim')
            instrument = rm.open_resource('GPIB0::9::INSTR',
                                          write_termination='\n',
                                          read_termination='\n')
        else:
            pyvisa_config = configs['instruments']['pyvisa']
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(pyvisa_config['resource'], **pyvisa_config['kwargs'])
        ctx.with_resource(instrument)
    except Error as e:
        logger.error(f"PYVISA error: {e}")
        sys.exit()

    ctx.obj['instrument'] = instrument
