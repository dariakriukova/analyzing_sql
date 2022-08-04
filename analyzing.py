import keyring
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Query

from orm import IVMeasurement, Wafer, Chip


def get_summary_data(query: Query, voltages: list[float, ...]) -> pd.DataFrame:
    df = pd.DataFrame(columns=voltages)
    for voltage in voltages:
        measurements = query.filter_by(voltage_input=voltage).all()
        s = pd.Series({
            measurement.chip.name: measurement.anode_current_corrected
            for measurement in measurements
        })
        df.loc[:, voltage] = s
    return df


def get_all_data(query: Query) -> pd.DataFrame:
    df = pd.DataFrame()
    measurements = query.all()
    for measurement in measurements:
        df.loc[measurement.chip.name,
               measurement.voltage_input] = measurement.anode_current_corrected
    return df


def main():
    engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(
        **{
            "user": keyring.get_password("ELFYS_DB", "USER"),
            "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
            "server": "95.217.222.91",
            "db": "elfys"
        }))

    with sessionmaker(bind=engine).begin() as session:
        wafer = session.query(Wafer).filter_by(name='BP6').one()
        query = session.query(IVMeasurement) \
            .filter(IVMeasurement.chip.has(type='U'),
                    IVMeasurement.chip.has(Chip.wafer.__eq__(wafer)))

        summary_data = get_summary_data(query, [0.01, 5, 10, 20, -1])
        all_data = get_all_data(query)

    with pd.ExcelWriter('output.xlsx') as writer:
        summary_data.to_excel(writer, sheet_name='Summary')
        all_data.to_excel(writer, sheet_name='All')
        writer.save()


if __name__ == '__main__':
    main()
