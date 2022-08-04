from sqlalchemy import create_engine
import keyring
from iv_measurement import IVMeasurement
from sqlalchemy.orm import sessionmaker, Session
import pandas as pd


def get_summary_data(session: Session, voltages: list[float, ...]) -> pd.DataFrame:
    df = pd.DataFrame(columns=voltages)
    for voltage in voltages:
        measurements = session.query(IVMeasurement).filter_by(voltage_input=voltage).all()
        s = pd.Series(
            {measurement.chip: measurement.anode_current_corrected for measurement in measurements})
        df.loc[:, voltage] = s
    return df


def get_all_data(session: Session) -> pd.DataFrame:
    df = pd.DataFrame()
    measurements = session.query(IVMeasurement).all()
    for measurement in measurements:
        df.loc[measurement.chip, measurement.voltage_input] = measurement.anode_current_corrected
    return df


def main():
    engine = create_engine('mysql://{user}:{pwd}@{server}:3306/{db}'.format(**{
        "user": keyring.get_password("ELFYS_DB", "USER"),
        "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
        "server": "95.217.222.91",
        "db": "elfys"
    }))

    with sessionmaker(bind=engine).begin() as session:
        summary_data = get_summary_data(session, [0.01, 5, 10, 20, -1])
        all_data = get_all_data(session)

    with pd.ExcelWriter('output.xlsx') as writer:
        summary_data.to_excel(writer, sheet_name='Summary')
        all_data.to_excel(writer, sheet_name='All')
        writer.save()


if __name__ == '__main__':
    main()
