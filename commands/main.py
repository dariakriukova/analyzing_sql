import logging
from typing import Union

import click
import keyring
import sentry_sdk
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import Wafer, ChipState
from utils import logger, get_db_url
from .set_db import set_db
from .summary import summary


@click.group(commands=[summary, set_db])
@click.pass_context
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False))
@click.option("--db-url", help="Database URL.")
def main(ctx: click.Context, log_level: str, db_url: Union[str, None]):
    logger.setLevel(log_level)
    if ctx.invoked_subcommand == summary.name:
        try:
            if db_url is None:
                db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                                    password=keyring.get_password("ELFYS_DB", "PASSWORD"))
            engine = create_engine(db_url,
                                   echo="debug" if logger.getEffectiveLevel() == logging.DEBUG else False)
            session = Session(bind=engine)
            ctx.with_resource(session)
            last_wafer = session.query(Wafer).order_by(desc(Wafer.created_at)).first()

            default_wafer_name = last_wafer.name
            wafer_option = next((o for o in summary.params if o.name == 'wafer_name'))
            wafer_option.default = default_wafer_name

            chip_states = session.query(ChipState).all()
            chip_state_option = next((o for o in summary.params if o.name == 'chip_states'))
            chip_state_option.type = click.Choice(
                [str(state.id) for state in chip_states] + chip_state_option.default)
            chip_state_option.help = chip_state_option.help + "\n\n" + "\n".join(
                ["{} - {};".format(state.id, state.name) for state in chip_states])
            ctx.obj = {'session': session, 'default_wafer': last_wafer, 'chip_states': chip_states}
        except OperationalError as e:
            if 'Access denied' in str(e):
                logger.warn(
                    f"Access denied to database. Try again or run {set_db.name} command to set new credentials.")
            else:
                logger.error(f"Error connecting to database: {e}")
                sentry_sdk.capture_exception(e)
            exit()
