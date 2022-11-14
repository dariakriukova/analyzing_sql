import click
import pandas as pd
from IPython.display import display
from sqlalchemy.orm import Session, joinedload

from orm import Wafer, Chip


@click.command(name='wafers', help="Show all wafers")
@click.pass_context
def wafers(ctx: click.Context):
    session: Session = ctx.obj['session']
    wafer_entities = session.query(Wafer).order_by(Wafer.record_created_at).options(
        joinedload(Wafer.chips)).all()
    data = pd.DataFrame([wafer.to_series() for wafer in wafer_entities])
    display(data.to_string(col_space=[10, 25, 8]))


@click.command(name='chips', help="Show all chips")
@click.pass_context
def chips(ctx: click.Context):
    session: Session = ctx.obj['session']
    chip_entities = session.query(Chip).order_by(Chip.id).options(
        joinedload(Chip.wafer)).all()
    data = pd.DataFrame([chip.to_series() for chip in chip_entities])
    display(data.to_string(col_space=[10, 10]))


@click.group(commands=[wafers, chips], help="Show data from database")
@click.pass_context
def show(ctx: click.Context):
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('styler.format.formatter', lambda: print('called'))
    pass
