from sqlalchemy import Column, Integer, Float, VARCHAR, DECIMAL

from sqlalchemy.orm import declarative_base

Base = declarative_base()


class IVMeasurement(Base):
    __tablename__ = 'iv_data'
    id = Column(Integer, primary_key=True, nullable=False)
    wafer = Column(VARCHAR(length=20))
    chip = Column(VARCHAR(length=20))
    int_time = Column(VARCHAR(length=20))
    temperature = Column(Float)
    voltage_input = Column(DECIMAL(precision=10, scale=5))
    anode_current = Column(Float)
    cathode_current = Column(Float)
    anode_current_corrected = Column(Float)

    def __repr__(self):
        return "<IVMeasurement(wafer='%s', chip='%s', id='%d')>" % (
            self.wafer, self.chip, self.id)
