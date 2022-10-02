from sqlalchemy import Column, Integer, Float, VARCHAR, DECIMAL, ForeignKey, DATETIME, FetchedValue
from sqlalchemy.orm import relationship

from .base import Base


class IVMeasurement(Base):
    __tablename__ = 'iv_data'

    id = Column(Integer, primary_key=True, nullable=False)
    chip_id = Column(Integer, ForeignKey('chip.id'), nullable=False)
    chip = relationship("Chip", back_populates='iv_measurements')
    chip_state_id = Column(Integer, ForeignKey('chip_state.id'), nullable=False)
    chip_state = relationship("ChipState")
    int_time = Column(VARCHAR(length=20))
    temperature = Column(Float)
    voltage_input = Column(DECIMAL(precision=10, scale=5), nullable=False)
    anode_current = Column(Float, nullable=False)
    cathode_current = Column(Float, nullable=True)
    anode_current_corrected = Column(Float)
    datetime = Column(DATETIME, server_default=FetchedValue())

    def __repr__(self):
        return "<IVMeasurement(chip='%s', voltage_input='%s', id='%d')>" % (
            self.chip.name, self.voltage_input, self.id)
