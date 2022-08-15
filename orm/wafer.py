from sqlalchemy import Column, INTEGER, VARCHAR, DATETIME, FetchedValue
from sqlalchemy.orm import relationship

from .base import Base


class Wafer(Base):
    __tablename__ = 'wafer'

    id = Column(INTEGER, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=20))
    chips = relationship("Chip", back_populates='wafer')
    # TODO: rename to record_created_at
    created_at = Column(DATETIME, server_default=FetchedValue())
