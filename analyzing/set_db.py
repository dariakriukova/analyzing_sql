import click
import keyring
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from utils import get_db_url, logger


@click.command(name='set-db', help='Set database credentials.')
def set_db():
    username = click.prompt('Username')
    password = click.prompt('Password')

    db_url = get_db_url(username=username, password=password)
    engine = create_engine(db_url)
    try:
        engine.connect().close()
        keyring.set_password('ELFYS_DB', "PASSWORD", password)
        keyring.set_password('ELFYS_DB', "USER", username)
        logger.info('Database credentials are set. Now you can run the summary command.')
    except OperationalError:
        logger.error(
            'Cannot connect to the database with given credentials. Saving credentials is rejected.')
