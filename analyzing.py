from typing import Union

import click
import keyring
import pandas as pd
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Query, Session

from orm import IVMeasurement, Wafer, Chip

engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(
    **{
        "user": keyring.get_password("ELFYS_DB", "USER"),
        "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
        "server": "95.217.222.91",
        "db": "elfys"
    }))


def get_summary_data(query: Query, voltages: list[float, ...]) -> pd.DataFrame:
    df = pd.DataFrame(columns=voltages)
    for voltage in voltages:
        measurements = query.filter_by(voltage_input=voltage).all()
        s = pd.Series({
            measurement.chip.name: measurement.anode_current_corrected
            for measurement in measurements
        }, dtype='float64')
        df.loc[:, voltage] = s
    return df


def get_all_data(query: Query) -> pd.DataFrame:
    df = pd.DataFrame()
    measurements = query.all()
    for measurement in measurements:
        df.loc[measurement.chip.name,
               measurement.voltage_input] = measurement.anode_current_corrected
    return df


@click.command()
@click.pass_context
@click.option("--chips-type", help="Type of the chips to analyze.")
@click.option("-o", "--output", "filename", default="summary.xlsx",
              help="Output file name. Default: summary.xlsx")
def analyzing(ctx: click.Context, chips_type: Union[str, None], wafer_name: str, filename: str):
    session: Session = ctx.obj['session']
    wafer = session.query(Wafer).filter_by(name=wafer_name).one()
    query = session.query(IVMeasurement) \
        .filter(IVMeasurement.chip.has(Chip.wafer.__eq__(wafer)))
    if chips_type is not None:
        query = query.filter(IVMeasurement.chip.has(Chip.type.__eq__(chips_type)))

    summary_data = get_summary_data(query, [0.01, 5, 10, 20, -1])
    all_data = get_all_data(query)

    with pd.ExcelWriter(filename) as writer:
        summary_data.to_excel(writer, sheet_name='Summary')
        all_data.to_excel(writer, sheet_name='All')
        writer.save()


def main():
    with sessionmaker(bind=engine).begin() as session:
        last_wafer = session.query(Wafer).order_by(desc(Wafer.created_at)).first()
        default_wafer_name = last_wafer.name
        wafer_option = click.Option(("-w", "--wafer", "wafer_name"), default=default_wafer_name,
                                    prompt=f"Wafer name", help="Wafer name.")
        analyzing.params.append(wafer_option)
        analyzing(obj={'session': session})


if __name__ == '__main__':
    main()
