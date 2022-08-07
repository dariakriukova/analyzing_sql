import subprocess
from decimal import Decimal
from os.path import exists as file_exists
from time import strftime, localtime
from typing import Union

import click
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from sqlalchemy.orm import Session, joinedload

from orm import IVMeasurement, Wafer, Chip


@click.command(name='summary', help='Summarize data in excel file.')
@click.pass_context
@click.option("-t", "--chips-type", help="Type of the chips to analyze.")
@click.option("-w", "--wafer", "wafer_name", prompt=f"Wafer name", help="Wafer name.")
@click.option("-o", "--output", "file_name", default="summary",
              help="Output file names without extension. Default: summary")
# TODO: add option to select last N measurements to analyze
# TODO: add option to filter measurement stage
def summary(ctx: click.Context, chips_type: Union[str, None], wafer_name: str, file_name: str):
    session: Session = ctx.obj['session']
    if ctx.obj['default_wafer'].name != wafer_name:
        wafer = session.query(Wafer).filter(Wafer.name == wafer_name).first()
    else:
        wafer = ctx.obj['default_wafer']
    query = session.query(IVMeasurement) \
        .filter(IVMeasurement.chip.has(Chip.wafer.__eq__(wafer))) \
        .options(joinedload(IVMeasurement.chip))
    if chips_type is not None:
        query = query.filter(IVMeasurement.chip.has(Chip.type.__eq__(chips_type)))
    else:
        click.echo('No chips type specified. Analyzing all chips.')

    measurements = query.all()
    data = get_data(measurements)

    plot_summary_voltages = list(map(Decimal, ["0.01", "5"]))
    fig = plot_data(measurements, plot_summary_voltages)

    png_file_name = file_name + '.png'
    check_file_exists(png_file_name)
    fig.savefig(png_file_name, dpi=300)
    click.echo(f'Summary data is plotted to {png_file_name}')

    exel_file_name = file_name + '.xlsx'
    check_file_exists(exel_file_name)
    with pd.ExcelWriter(exel_file_name) as writer:
        info = get_info(wafer)
        excel_summary_voltages = list(map(Decimal, ["0.01", "5", "10", "20", "-1"]))
        data[excel_summary_voltages].to_excel(writer, sheet_name='Summary')
        data.to_excel(writer, sheet_name='All')
        info.to_excel(writer, sheet_name='Info')
    click.echo(f'Summary data is saved to {exel_file_name}')


def get_data(measurements: list[IVMeasurement, ...]) -> pd.DataFrame:
    chip_names = {measurement.chip.name for measurement in measurements}
    df = pd.DataFrame(dtype='float64', index=chip_names)
    with click.progressbar(measurements, label='Processing measurements...') as progress:
        for measurement in progress:
            df.loc[measurement.chip.name,
                   measurement.voltage_input] = measurement.anode_current_corrected
    df.columns = df.columns.sort_values()
    return df


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


def get_heat_map_data(measurements: list[IVMeasurement, ...]) -> dict:
    xs, ys = [], []

    for measurement in measurements:
        xs.append(measurement.chip.x_coordinate)
        ys.append(measurement.chip.y_coordinate)

    borders = {'left': min(xs), 'right': max(xs), 'bottom': min(ys), 'top': max(ys)}
    width = borders['right'] - borders['left'] + 1
    height = borders['top'] - borders['bottom'] + 1
    data = np.full((height, width), np.nan)
    for measurement in measurements:
        data[
            measurement.chip.y_coordinate - borders['bottom']][
            measurement.chip.x_coordinate - borders['left']] = measurement.anode_current_corrected
    return {'data': data, 'borders': borders}


def get_outliers_idx(data: np.ndarray, m: float) -> np.ndarray:
    return np.abs(data - np.nanmedian(data)) > m * np.nanstd(data)


def plot_hist(ax: Axes, data: np.ndarray):
    ax.set_ylabel("Number of chips")
    ax.set_xlabel("Anode current [pA]")
    ax.hist(data * 1e12, bins=15)


def plot_heat_map(ax: Axes, measurements: list[IVMeasurement, ...], low, high):
    xs = {measurement.chip.x_coordinate for measurement in measurements}
    ys = {measurement.chip.y_coordinate for measurement in measurements}

    width = max(xs) - min(xs) + 1
    height = max(ys) - min(ys) + 1
    grid = np.full((height, width), np.nan)
    for cell in measurements:
        grid[cell.chip.y_coordinate - min(ys)][
            cell.chip.x_coordinate - min(xs)] = cell.anode_current_corrected

    X = np.linspace(min(xs) - 0.5, max(xs) + 0.5, width + 1)
    Y = np.linspace(min(ys) - 0.5, max(ys) + 0.5, height + 1)
    mesh = ax.pcolormesh(X, Y, grid, cmap='hot', shading='flat', vmin=low, vmax=high)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=0))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, min_n_ticks=0))
    ax.set_ylabel("Y coordinate")
    ax.set_xlabel("X coordinate")
    ax.figure.colorbar(mesh, ax=ax)


def plot_data(measurements: list[IVMeasurement, ...],
              summary_voltages: list[Decimal, ...]) -> Figure:
    fig, axes = plt.subplots(nrows=len(summary_voltages), ncols=2,
                             figsize=(10, 5 * len(summary_voltages)),
                             gridspec_kw=dict(left=0.08, right=0.95, bottom=0.05, top=0.95,
                                              wspace=0.3, hspace=0.35))
    for i, voltage in enumerate(summary_voltages):
        target_measurements = [measurement for measurement in measurements if
                               measurement.voltage_input == voltage]
        data = np.array(
            [measurement.anode_current_corrected for measurement in target_measurements])

        outliers_idx = get_outliers_idx(data, 2)
        if outliers_idx.any():
            # TODO: add including/excluding outliers option
            # TODO: use warning output instead of click.echo
            outlier_chip_names = (outlier.chip.name for outlier in
                                  np.array(target_measurements)[outliers_idx])
            click.echo(
                f'Outliers detected! {", ".join(outlier_chip_names)} are ignored on {voltage}V histogram and heat map color scale')
            data = data[~outliers_idx]

        axes[i][0].set_title(f"{voltage}V")
        plot_hist(axes[i][0], data)

        low, high = data.min(), data.max()
        axes[i][1].set_title(f"{voltage}V")
        plot_heat_map(axes[i][1], target_measurements, low, high)
    return fig