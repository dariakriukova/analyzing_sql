import pandas as pd
from sqlalchemy import Column, Integer, CHAR, VARCHAR, ForeignKey, FetchedValue
from sqlalchemy.orm import relationship

from .base import Base


class Chip(Base):
    __tablename__ = 'chip'

    chip_sizes = {
        'X': (1, 1),
        'Y': (2, 2),
        'U': (5, 5),
        'V': (10, 10),
        'F': (2.56, 1.25),
        'G': (1.4, 3.25),
    }

    id = Column(Integer, primary_key=True, nullable=False)
    wafer_id = Column(Integer, ForeignKey('wafer.id'))
    wafer = relationship("Wafer", back_populates='chips')
    name = Column(VARCHAR(length=20))
    type = Column(CHAR(length=1), server_default=FetchedValue())
    iv_measurements = relationship("IVMeasurement", back_populates='chip')
    cv_measurements = relationship("CVMeasurement", back_populates='chip')

    @property
    def x_coordinate(self):
        return int(self.name[1:3])

    @property
    def y_coordinate(self):
        return int(self.name[3:5])

    @property
    def area(self):
        return Chip.get_area(self.type)

    def to_series(self) -> pd.Series:
        return pd.Series({
            'Name': self.name,
            'Wafer': self.wafer.name,
        })

    @staticmethod
    def get_area(chip_type: str) -> float:
        return Chip.chip_sizes[chip_type][0] * Chip.chip_sizes[chip_type][1]

    @staticmethod
    def get_perimeter(chip_type: str) -> float:
        return (Chip.chip_sizes[chip_type][0] + Chip.chip_sizes[chip_type][1]) * 2
