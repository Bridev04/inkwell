"""Declarative base with standardised MetaData naming convention.

The naming convention ensures Alembic autogenerate produces stable, deterministic
constraint names across databases rather than relying on provider-generated names.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standard SQLAlchemy naming convention from the docs. Produces names like:
#   ix_users_email, uq_users_username, fk_posts_user_id_users, pk_users
_NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=_NAMING_CONVENTION)
