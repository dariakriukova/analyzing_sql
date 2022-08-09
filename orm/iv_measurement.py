from sqlalchemy import Column, Integer, Float, VARCHAR, DECIMAL, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class IVMeasurement(Base):
    __tablename__ = 'iv_data'

    id = Column(Integer, primary_key=True, nullable=False)
    chip_id = Column(Integer, ForeignKey('chip.id'))
    chip = relationship("Chip", back_populates='iv_measurements')
    chip_state_id = Column(Integer, ForeignKey('chip_state.id'))
    chip_state = relationship("ChipState", back_populates='iv_measurements')
    int_time = Column(VARCHAR(length=20))
    temperature = Column(Float)
    voltage_input = Column(DECIMAL(precision=10, scale=5))
    anode_current = Column(Float)
    cathode_current = Column(Float)
    anode_current_corrected = Column(Float)

    def __repr__(self):
        return "<IVMeasurement(wafer='%s', chip='%s', id='%d')>" % (
            self.wafer, self.chip, self.id)
