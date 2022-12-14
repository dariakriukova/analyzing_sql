from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class EqeMeasurement(Base):
    __tablename__ = 'eqe_data'

    id = Column(Integer, primary_key=True, nullable=False)
    wavelength = Column(Integer, nullable=False)
    light_current = Column(Float, nullable=False)
    dark_current = Column(Float, nullable=True)
    std = Column(Float, nullable=True)
    eqe = Column(Float, nullable=True)
    responsivity = Column(Float, nullable=True)
    conditions_id = Column(
        Integer,
        ForeignKey('eqe_conditions.id',
                   name='eqe_data__conditions',
                   ondelete='CASCADE',
                   onupdate='CASCADE'),
        nullable=False,
        index=True,
    )
    conditions = relationship("EqeConditions", back_populates='measurements')

    def __repr__(self):
        return "<EqeMeasurement(id='%d')>" % (self.id)
