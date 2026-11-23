# All4Schools2Calendar

[![Docker](https://github.com/Squirrelsoft-py/All4Schools2Calendar/actions/workflows/docker.yml/badge.svg)](https://github.com/Squirrelsoft-py/All4Schools2Calendar/actions/workflows/docker.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Syncs the timetable of the All4Schools school portal into a CalDAV calendar.

The script reads the timetable from the school's REST API, turns every lesson into a
calendar event and keeps the calendar in sync: lessons that disappeared are deleted, new
lessons are added.

It is written for the All4Schools portal (version 3.3) that is used at Schule Luisenlund,
but everything except the portal itself is generic.

## Features

- Reads the timetable from the school portal (JWT login, no browser needed)
- Writes the lessons into any CalDAV calendar (Nextcloud, Radicale, Infomaniak, …)
- Keeps the calendar in sync: new lessons are created, cancelled lessons are deleted
- Filters out lessons you do not want in the calendar, for example the "Studio Times"
- Merges consecutive lessons of the same subject into a single event
- All settings live in one JSON file or in environment variables, the credentials are
  never committed
- Runs in a Docker container, the image is built by GitHub Actions

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

All settings live in one JSON file, `a4s_config.json`. The repository contains a template
with placeholder data, copy it and fill in your own data:

```bash
cp a4s_config.example.json a4s_config.json
```

```json
{
    "a4s": {
        "url": "schule.louisenlund.de",
        "username": "example-user",
        "password": "example-password",
        "pin": null,
        "refresh": 1440
    },
    "caldav": {
        "url": "https://caldav.example.com/calendars/EXAMPLE0000/00000000-0000-0000-0000-000000000000",
        "username": "example-user",
        "password": "example-password",
        "calendar_name": "Stundenplan"
    },
    "filters": [
        "StudioTimes"
    ]
}
```

**`a4s` section** – the school portal:

- `url` is the host name of the school portal. `https://schule.louisenlund.de` and
  `https://schule.louisenlund.de/` are accepted as well – the scheme and the trailing slash
  are stripped automatically.
- `pin` is optional and only needed for accounts with two factor authentication.
- `refresh` is the interval of the scheduler **in minutes**, `1440` is every 24 hours.

**`caldav` section** – the calendar:

- `url` is the URL of the calendar collection, `username` and `password` the credentials.
  The URL differs per provider, for example `https://cloud.example.com/remote.php/dav/`
  for Nextcloud or `https://caldav.example.com/calendars/<user>/<id>` for other providers.
- `calendar_name` is the name of the CalDAV calendar that is written.

**`filters`** – the subjects that are removed from the calendar. The list is prefilled with
`StudioTimes`, so those lessons are never written to the calendar and existing events of
that kind are deleted by the sync. The list can be changed as needed:

```json
"filters": ["StudioTimes", "Pause", "Freizeit"]
```

An empty list keeps every lesson. The comparison ignores case and spaces, so the filter
`StudioTimes` also matches `Studio Times digitalfrei` and `StudioTimes Spezial`.

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
| Filters | `A4S_FILTERS` | `filters` | `StudioTimes` | Subjects that are removed, comma separated in the environment |
| Sync period | `A4S_SYNC_DAYS` | `a4s.sync_days` | `31` | Number of days that are synced |
| Refresh | `A4S_REFRESH` | `a4s.refresh` | `1440` | Minutes between two syncs of the scheduler |

Instead of the `caldav` section, the CalDAV login can also be written into
`caldav_credentials.txt` (three lines: `url`, `username`, `password`). The configuration
file and the environment variables have priority over that file.

## Usage

| Script | Description |
| --- | --- |
| `a4s_console.py` | Prints the lessons of the current day |
| `a4s_main_caldav.py` | Syncs the next 31 days into the CalDAV calendar |
| `scheduler.py` | Runs the sync in a loop, every `a4s.refresh` minutes |

```bash
.venv/bin/python a4s_console.py
.venv/bin/python a4s_main_caldav.py
```

Run the sync regularly, for example every evening with a cron job:

```cron
30 18 * * * cd /path/to/All4Schools2Calendar && .venv/bin/python a4s_main_caldav.py
```

### How the sync works

1. The lessons of the next 31 days are read from the school portal.
2. The lessons of the same subject that follow each other directly are merged into one
   event, the lessons that match a filter (`StudioTimes` by default) are removed.
3. Every event of the calendar in that period is compared with the timetable:
   - events that are no longer part of the timetable are deleted
   - duplicates of the same lesson are deleted
   - lessons without an event are created

Running the sync twice in a row does not change anything.

### How the login works

The school portal is a single page application and has no form login. The credentials are
sent to its REST API:

1. `POST https://<host>/api/Api/Authorization/JwtAuth` with
   `{"Username": ..., "Password": ..., "Pin": ...}` returns a JSON Web Token.
2. Every following request is sent with the header `Authorization: Bearer <token>`.

## Docker

The image is built by GitHub Actions and pushed to the GitHub container registry:

```bash
docker pull ghcr.io/squirrelsoft-py/all4schools2calendar:latest
```

The package is private by default. To pull it without a token, make the package public
(package settings → *Change visibility* → Public), or log in first:

```bash
docker login ghcr.io -u Squirrelsoft-py -p <token with read:packages>
```

### Portainer or Dockge

1. Copy the content of `docker-compose.yml` into the stack editor
2. Replace the values that are marked with `your-...`
3. Start the stack

The compose file is self contained, it needs no `.env` file and no build on the server.

### On the command line

```bash
docker compose up -d                    # sync every a4s.refresh minutes
```

The compose file has a single service, the `scheduler`. It keeps the calendar up to date,
is restarted if it stops and needs no further configuration.

Without Docker Compose:

```bash
docker build -t all4schools2calendar .
docker run --rm --env-file .env all4schools2calendar                     # sync once
docker run --rm --env-file .env all4schools2calendar a4s_console.py      # print the timetable
docker run -d --name a4s --env-file .env all4schools2calendar scheduler.py
```

The `.env.example` holds the same settings for the `docker run` commands.

### Build pipeline

The workflow is in `.github/workflows/docker.yml`:

| Trigger | What happens |
| --- | --- |
| Push to `main` | The image is built and pushed, tagged with `main`, `latest` and the commit sha |
| Push to `dev` | The image is built and pushed, tagged with `dev` and the commit sha |
| Push of a `v*` tag | The image is built and pushed, tagged with the version (`1.2`, `1.2.3`) |
| Pull request | The image is built to check that it still works, nothing is pushed |
| Manual run | The same as a push to `main` |

The image is built for `linux/amd64` and `linux/arm64` (Raspberry Pi), the build cache is
kept between the runs. After the push the image is started once as a smoke test.

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
| `docker-compose.yml` | The scheduler, ready for Portainer and Dockge |
| `.env.example` | Template for the settings of the container |

## Development

Development happens on the `dev` branch, changes are merged into `main` when they work.
Every push to `main` or `dev` builds the container image, pull requests are only built to
check that they still work.

```bash
git checkout dev
# ... change something ...
git commit -am "..."
git push origin dev
```

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

MIT, see [LICENSE](LICENSE).

The school timetable and all data of the portal belong to their respective owners.
