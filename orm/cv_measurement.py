from sqlalchemy import Column, Integer, Float, DECIMAL, ForeignKey, DATETIME, func
from sqlalchemy.orm import relationship

from .base import Base


class CVMeasurement(Base):
    __tablename__ = 'cv_data'

    id = Column(Integer, primary_key=True, nullable=False)
    chip_id = Column(Integer, ForeignKey('chip.id'), nullable=False)
    chip = relationship("Chip", back_populates='cv_measurements')
    chip_state_id = Column(Integer, ForeignKey('chip_state.id'), nullable=False)
    chip_state = relationship("ChipState")
    voltage_input = Column(DECIMAL(precision=10, scale=5), nullable=False)
    capacitance = Column(Float, nullable=False)
    datetime = Column(DATETIME, server_default=func.current_timestamp(), nullable=False, )

    def __repr__(self):
        return "<CVMeasurement(id='%d', chip='%s', capacitance='%.3e')>" % (
            self.id, self.chip, self.capacitance)
