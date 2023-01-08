## Installation

1. Run the following command in PowerShell to install analyzer.exe
   ```powershell
   Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/dariakriukova/analyzing_sql/main/install.ps1" -OutFile "./install-analyzing.ps1"; &"./install-analyzing.ps1"; & rm "install-analyzing.ps1"
   ```
2. Restart PowerShell and run `analyzer.exe`


## Development

1. Install pyenv:
    - [Instructions](https://pyenv-win.github.io/pyenv-win/#installation) for windows
    - [Instructions](https://github.com/pyenv/pyenv#installation) for Linux and MacOS
2. Install PipEnv python module
   `pip install --user pipenv`
3. Clone this repository
   `git clone https://github.com/dariakriukova/analyzing_sql.git`
4. Navigate to the project directory
   `cd analyzing_sql`
5. Install python dependencies
   `python -m pipenv install --dev`
     <details><summary>Expected output (on MacOS)</summary>
     <pre>
     Creating a virtualenv for this project...
     Pipfile: ~/projects/analyzing_sql/Pipfile
     Using ~/.pyenv/versions/3.10.1/bin/python3 (3.10.1) to create virtualenv...
     ⠦ Creating virtual environment...created virtual environment
     ✔ Successfully created virtual environment! 
     Virtualenv location: ~/.local/share/virtualenvs/analyzing_sql-jP6szl67
     Installing dependencies from Pipfile.lock (f950b0)...
     🐍   ▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉▉ 13/13 — 00:00:06
     Ignoring pywin32: markers 'sys_platform == "win32"' don't match your environment
     To activate this project's virtualenv, run pipenv shell.
     Alternatively, run a command inside the virtualenv with pipenv run.
        </pre></details>
6. Activating the new virtual environment
   `python -m pipenv shell`

## Usage

Running the program: `python analyzing.exe --help`

```
   █████╗  ███╗   ██╗  █████╗  ██╗   ██╗   ██╗ ███████╗ ███████╗ ██████╗ 
  ██╔══██╗ ████╗  ██║ ██╔══██╗ ██║   ╚██╗ ██╔╝ ╚══███╔╝ ██╔════╝ ██╔══██╗ 
  ███████║ ██╔██╗ ██║ ███████║ ██║    ╚████╔╝    ███╔╝  █████╗   ██████╔╝ 
  ██╔══██║ ██║╚██╗██║ ██╔══██║ ██║     ╚██╔╝    ███╔╝   ██╔══╝   ██╔══██╗ 
  ██║  ██║ ██║ ╚████║ ██║  ██║ ███████╗ ██║    ███████╗ ███████╗ ██║  ██║ 
  ╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚══════╝ ╚═╝    ╚══════╝ ╚══════╝ ╚═╝  ╚═╝

  Version: 0.17

Options:
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  Log level.  [default: INFO]
  --db-url TEXT                   Database URL.
  --help                          Show this message and exit.

Commands:
  compare-wafers  Compare wafers
  db              Set of commands to manage related database
  parse           Parse files with measurements and save to database
  show            Show data from database
  summary         Group of command to analyze and summaryze the data
```

### TODO

- [ ] Add instrument to configs and measurement relations
