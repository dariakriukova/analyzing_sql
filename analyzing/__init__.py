import logging
import sys
from typing import Union

import click
import keyring
import sentry_sdk
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import Wafer, ChipState
from utils import logger, get_db_url
from .parse import parse_iv, parse_cv
from .set_db import set_db
from .show import show
from .summary import summary


@click.group(commands=[summary, set_db, show, parse_cv, parse_iv])
@click.pass_context
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False))
@click.option("--db-url", help="Database URL.")
def analyzing(ctx: click.Context, log_level: str, db_url: Union[str, None]):
    logger.setLevel(log_level)
    ctx.obj = dict()
    if ctx.invoked_subcommand in (summary.name, show.name, parse_iv.name, parse_cv.name):
        try:
            if db_url is None:
                db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                                    password=keyring.get_password("ELFYS_DB", "PASSWORD"))
            engine = create_engine(db_url,
                                   echo="debug" if logger.getEffectiveLevel() == logging.DEBUG else False)
            engine.connect()
            session = Session(bind=engine)
            ctx.with_resource(session)
            ctx.obj['session'] = session
        except OperationalError as e:
            if 'Access denied' in str(e):
                logger.warn(
                    f"Access denied to database. Try again or run {set_db.name} command to set new credentials.")
            else:
                logger.error(f"Error connecting to database: {e}")
                sentry_sdk.capture_exception(e)
            sys.exit()

        if ctx.invoked_subcommand in (summary.name, parse_iv.name, parse_cv.name):
            chip_states = session.query(ChipState).all()
            ctx.obj['chip_states'] = chip_states

            if ctx.invoked_subcommand == summary.name:
                chip_state_option = next((o for o in summary.params if o.name == 'chip_states'))
                chip_state_option.type = click.Choice(
                    [str(state.id) for state in chip_states] + chip_state_option.default)
                chip_state_option.help = chip_state_option.help + "\n\n" + "\n".join(
                    ["{} - {};".format(state.id, state.name) for state in chip_states])

                last_wafer = session.query(Wafer).order_by(desc(Wafer.created_at)).first()
                default_wafer_name = last_wafer.name
                wafer_option = next((o for o in summary.params if o.name == 'wafer_name'))
                wafer_option.default = default_wafer_name
                ctx.obj['default_wafer'] = last_wafer
