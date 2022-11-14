import click
import pandas as pd
from IPython.display import display
from sqlalchemy.orm import Session, joinedload

from orm import Wafer, Chip
from utils import logger


@click.command(name='wafers', help="""Show all wafers.

\b Batch id is a unique identifier decoding the batch production information.

\b Example 1: PFM2236, where P - PD product, F - Topsil method (Fz), M - medium resistivity
(700-1200ohm-cm), 22 - year, 36 - week, A - parent (if applicable)

\b Example 2: SFM2236, where S - SM product, C - Okmetic method (Cz), H - high resistivity
(>1200ohm-cm), 22 - year, 36 - week, B - split batch (if applicable)
""")
@click.pass_context
def wafers(ctx: click.Context):
    session: Session = ctx.obj['session']
    wafer_entities = session.query(Wafer).order_by(Wafer.record_created_at).options(
        joinedload(Wafer.chips)).all()
    data = pd.DataFrame([wafer.to_series() for wafer in wafer_entities])
    display(data.to_string(col_space=[10, 25, 10, 8]))


@click.command(name='chips', help="Show all chips")
@click.pass_context
@click.option('--limit', help="Limit the number of chips to show", default=100, show_default=True)
def chips(ctx: click.Context, limit: int):
    session: Session = ctx.obj['session']
    chip_entities = session.query(Chip).order_by(Chip.id.desc()).options(
        joinedload(Chip.wafer)).limit(limit).all()
    data = pd.DataFrame([chip.to_series() for chip in chip_entities])
    display(data.to_string(col_space=[10, 10]))
    logger.info(
        f"Showing last {len(chip_entities)} of {session.query(Chip).count()} chips. Use --limit option to increase that number.")


@click.group(commands=[wafers, chips], help="Show data from database")
def show():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('styler.format.formatter', lambda: print('called'))
    pass
