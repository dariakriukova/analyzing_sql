from sqlalchemy import Column, INTEGER, VARCHAR, DATETIME
from sqlalchemy.orm import relationship

from .base import Base


class Wafer(Base):
    __tablename__ = 'wafer'

    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=20))
    chips = relationship("Chip", back_populates='wafer')
    created_at = Column(DATETIME)
