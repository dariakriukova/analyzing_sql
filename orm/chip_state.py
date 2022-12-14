from sqlalchemy import Column, Integer, VARCHAR

from .base import Base


class ChipState(Base):
    __tablename__ = 'chip_state'

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=100), nullable=False, unique=True,
                  comment="Chip state is used to indicate the state of corresponding chip during measurement (iv_data)")

    def __repr__(self):
        return f"<ChipState(id={self.id}, name='{self.name}')>"
