import click
import keyring
from sqlalchemy import create_engine, desc
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from orm import Wafer
from .set_db import set_db
from .summary import summary


@click.group(commands=[summary, set_db])
@click.pass_context
def main(ctx: click.Context):
    if ctx.invoked_subcommand == 'summary':
        try:
            engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(
                **{
                    "user": keyring.get_password("ELFYS_DB", "USER"),
                    "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
                    "server": "95.217.222.91",
                    "db": "elfys"
                }))
            session = Session(bind=engine)
            ctx.with_resource(session)
            last_wafer = session.query(Wafer).order_by(desc(Wafer.created_at)).first()
            default_wafer_name = last_wafer.name
            wafer_option = next((o for o in summary.params if o.name == 'wafer_name'))
            wafer_option.default = default_wafer_name
            ctx.obj = {'session': session, 'default_wafer': last_wafer}
        except OperationalError:
            click.echo(f"Database credentials are not set. Try running {set_db.name}.")
            exit()
        except Exception as e:
            click.echo(e)
            click.echo('Something went wrong. Try again.')
            exit()
