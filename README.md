# All4Schools2Calendar

Syncs the timetable of the All4Schools school portal (Schule Luisenlund) into a CalDAV
calendar.

The script reads the timetable from the school's REST API, turns every lesson into a
calendar event and keeps the calendar in sync: lessons that disappeared are deleted, new
lessons are added.

## Features

- Reads the timetable from the All4Schools API (JWT login, no browser needed)
- Writes the lessons into any CalDAV calendar (Nextcloud, Radicale, …)
- Keeps the calendar in sync: new lessons are created, cancelled lessons are deleted
- Filters out the "Studio Times" lessons (can be enabled again)
- Merges consecutive lessons of the same subject into a single event
- All credentials live in local files or environment variables that are never committed
- Ready to run in a Docker container, the image is built by GitHub Actions

## Requirements

- Python 3.9 or newer
- Access to the school portal (user name and password)
- A CalDAV account

## Setup

```bash
git clone https://github.com/Squirrelsoft-py/All4Schools2Calendar.git
cd All4Schools2Calendar

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the scripts with the interpreter of the virtual environment:

```bash
.venv/bin/python a4s_console.py
```

or activate it once per shell:

```bash
source .venv/bin/activate
```

## Configuration

The scripts read their settings from `a4s_config.json`. Every one of the credential files
has a tracked example template (`*.example.*`) with placeholder data, so the repository is
complete right after cloning:

| Credential file | Example template | Used by | Format |
| --- | --- | --- | --- |
| `a4s_config.json` | `a4s_config.example.json` | all scripts | JSON with all settings |
| `caldav_credentials.txt` | `caldav_credentials.example.txt` | `caldav_api.py` | Optional alternative for the CalDAV login, 3 lines: `url`, `username`, `password` |

The real files are listed in `.gitignore`, only the example templates are tracked. Copy the
template and fill in your own data:

```bash
cp a4s_config.example.json a4s_config.json
```

If the real file is missing, the matching example template is used instead and the program
prints a warning including the `cp` command that creates the real file.

### `a4s_config.json` – the settings

All settings of the project are in one JSON file:

```json
{
    "a4s": {
        "url": "schule.louisenlund.de",
        "username": "example-user",
        "password": "example-password",
        "pin": null,
        "include_studio_times": false
    },
    "caldav": {
        "url": "https://caldav.example.com/calendars/EXAMPLE0000/00000000-0000-0000-0000-000000000000",
        "username": "example-user",
        "password": "example-password",
        "calendar_name": "Stundenplan"
    }
}
```

**`a4s` section** – the school portal:

- `url` is the host name of the school portal. `https://schule.louisenlund.de` and
  `https://schule.louisenlund.de/` are accepted as well – the scheme and the trailing slash
  are stripped automatically.
- `pin` is optional and only needed for accounts with two factor authentication.
- `include_studio_times` keeps the "Studio Times" lessons in the calendar when it is `true`.

**`caldav` section** – the calendar:

- `url` is the URL of the calendar collection, `username` and `password` the credentials.
- `calendar_name` is the name of the CalDAV calendar that is written.

The credentials are resolved in this order:

1. explicit arguments: `all4s_lib.Main(url=..., username=..., password=..., pin=...)`
2. environment variables: `A4S_URL`, `A4S_USERNAME`, `A4S_PASSWORD`, `A4S_PIN`
3. the `a4s` section of `a4s_config.json` (the path can be changed with `A4S_CONFIG`)

### `caldav_credentials.txt` – the CalDAV login (optional)

An alternative to the `caldav` section of the configuration file, three lines with the URL,
the user name and the password:

```
https://caldav.example.com/calendars/EXAMPLE0000/00000000-0000-0000-0000-000000000000
example-user
example-password
```

Line 1 is the URL of the calendar collection, line 2 the user name and line 3 the password
(or app password). The URL differs per provider, for example
`https://cloud.example.com/remote.php/dav/` for Nextcloud or
`https://caldav.example.com/calendars/<user>/<id>` for other providers.

The `caldav` section of `a4s_config.json` and the environment variables have priority over
this file. If neither is set, the server information is asked for interactively and can be
saved to `caldav_credentials.txt`.

### Settings

Every setting can be given as an environment variable or in the configuration file. The
environment variable has the highest priority, the file name is the setting name in upper
case, the key in the configuration file is the name without the prefix:

