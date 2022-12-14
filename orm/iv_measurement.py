from sqlalchemy import Column, Integer, Float, VARCHAR, DECIMAL, ForeignKey, DATETIME, func
from sqlalchemy.orm import relationship

from .base import Base


class IVMeasurement(Base):
    __tablename__ = 'iv_data'

    id = Column(Integer, primary_key=True, nullable=False)
    chip_id = Column(
        Integer,
        ForeignKey('chip.id',
                   name='iv_data__chip',
                   ondelete='CASCADE',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    chip = relationship("Chip", back_populates='iv_measurements')
    chip_state_id = Column(
        Integer,
        ForeignKey('chip_state.id',
                   name='iv_data__chip_state',
                   ondelete='RESTRICT',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    chip_state = relationship("ChipState")
    int_time = Column(VARCHAR(length=20))
    temperature = Column(Float)
    voltage_input = Column(DECIMAL(precision=10, scale=5), nullable=False)
    anode_current = Column(Float, nullable=False)
    cathode_current = Column(Float, nullable=True)
    anode_current_corrected = Column(Float)
    datetime = Column(DATETIME, server_default=func.current_timestamp(), nullable=False)

    def __repr__(self):
        return "<IVMeasurement(chip='%s', voltage_input='%s', id='%d')>" % (
            self.chip.name, self.voltage_input, self.id)
