import logging
import subprocess
import sys
import time
from logging.config import fileConfig

import click
import keyring
from alembic import context
from sqlalchemy import create_engine, engine_from_config

from utils import get_db_url

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from orm import Base

target_metadata = Base.metadata


def save_dump(url, logger: logging.Logger) -> None:
    logger.info("Saving database dump... This may take a while.")

    filename = time.strftime('dump-%Y-%m-%d-%I.sql.gz')

    mysqldump = subprocess.Popen(
        f'docker run --rm mysql:latest \
        mysqldump --no-tablespaces --host={url.host} --port={url.port} \
        --user={url.username} --password={url.password} {url.database}',
        shell=True, text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    mysqldump.stdin.write(url.password)
    gzip = subprocess.Popen(f'gzip -9 > {filename}', shell=True, text=True,
                            stdin=mysqldump.stdout,
                            stderr=subprocess.PIPE)

    mysqldump.wait()
    output, error = mysqldump.communicate()
    if error:
        logger.warning(error)
    if mysqldump.returncode != 0:
        logger.error(f'Error while dumping database')
        sys.exit(mysqldump.returncode)

    output, error = gzip.communicate()
    if error:
        logger.warning(error)
    if gzip.returncode != 0:
        logger.error(f'Error while compressing dump')
        sys.exit(gzip.returncode)

    logger.info(f"Database dumped to {filename}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    if 'production' in context.get_x_argument():
        logger = logging.getLogger("alembic.runtime.migration")
        logger.warning("Running migrations in production mode.")
        click.confirm('Do you want to continue?', abort=True)
        db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                            password=keyring.get_password("ELFYS_DB", "PASSWORD"))
        engine = create_engine(db_url)
        save_dump(engine.url, logger)
    else:
        engine = engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
        )

    with engine.begin() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():  # mysql doesn't support DDL transactions anyway =(
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
