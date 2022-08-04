from sqlalchemy import create_engine
import keyring
from iv_measurement import IVMeasurement
from sqlalchemy.orm import sessionmaker

if __name__ == '__main__':
    engine = create_engine('mysql://{user}:{pwd}@{server}:3306/elfys'.format(**{
        "user": keyring.get_password("ELFYS_DB", "USER"),
        "pwd": keyring.get_password("ELFYS_DB", "PASSWORD"),
        "server": "95.217.222.91"
    }))

    Session = sessionmaker(bind=engine)
    session = Session()

    measurements = session.query(IVMeasurement).filter_by(voltage_input=0.01).all()

    ### create summary file
    print(measurements)



engine.dispose()