from sqlalchemy import Column, Integer, CHAR, VARCHAR, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Chip(Base):
    __tablename__ = 'chip'

    id = Column(Integer, primary_key=True, nullable=False)
    wafer_id = Column(Integer, ForeignKey('wafer.id'))
    wafer = relationship("Wafer", back_populates='chips')
    name = Column(VARCHAR(length=20))
    type = Column(CHAR(length=1))
    iv_measurements = relationship("IVMeasurement", back_populates='chip')

    @property
    def x_coordinate(self):
        return int(self.name[1:3])

    @property
    def y_coordinate(self):
        return int(self.name[3:5])
