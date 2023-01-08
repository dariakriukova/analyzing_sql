import os
import subprocess
import time
from typing import Optional

import click
import keyring
import sqlalchemy.engine as engine
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from utils import get_db_url, logger


@click.command(name='set', help='Set database credentials.')
def set_db():
    username = click.prompt('Username')
    password = click.prompt('Password')

    db_url = get_db_url(username=username, password=password)
    engine = create_engine(db_url)
    try:
        engine.connect().close()
        keyring.set_password('ELFYS_DB', "PASSWORD", password)
        keyring.set_password('ELFYS_DB', "USER", username)
        logger.info('Database credentials are set. Now you can use analyzer commands.')
    except OperationalError:
        logger.warn(
            'Cannot connect to the database with given credentials. Saving credentials is rejected.')


@click.command(name='dump', help='Dump database to .sql.gz file.')
@click.pass_context
@click.option('--limit', '-l', type=int, help='Limit number of rows in each table.')
def dump_db(ctx: click.Context, limit: Optional[int]):
    try:
        db_url = engine.create_engine(ctx.parent.parent.params['db_url']).url
    except (KeyError, AttributeError):
        db_url = get_db_url(username=keyring.get_password("ELFYS_DB", "USER"),
                            password=keyring.get_password("ELFYS_DB", "PASSWORD"))

    logger.info("Saving database dump... This may take a while.")

    dump_file = f'dump_{time.strftime("%Y%m%d_%H%M%S")}.sql.gz'
    command = f'docker run --rm -i mysql:latest \
        mysqldump --no-tablespaces --host={db_url.host} --port={db_url.port} \
        --user={db_url.username} -p {db_url.database}'
    if limit:
        command = f'{command} --where="1 limit {limit}"'
    mysqldump = subprocess.Popen(
        command,
        shell=True, text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    mysqldump.stdin.write(db_url.password + os.linesep)
    mysqldump.stdin.flush()

    gzip = subprocess.Popen(f'gzip -9 > {dump_file}', shell=True, text=True,
                            stdin=mysqldump.stdout,
                            stderr=subprocess.PIPE)

    mysqldump.wait()
    output, error = mysqldump.communicate()
    error = error.replace('Enter password: ', '')
    if error:
        logger.warning(error)
    if mysqldump.returncode != 0:
        logger.error(f'Error while dumping database')
        ctx.exit(mysqldump.returncode)

    output, error = gzip.communicate()
    if error:
        logger.warning(error)
    if gzip.returncode != 0:
        logger.error(f'Error while compressing dump')
        ctx.exit(gzip.returncode)

    logger.info(f"Database dumped to {dump_file}")
    return db_url


@click.group(name="db", help="Set of commands to manage related database",
             commands=[set_db, dump_db])
def db_group():
    ...
