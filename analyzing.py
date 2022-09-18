import os
import pathlib
import sys

import sentry_sdk

frozen = getattr(sys, 'frozen', False)

sentry_sdk.init(
    dsn="https://11a7db21d98f44e8b5c66bf16c463149@o121277.ingest.sentry.io/6630216",
    traces_sample_rate=1.0,
    environment="pyinstaller" if frozen else "development" if os.getenv("DEV", False) else "pipenv",
)

if frozen:
    os.environ['MPLCONFIGDIR'] = str(pathlib.Path(__file__).parent / 'matplotlib' / 'appdata')

from analyzing import analyzing

if __name__ == '__main__':
    analyzing(windows_expand_args=False)
