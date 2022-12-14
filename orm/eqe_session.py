from sqlalchemy import Column, Integer, TEXT, DATE, text
from sqlalchemy.orm import relationship

from .base import Base


class EqeSession(Base):
    __tablename__ = 'eqe_session'

    id = Column(Integer, primary_key=True, nullable=False)
    date = Column(DATE, server_default=text("(CURRENT_DATE)"), nullable=False)
    eqe_conditions = relationship("EqeConditions", back_populates='session')

    def __repr__(self):
        return f"<EqeSession(id={self.id}, date={self.date})>"
