from sqlalchemy import Column, CHAR

from .base import Base


class ClientVersion(Base):
    __tablename__ = 'client_version'
    version = Column(CHAR(length=10), nullable=False, unique=True, primary_key=True)

    def __repr__(self):
        return f"<ClientVersion(version={self.version})>"

    def __eq__(self, other):
        return self.version == other.version
