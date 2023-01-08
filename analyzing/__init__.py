import logging
import os
from typing import Union

import click
import keyring
import sentry_sdk
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import ChipState, ClientVersion
from utils import logger, get_db_url, EntityChoice
from .compare_wafers import compare_wafers
from .db import db_group, set_db
from .parse import parse_group
from .show import show
from .summary import summary_group

LOGO = """
\b  █████╗  ███╗   ██╗  █████╗  ██╗   ██╗   ██╗ ███████╗ ███████╗ ██████╗
\b ██╔══██╗ ████╗  ██║ ██╔══██╗ ██║   ╚██╗ ██╔╝ ╚══███╔╝ ██╔════╝ ██╔══██╗
\b ███████║ ██╔██╗ ██║ ███████║ ██║    ╚████╔╝    ███╔╝  █████╗   ██████╔╝
\b ██╔══██║ ██║╚██╗██║ ██╔══██║ ██║     ╚██╔╝    ███╔╝   ██╔══╝   ██╔══██╗
\b ██║  ██║ ██║ ╚████║ ██║  ██║ ███████╗ ██║    ███████╗ ███████╗ ██║  ██║
\b ╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝    ╚══════╝ ╚══════╝ ╚═╝  ╚═╝
"""

VERSION = '0.17'


@click.group(commands=[summary_group, db_group, show, parse_group, compare_wafers],
             help=f"{LOGO}\nVersion: {VERSION}")
@click.pass_context
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False))
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
            session = ctx.with_resource(Session(bind=engine, autoflush=False, autocommit=False))
            ctx.obj['session'] = session
            latest = session.query(ClientVersion).one()
            if latest != ClientVersion(version=VERSION):
                logger.warning(
                    f"Your analyzing version seems outdated. Your version {VERSION}, latest available version {latest.version}. Consider upgrading.")
        except OperationalError as e:
            if 'Access denied' in str(e):
                logger.warn(
                    f"Access denied to database. Try again or run {set_db.name} command to set new credentials.")
            else:
                logger.error(f"Error connecting to database: {e}")
                sentry_sdk.capture_exception(e)
            ctx.exit()

        if active_command in (compare_wafers, ):
            chip_states = session.query(ChipState).all()
            ctx.obj['chip_states'] = chip_states
            chip_state_option = next(
                (o for o in active_command.params if o.name == 'chip_state_ids'))
            chip_state_option.type = EntityChoice(chip_states, multiple=chip_state_option.multiple)

