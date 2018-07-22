import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base, declared_attr


# http://alembic.zzzcomputing.com/en/latest/naming.html
# NAMING_CONVENTION = {
#     "ix": "ix_%(column_0_label)s",
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(constraint_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }


class BaseModel:
    """Base sqlalchemy model."""
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


# Meta = sa.MetaData(naming_convention=NAMING_CONVENTION)
Meta = sa.MetaData()
Base = declarative_base(cls=BaseModel, metadata=Meta)
