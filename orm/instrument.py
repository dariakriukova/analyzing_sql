from sqlalchemy import Column, VARCHAR, SmallInteger

from .base import Base


class Instrument(Base):
    __tablename__ = 'instrument'

    id = Column(SmallInteger, primary_key=True, nullable=False)
    name = Column(VARCHAR(length=100), unique=True)

    def __repr__(self):
        return "<Instrument(name='%s', id='%d')>" % (self.name, self.id)
