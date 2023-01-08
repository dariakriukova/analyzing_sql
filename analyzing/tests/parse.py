import re
from pathlib import Path

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from analyzing.parse import parse_group, parse_cv, parse_iv, parse_eqe
from analyzing.tests.log_mem_handler import LogMemHandler
from utils import logger


@pytest.fixture
def session():
    db_url = "mysql://root:pwd@127.0.0.1:3306/elfys"
    engine = create_engine(db_url)
    session = Session(bind=engine, autoflush=False, autocommit=False)
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def log_handler():
    logger.setLevel('INFO')
    handler = LogMemHandler()
    logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)


class TestParseGroup:
    def setup_class(self):
        pass

    def teardown_class(self):
        pass

    def test_help_ok(self, runner):
        result = runner.invoke(parse_group, ['--help'])
        assert result.exit_code == 0

    def test_help_text(self, runner):
        result = runner.invoke(parse_group, ['--help'])
        assert re.search(r'cv\s+parse cv', result.output, re.I) is not None
        assert re.search(r'iv\s+parse iv', result.output, re.I) is not None
        assert re.search(r'eqe\s+parse eqe', result.output, re.I) is not None
        assert len(result.output.split('\n')) == 12


class TestParseCV:
    def should_parse_file(self, filename, content):
        assert Path(filename).exists() is False
        assert Path(f"{filename}.parsed").exists() is True
        assert Path(f"{filename}.parsed").read_text() == content

    def should_not_parse_file(self, filename, content):
        assert Path(filename).exists() is True
        assert Path(filename).read_text() == content
        assert Path(f"{filename}.parsed").exists() is False

    def test_help_ok(self, runner):
        result = runner.invoke(parse_cv, ['--help'])
        assert result.exit_code == 0

    def test_parse_dat_file_with_5_columns(self, runner: CliRunner, session, log_handler):
        test_file_name = 'CV AY1 F0142 5_columns.dat'
        test_file_content = Path(f'./data/cv/{test_file_name}').read_text()
        obj = {'session': session}
        with runner.isolated_filesystem():
            with open(test_file_name, 'wt') as f:
                f.write(test_file_content)

            result = runner.invoke(parse_cv, [test_file_name], obj=obj,
                                   input='\n'.join(['', '', '1', '']))

            assert result.exit_code == 0
            logs = log_handler.records
            assert len(logs) == 3
            assert logs[1].message == "Guessed from filename: wafer=AY1, chip=F0142"
            assert logs[
                       2].message == f"File was saved to database and renamed to '{test_file_name}.parsed'"

            self.should_parse_file(test_file_name, test_file_content)

    def test_parse_unknown_table_format(self, runner: CliRunner, session, log_handler):
        test_file_name = 'CV AY1 F0142 unknown_table_format.dat'
        test_file_content = Path(f'./data/cv/{test_file_name}').read_text()
        obj = {'session': session}
        with runner.isolated_filesystem():
            Path(test_file_name).write_text(test_file_content)

            result = runner.invoke(parse_cv, [test_file_name], obj=obj,
                                   input='\n'.join(['', '', '1', '']))
            assert result.exit_code == 0

            assert len(log_handler.records) == 4
            assert log_handler.records[
                       2].message == 'No data was found in given file. Does it use the unusual format?'
            assert log_handler.records[2].levelname == 'WARNING'

            assert log_handler.records[3].message == 'Skipping file...'
            assert log_handler.records[3].levelname == 'INFO'

            self.should_not_parse_file(test_file_name, test_file_content)


class TestParseIV:
    def test_help_ok(self, runner):
        result = runner.invoke(parse_iv, ['--help'])
        assert result.exit_code == 0


class TestParseEQE:
    def test_help_ok(self, runner):
        result = runner.invoke(parse_eqe, ['--help'])
        assert result.exit_code == 0
