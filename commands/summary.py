import subprocess
from decimal import Decimal
from os.path import exists as file_exists
from time import strftime, localtime
from typing import Union

import click
import pandas as pd
from sqlalchemy.orm import Session

from orm import IVMeasurement, Wafer, Chip


@click.command(name='summary', help='Summarize data in excel file.')
@click.pass_context
@click.option("-t", "--chips-type", help="Type of the chips to analyze.")
@click.option("-w", "--wafer", "wafer_name", prompt=f"Wafer name", help="Wafer name.")
@click.option("-o", "--output", "file_name", default="summary.xlsx",
              help="Output file name. Default: summary.xlsx")
# TODO: add option to select last N measurements to analyze
# TODO: add option to filter measurement stage
def summary(ctx: click.Context, chips_type: Union[str, None], wafer_name: str, file_name: str):
    check_file_exists(file_name)
    session: Session = ctx.obj['session']
    wafer = session.query(Wafer).filter(Wafer.name == wafer_name).first()
    query = session.query(IVMeasurement) \
        .filter(IVMeasurement.chip.has(Chip.wafer.__eq__(wafer)))
    if chips_type is not None:
        query = query.filter(IVMeasurement.chip.has(Chip.type.__eq__(chips_type)))
    else:
        click.echo('No chips type specified. Analyzing all chips.')

    measurements = query.all()
    data = get_frames(measurements, list(map(Decimal, ["0.01", "5", "10", "20", "-1"])))
    info = get_info(wafer)

    with pd.ExcelWriter(file_name) as writer:
        data['summary'].to_excel(writer, sheet_name='Summary')
        data['all'].to_excel(writer, sheet_name='All')
        info.to_excel(writer, sheet_name='Info')
    click.echo(f'Summary data is saved to {file_name}')


def get_frames(measurements: list[IVMeasurement, ...], voltages: list[Decimal, ...]) \
        -> dict[str, pd.DataFrame]:
    all_df = pd.DataFrame(dtype='float64')
    summary_df = pd.DataFrame(columns=voltages, dtype='float64')
    # click.echo(f'Got {len(measurements)} measurements.')
    with click.progressbar(measurements, label='Processing measurements...') as progress:
        for measurement in progress:
            all_df.loc[measurement.chip.name,
                       measurement.voltage_input] = measurement.anode_current_corrected
            if measurement.voltage_input in voltages:
                summary_df.loc[measurement.chip.name,
                               measurement.voltage_input] = measurement.anode_current_corrected
    all_df.columns = all_df.columns.sort_values()
    return {'all': all_df, 'summary': summary_df}


def get_info(wafer: Wafer) -> pd.Series:
    try:
        process = subprocess.Popen(['git', 'rev-parse', 'HEAD'], shell=False,
                                   stdout=subprocess.PIPE)
        git_hash = process.communicate()[0].strip()
    except FileNotFoundError:
        git_hash = 'unknown'
    format_date = strftime("%A, %d %b %Y", localtime())

    return pd.Series({
        'Wafer': wafer.name,
        'Summary generation date': format_date,
        'Analyzer git hash': git_hash
        # TODO: add measurement stage
    })


def check_file_exists(file_name: str):
    while True:
        if file_exists(file_name):
            ok = click.prompt(f'File {file_name} already exists. Overwrite?', default='y',
                              type=click.Choice(['y', 'n']))
            if ok == 'n':
                file_name = click.prompt(f'Enter new file name')
            else:
                break
        else:
            break
