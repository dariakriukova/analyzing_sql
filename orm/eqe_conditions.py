from sqlalchemy import Column, Integer, Float, ForeignKey, DATETIME, func, VARCHAR, TEXT
from sqlalchemy.orm import relationship

from .base import Base


class EqeConditions(Base):
    __tablename__ = 'eqe_conditions'

    id = Column(Integer, primary_key=True, nullable=False)
    chip_id = Column(
        Integer,
        ForeignKey('chip.id',
                   name='eqe_conditions__chip',
                   ondelete='CASCADE',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    chip = relationship("Chip", back_populates='eqe_conditions')
    chip_state_id = Column(
        Integer,
        ForeignKey('chip_state.id',
                   name='eqe_conditions__chip_state',
                   ondelete='RESTRICT',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    chip_state = relationship("ChipState")
    measurements = relationship("EqeMeasurement", back_populates='conditions')
    datetime = Column(DATETIME, server_default=func.current_timestamp(), nullable=False)
    bias = Column(Float, nullable=False)
    averaging = Column(Integer, nullable=False)
    dark_current = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False)
    ddc = Column(VARCHAR(100), nullable=True)
    calibration_file = Column(VARCHAR(100), nullable=False)
    session_id = Column(
        Integer,
        ForeignKey('eqe_session.id',
                   name='eqe_conditions__session',
                   ondelete='CASCADE',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    session = relationship("EqeSession", back_populates='eqe_conditions')
    instrument_id = Column(
        Integer,
        ForeignKey('instrument.id',
                   name='eqe_conditions__instrument',
                   ondelete='RESTRICT',
                   onupdate='CASCADE'),
        nullable=True,  # no back_populates, no index
    )
    instrument = relationship("Instrument")
    carrier_id = Column(
        Integer,
        ForeignKey('carrier.id',
                   name='eqe_conditions__carrier',
                   ondelete='RESTRICT',
                   onupdate='CASCADE'),
        nullable=False,  # no back_populates, no index
    )
    carrier = relationship("Carrier")
    comment = Column(TEXT(), nullable=True)

    def __repr__(self):
        return f"<EqeConditions(id={self.id}, datetime={self.datetime}, comment={self.comment})>"
