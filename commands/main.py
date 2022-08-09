import logging

import click
import keyring
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import Wafer, ChipState
from utils import logger
from .set_db import set_db
from .summary import summary


@click.group(commands=[summary, set_db])
@click.pass_context
@click.option("--log-level", default="INFO", help="Log level.", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                                case_sensitive=False))
def main(ctx: click.Context, log_level: str):
    logger.setLevel(log_level)
    if ctx.invoked_subcommand == summary.name:
        try:
            engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(
                **{
                    "user": keyring.get_password("ELFYS_DB", "USER"),
                    "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
                    "server": "95.217.222.91",
                    "db": "elfys"
                }), echo="debug" if logger.getEffectiveLevel() == logging.DEBUG else False)
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
        except OperationalError:
            click.echo(f"Database credentials are not set. Try running {set_db.name}.")
            exit()
