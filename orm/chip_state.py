from sqlalchemy import Column, Integer, VARCHAR
from sqlalchemy.orm import relationship

from .base import Base


class ChipState(Base):
    __tablename__ = 'chip_state'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=100))
