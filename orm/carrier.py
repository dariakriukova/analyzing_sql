from sqlalchemy import Column, VARCHAR, SmallInteger

from .base import Base


class Carrier(Base):
    __tablename__ = 'carrier'

    id = Column(SmallInteger, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=100), nullable=False, unique=True)

    def __repr__(self):
        return f"<Carrier(id={self.id} name='{self.name}')>"
