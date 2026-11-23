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
- All credentials live in local files that are never committed

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

The scripts expect two local credential files. Every one of them has a tracked example
template (`*.example.*`) with placeholder data, so the repository is complete right after
cloning:

| Credential file | Example template | Used by | Format |
| --- | --- | --- | --- |
| `a4s_config.json` | `a4s_config.example.json` | `all4s_lib.py` | JSON with the school credentials |
| `caldav_credentials.txt` | `caldav_credentials.example.txt` | `caldav_api.py` | 3 lines: `url`, `username`, `password` |

The real files are listed in `.gitignore`, only the example templates are tracked. Copy the
templates and fill in your own data:

```bash
cp a4s_config.example.json         a4s_config.json
cp caldav_credentials.example.txt   caldav_credentials.txt
```

If a real file is missing, the matching example template is used instead and the program
prints a warning including the `cp` command that creates the real file.

### `a4s_config.json` – the school login

```json
{
    "a4s": {
        "url": "schule.louisenlund.de",
        "username": "example-user",
        "password": "example-password",
        "pin": null
    }
}
```

- `url` is the host name of the school portal. `https://schule.louisenlund.de` and
  `https://schule.louisenlund.de/` are accepted as well – the scheme and the trailing slash
  are stripped automatically.
- `pin` is optional and only needed for accounts with two factor authentication.

The credentials are resolved in this order:

1. explicit arguments: `all4s_lib.Main(url=..., username=..., password=..., pin=...)`
2. environment variables: `A4S_URL`, `A4S_USERNAME`, `A4S_PASSWORD`, `A4S_PIN`
3. the `a4s` section of `a4s_config.json` (the path can be changed with `A4S_CONFIG`)

### `caldav_credentials.txt` – the CalDAV login

```
https://caldav.example.com/calendars/EXAMPLE0000/00000000-0000-0000-0000-000000000000
example-user
example-password
```

Line 1 is the URL of the calendar collection, line 2 the user name and line 3 the password
(or app password). The URL differs per provider, for example
`https://cloud.example.com/remote.php/dav/` for Nextcloud or
`https://caldav.example.com/calendars/<user>/<id>` for other providers.

The file path can be changed with the `CALDAV_CREDENTIALS` environment variable. If neither
the real file nor the template is present, the server information is asked for
interactively and can be saved to `caldav_credentials.txt`.

## Usage

| Script | Description |
| --- | --- |
| `a4s_console.py` | Prints the lessons of the current day |
| `a4s_main_caldav.py` | Syncs the next 31 days into the CalDAV calendar "Stundenplan" |
| `a4s_console_one.py` | Console script with its own copy of the library |

```bash
.venv/bin/python a4s_console.py
.venv/bin/python a4s_main_caldav.py
```

The calendar name is set in the scripts, see `calendar_name="Stundenplan"`.

Run the sync regularly, for example every evening with a cron job:

```cron
30 18 * * * cd /path/to/All4Schools2Calendar && .venv/bin/python a4s_main_caldav.py
```

### How the sync works

1. The lessons of the next 31 days are read from the school portal.
2. The lessons of the same subject that follow each other directly are merged into one
   event, "Studio Times" lessons are removed.
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

## Project layout

| File | Description |
| --- | --- |
| `all4s_lib.py` | Access to the school portal: login, user, school and timetable |
| `caldav_api.py` | CalDAV client: read, create and delete events |
| `a4s_files.py` | Locates the credential files and their example templates |
| `a4s_console.py` | Prints the timetable of today |
| `a4s_main_caldav.py` | Syncs the timetable into a CalDAV calendar |
| `a4s_console_one.py` | Console script with its own copy of the library |
| `test.py` | Small helper to test the calendar connection |

## Errors

| Error | Meaning |
| --- | --- |
| `ConfigError` | The configuration file is missing, unreadable or incomplete |
| `LoginError` | The school portal is unreachable or the login was rejected |
| `CalDAVError` | The CalDAV server cannot be reached or does not work as expected |

## Security

- `a4s_config.json` and `caldav_credentials.txt` are listed in `.gitignore`, so real
  credentials are never committed.
- Only the `*.example.*` templates are tracked in the repository.
- If you ever committed real credentials, remove them from the history (for example with
  `git filter-repo --replace-text`) and change the affected passwords.

## License

The school timetable and all data of the portal belong to their respective owners. This
script is provided as is, without warranty of any kind.