| Setting | Environment variable | Config file | Default | Description |
| --- | --- | --- | --- | --- |
| School URL | `A4S_URL` | `a4s.url` | – | Host name of the school portal |
| School user | `A4S_USERNAME` | `a4s.username` | – | |
| School password | `A4S_PASSWORD` | `a4s.password` | – | |
| School PIN | `A4S_PIN` | `a4s.pin` | – | Only for two factor authentication |
| CalDAV URL | `CALDAV_URL` | `caldav.url` | – | URL of the calendar collection |
| CalDAV user | `CALDAV_USERNAME` | `caldav.username` | – | |
| CalDAV password | `CALDAV_PASSWORD` | `caldav.password` | – | |
| Calendar name | `CALDAV_CALENDAR_NAME` | `caldav.calendar_name` | `Stundenplan` | The calendar that is written |
| Studio Times filter | `A4S_INCLUDE_STUDIO_TIMES` | `a4s.include_studio_times` | `false` | `true` keeps the "Studio Times" lessons |
| Sync period | `A4S_SYNC_DAYS` | – | `31` | Number of days that are synced |
| Scheduler interval | `SYNC_INTERVAL_HOURS` | – | `24` | Hours between two syncs of the scheduler |

## Usage

| Script | Description |
| --- | --- |
| `a4s_console.py` | Prints the lessons of the current day |
| `a4s_main_caldav.py` | Syncs the next 31 days into the CalDAV calendar |
| `scheduler.py` | Runs the sync in a loop, every `SYNC_INTERVAL_HOURS` hours |

```bash
.venv/bin/python a4s_console.py
.venv/bin/python a4s_main_caldav.py
```

The calendar name and the other settings are taken from the environment or the
configuration file, see [Settings](#settings).

Run the sync regularly, for example every evening with a cron job:

```cron
30 18 * * * cd /path/to/All4Schools2Calendar && .venv/bin/python a4s_main_caldav.py
```

### How the sync works

1. The lessons of the next 31 days are read from the school portal.
2. The lessons of the same subject that follow each other directly are merged into one
   event, "Studio Times" lessons are removed unless `A4S_INCLUDE_STUDIO_TIMES` is `true`.
3. Every event of the calendar in that period is compared with the timetable:
   - events that are no longer part of the timetable are deleted
   - duplicates of the same lesson are deleted
   - lessons without an event are created

Running the sync twice in a row does not change anything.

### How the login works

The school portal is a single page application and has no form login anymore. The
credentials are sent to its REST API:

1. `POST https://<host>/api/Api/Authorization/JwtAuth` with
   `{"Username": ..., "Password": ..., "Pin": ...}` returns a JSON Web Token.
2. Every following request is sent with the header `Authorization: Bearer <token>`.

## Docker

The repository contains a `Dockerfile` and a `docker-compose.yml`. All settings are
passed as environment variables, the credentials are never copied into the image.

```bash
cp .env.example .env
# fill in your own data in .env
docker compose build
docker compose run --rm sync        # sync once
docker compose up -d scheduler      # sync every SYNC_INTERVAL_HOURS hours
```

Without Docker Compose:

```bash
docker build -t all4schools2calendar .
docker run --rm --env-file .env all4schools2calendar                     # sync once
docker run --rm --env-file .env all4schools2calendar a4s_console.py      # print the timetable
docker run -d --name a4s --env-file .env all4schools2calendar scheduler.py
```

The image is built by GitHub Actions on every push to `main` and pushed to the GitHub
container registry:

```bash
docker pull ghcr.io/squirrelsoft-py/all4schools2calendar:latest
```

The workflow is in `.github/workflows/docker.yml`. To use the image from the registry,
change the `image:` line in `docker-compose.yml` and remove the `build:` line.

## Project layout

| File | Description |
| --- | --- |
| `all4s_lib.py` | Access to the school portal: login, user, school and timetable |
| `caldav_api.py` | CalDAV client: read, create and delete events |
| `a4s_files.py` | Locates the credential files and their example templates |
| `a4s_console.py` | Prints the timetable of today |
| `a4s_main_caldav.py` | Syncs the timetable into a CalDAV calendar |
| `scheduler.py` | Runs the sync in a loop |
| `Dockerfile` | Image for the sync |
| `docker-compose.yml` | One shot sync and scheduler |
| `.env.example` | Template for the settings of the container |

## Errors

| Error | Meaning |
| --- | --- |
| `ConfigError` | The configuration file is missing, unreadable or incomplete |
| `LoginError` | The school portal is unreachable or the login was rejected |
| `CalDAVError` | The CalDAV server cannot be reached or does not work as expected |

## Security

- `a4s_config.json`, `caldav_credentials.txt` and `.env` are listed in `.gitignore`, so
  real credentials are never committed.
- Only the `*.example.*` templates are tracked in the repository.
- The `.dockerignore` keeps the credentials out of the build context.
- If you ever committed real credentials, remove them from the history (for example with
  `git filter-repo --replace-text`) and change the affected passwords.
## License

The school timetable and all data of the portal belong to their respective owners. This
script is provided as is, without warranty of any kind.
