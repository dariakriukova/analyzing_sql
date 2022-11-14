from sqlalchemy import Column, INTEGER, VARCHAR, DATETIME, FetchedValue
from sqlalchemy.orm import relationship

from .base import Base
import pandas as pd


class Wafer(Base):
    __tablename__ = 'wafer'

    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=20))
    chips = relationship("Chip", back_populates='wafer')
    record_created_at = Column(DATETIME, server_default=FetchedValue(), name='record_created_at')

    def to_series(self) -> pd.Series:
        return pd.Series({
            'Name': self.name,
            'Created at': self.record_created_at,
            'Number of chips': len(self.chips)
        })

    def __repr__(self):
        return "<Wafer(name='%s', id='%d')>" % (self.name, self.id)
