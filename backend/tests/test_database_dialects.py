from sqlalchemy.dialects import mysql, postgresql
from sqlalchemy.schema import CreateTable
from pydantic import ValidationError

from app.config import Settings
from app.db import Base
import app.models  # noqa: F401


def test_schema_compiles_for_mysql_and_postgres():
    """The assignment accepts MySQL/Postgres, so keep both dialects buildable."""
    assert Base.metadata.sorted_tables
    for dialect in (mysql.dialect(), postgresql.dialect()):
        ddl = [str(CreateTable(table).compile(dialect=dialect)) for table in Base.metadata.sorted_tables]
        assert len(ddl) == len(Base.metadata.sorted_tables)
        assert all("CREATE TABLE" in statement for statement in ddl)


def test_runtime_database_url_rejects_sqlite():
    try:
        Settings(database_url="sqlite:///aivoa_crm.db")
    except ValidationError as exc:
        assert "MySQL or PostgreSQL" in str(exc)
    else:
        raise AssertionError("SQLite DATABASE_URL should not be accepted for this assignment.")
