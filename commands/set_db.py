import click
import keyring


@click.command(name='set-db', help='Set database credentials.')
def set_db():
    username = click.prompt('Username')
    keyring.set_password('ELFYS_DB', "USER", username)
    password = click.prompt('Password', hide_input=True)
    keyring.set_password('ELFYS_DB', "PASSWORD", password)
