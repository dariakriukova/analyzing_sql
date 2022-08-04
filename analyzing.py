import subprocess
from decimal import Decimal
from time import strftime, localtime
from typing import Union

import click
import keyring
import pandas as pd
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Query, Session

from orm import IVMeasurement, Wafer, Chip


def get_summary_data(query: Query, voltages: list[str, ...]) -> pd.DataFrame:
    df = pd.DataFrame(columns=voltages)
    measurements = query.filter(IVMeasurement.voltage_input.in_(voltages)).all()
    for voltage in voltages:
        s = pd.Series({
            measurement.chip.name: measurement.anode_current_corrected
            for measurement in measurements if measurement.voltage_input == Decimal(voltage)
        }, dtype='float64')
        df.loc[:, voltage] = s
    return df


def get_all_data(query: Query) -> pd.DataFrame:
    measurements = query.all()
    df = pd.DataFrame()
    for measurement in measurements:
        df.loc[measurement.chip.name,
               measurement.voltage_input] = measurement.anode_current_corrected
    return df


def get_info_data(wafer: Wafer) -> pd.Series:
    try:
        process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], shell=False,
                                   stdout=subprocess.PIPE)
        git_hash = process.communicate()[0].strip()
    except FileNotFoundError:
        git_hash = 'unknown'
    format_date = strftime("%A, %d %b %Y", localtime())

    return pd.Series({
        'Wafer': wafer.name,
        'Summary generation data': format_date,
        'Analyzer git hash': git_hash
    })


@click.command()
@click.pass_context
@click.option("-t", "--chips-type", help="Type of the chips to analyze.")
@click.option("-w", "--wafer", "wafer_name", prompt=f"Wafer name", help="Wafer name.")
@click.option("-o", "--output", "filename", default="summary.xlsx",
              help="Output file name. Default: summary.xlsx")
def analyzing(ctx: click.Context, chips_type: Union[str, None], wafer_name: str, filename: str):
    session: Session = ctx.obj['session']
    wafer = session.query(Wafer).filter_by(name=wafer_name).one()
    query = session.query(IVMeasurement) \
        .filter(IVMeasurement.chip.has(Chip.wafer.__eq__(wafer)))
    if chips_type is not None:
        query = query.filter(IVMeasurement.chip.has(Chip.type.__eq__(chips_type)))

    summary_data = get_summary_data(query, ["0.01", "5", "10", "20", "-1"])
    all_data = get_all_data(query)
    info_data = get_info_data(wafer)

    with pd.ExcelWriter(filename) as writer:
        summary_data.to_excel(writer, sheet_name='Summary')
        all_data.to_excel(writer, sheet_name='All')
        info_data.to_excel(writer, sheet_name='Info')


def main():
    engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(
        **{
            "user": keyring.get_password("ELFYS_DB", "USER"),
            "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
            "server": "95.217.222.91",
            "db": "elfys"
        }))
    with sessionmaker(bind=engine).begin() as session:
        last_wafer = session.query(Wafer).order_by(desc(Wafer.created_at)).first()
        default_wafer_name = last_wafer.name
        wafer_option = next((o for o in analyzing.params if o.name == 'wafer_name'))
        wafer_option.default = default_wafer_name
        analyzing(obj={'session': session})


if __name__ == '__main__':
    main()
