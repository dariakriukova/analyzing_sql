import logging
import os
from typing import Union

import click
import keyring
import sentry_sdk
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import Wafer, ChipState
from utils import logger, get_db_url, CsvChoice
from .compare_wafers import compare_wafers
from .parse import parse
from .db import db_group, set_db
from .show import show
from .summary import summary_iv, summary_cv


@click.group(commands=[summary_iv, summary_cv, db_group, show, parse, compare_wafers])
@click.pass_context
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False))
@click.option("--db-url", help="Database URL.")
def analyzing(ctx: click.Context, log_level: str, db_url: Union[str, None]):
    logger.setLevel(log_level)
    ctx.obj = dict()
    active_command = analyzing.commands[ctx.invoked_subcommand]
    if active_command is not db_group:
        try:
            if db_url is None and not os.environ.get('DEV', False):
                db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                                    password=keyring.get_password("ELFYS_DB", "PASSWORD"))
            engine = create_engine(db_url,
                                   echo="debug" if logger.getEffectiveLevel() == logging.DEBUG else False)
            engine.connect()
            session = ctx.with_resource(Session(bind=engine, autoflush=False, autocommit=False))
            ctx.obj['session'] = session
        except OperationalError as e:
            if 'Access denied' in str(e):
                logger.warn(
                    f"Access denied to database. Try again or run {set_db.name} command to set new credentials.")
            else:
                logger.error(f"Error connecting to database: {e}")
                sentry_sdk.capture_exception(e)
            ctx.exit()

        if active_command in (summary_iv, summary_cv, compare_wafers):
            chip_states = session.query(ChipState).all()
            ctx.obj['chip_states'] = chip_states
            chip_state_option = next((o for o in active_command.params if o.name == 'chip_state_ids'))
            chip_state_option.type = CsvChoice(
                [str(state.id) for state in chip_states] + chip_state_option.default)
            chip_state_option.help = chip_state_option.help + "\n\n\b\n" + "\n".join(
                ["{} - {};".format(state.id, state.name) for state in chip_states])

        if active_command in (summary_cv, summary_iv):
            last_wafer = session.query(Wafer).order_by(desc(Wafer.record_created_at)).first()
            default_wafer_name = last_wafer.name
            wafer_option = next((o for o in active_command.params if o.name == 'wafer_name'))
            wafer_option.default = default_wafer_name
            ctx.obj['default_wafer'] = last_wafer
