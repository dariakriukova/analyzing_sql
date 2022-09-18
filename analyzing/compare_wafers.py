from decimal import Decimal
from itertools import product
from time import strftime

import click
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session, contains_eager

from orm import Wafer, Chip, IVMeasurement
from utils import logger, flatten_options, iv_thresholds


@click.command(name="compare-wafers", help='Compare wafers')
@click.pass_context
@click.option("-w", "--wafers", "wafer_names", type=str, multiple=True, help="Wafers to compare",
              callback=flatten_options)
@click.option("-s", "--chip-state", "chip_state_ids", help="State of the chips to analyze.",
              default=['all'], show_default=True, multiple=True, callback=flatten_options)
@click.option("-o", "--output", "file_name",
              default=lambda: f"wafers-comparison-{strftime('%y%m%d-%H%M%S')}.xlsx",
              help="Output file name.", show_default="wafers-comparison-{datetime}.xlsx")
def compare_wafers(ctx: click.Context, wafer_names: set[str], chip_state_ids: tuple[str],
                   file_name: str):
    session: Session = ctx.obj['session']

    compare_voltages = set(map(Decimal, ("0.01", "10", "20")))
    threshold_voltages = set(map(Decimal, {v for x in iv_thresholds.values() for v in x}))

    wafers_query = session.query(Wafer).filter(Wafer.name.in_(wafer_names))
    wafers = wafers_query.all()

    not_found_wafers = wafer_names - set(wafer.name for wafer in wafers)
    if not_found_wafers:
        logger.warning(f"Wafers not found: {', '.join(not_found_wafers)}")
        wafer_names -= not_found_wafers

    chips_query = session.query(Chip).join(Chip.iv_measurements) \
        .options(contains_eager(Chip.iv_measurements)) \
        .filter(Chip.wafer_id.in_({wafer.id for wafer in wafers})) \
        .filter(IVMeasurement.voltage_input.in_(compare_voltages | threshold_voltages))

    if 'all' not in chip_state_ids:
        chips_query = chips_query.filter(IVMeasurement.chip_state_id.in_(chip_state_ids))
        chip_states = [state for state in ctx.obj['chip_states'] if str(state.id) in chip_state_ids]
    else:
        chip_states = ctx.obj['chip_states']

    chips = chips_query.all()
    if not chips:
        logger.warn('Chips for given filters are not found.')
        return

    chip_state_names = [chip_state.name for chip_state in chip_states]
    chip_types = sorted(set(chip.type for chip in chips), key=lambda t: Chip.get_area(t))
    chip_perimeter_areas = [Chip.get_perimeter(chip_type) / Chip.get_area(chip_type) for chip_type
                            in chip_types]

    index = pd.MultiIndex(levels=[wafer_names, chip_state_names], codes=[[], []],
                          names=['wafer', 'chip'])
    codes = list(zip(*product(range(len(compare_voltages)), range(len(chip_types)))))
    columns = pd.MultiIndex(levels=[sorted(compare_voltages), chip_types, chip_perimeter_areas],
                            codes=[*codes, codes[1]],
                            names=['voltage, V', 'type', 'perimeter/area, mm^-1'])

    leakage_df = pd.DataFrame(index=index, columns=columns)
    leak_density_df = pd.DataFrame(index=index, columns=columns)
    std_df = pd.DataFrame(index=index, columns=columns)

    yield_codes = list(zip(*product(range(len(threshold_voltages)), range(len(chip_types)))))
    yield_columns = pd.MultiIndex(levels=[sorted(threshold_voltages), chip_types],
                                  codes=yield_codes,
                                  names=['voltage, V', 'type'])
    yield_df = pd.DataFrame(index=index, columns=yield_columns)

    for wafer, chip_type in product(wafers, chip_types):
        target_chips = [chip for chip in chips if chip.wafer == wafer and chip.type == chip_type]

        for (voltage, chip_state) in product(compare_voltages, chip_states):
            target_values = get_target_values(chip_state, target_chips, voltage)
            if not target_values:
                continue

            target_values = [value * -1e12 for value in target_values]
            area = Chip.get_area(chip_type)
            perimeter = Chip.get_perimeter(chip_type)
            location = (wafer.name, chip_state.name), (voltage, chip_type, perimeter / area)

            median = np.median(target_values)
            leakage_df.loc[location] = median
            leak_density_df.loc[location] = median / area
            std = np.std(target_values)
            std_df.loc[location] = std

        for (voltage, chip_state) in product(threshold_voltages, chip_states):
            leakage_threshold = iv_thresholds[chip_type].get(str(voltage))
            if leakage_threshold is None:
                continue

            target_values = get_target_values(chip_state, target_chips, voltage)
            if not target_values:
                continue
            location = (wafer.name, chip_state.name), (voltage, chip_type)
            yield_value = np.mean([value > leakage_threshold for value in target_values])
            yield_df.loc[location] = "{:.2%}".format(yield_value)

    with pd.ExcelWriter(file_name) as writer:
        leakage_df.dropna(how="all", axis=0) \
            .dropna(how="all", axis=1).to_excel(writer, sheet_name='Leakage')
        leak_density_df.dropna(how="all", axis=0) \
            .dropna(how="all", axis=1).to_excel(writer, sheet_name='Density')
        std_df.dropna(how="all", axis=0) \
            .dropna(how="all", axis=1).to_excel(writer, sheet_name='Standard Deviation')
        yield_df.dropna(how="all", axis=0) \
            .dropna(how="all", axis=1).to_excel(writer, sheet_name='Yield')
    logger.info(f'Wafers comparison is saved to {file_name}')


def get_target_values(chip_state, target_chips, voltage):
    return [
        iv_measurement.anode_current_corrected or iv_measurement.anode_current
        for chip in target_chips
        for iv_measurement in chip.iv_measurements
        if iv_measurement.voltage_input == voltage
        and iv_measurement.chip_state_id == chip_state.id
    ]
