"""Locating of the local credential files and their example templates.

Every credential file used by this project has a tracked example twin with the
same name plus the ``.example`` infix, e.g. ``credentials.json`` and
``credentials.example.json``. The example files only contain placeholder data
and are meant to be copied over the real file and filled in.

The JSON configuration file (``a4s_config.json``) holds all settings of the
project, the other credential files are optional alternatives.
"""

import json
import os

ENV_VARS = {
    "a4s_config.json": "A4S_CONFIG",
    "caldav_credentials.txt": "CALDAV_CREDENTIALS",
}

CONFIG_FILENAME = "a4s_config.json"

DEFAULT_FILTERS = ["StudioTimes"]

_CONFIG_CACHE = {}


class ConfigError(Exception):
    """Raised when the configuration file is missing or incomplete."""


def project_dir():
    """Return the directory that holds the project files."""
    return os.path.dirname(os.path.abspath(__file__))


def example_filename(filename):
    """Return the name of the example template belonging to a credential file."""
    stem, extension = os.path.splitext(filename)
    return f"{stem}.example{extension}"


def real_path(filename, env_var=None):
    """Return the path of a credential file, honouring an environment override."""
    if env_var is None:
        env_var = ENV_VARS.get(os.path.basename(filename))
    if env_var:
        override = os.environ.get(env_var)
        if override:
            return override
    return filename


def example_path(filename):
    """Return the path of the tracked example template for a credential file."""
    return os.path.join(project_dir(), example_filename(os.path.basename(filename)))


def resolve(filename, env_var=None):
    """Return ``(path, is_example)`` for a credential file.

    The real file wins. If it does not exist the tracked example template is
    used instead and flagged as an example.
    """
    path = real_path(filename, env_var)
    if os.path.exists(path):
        return path, False
    example = example_path(path)
    if os.path.exists(example):
        return example, True
    return path, False


def is_placeholder(path):
    """Return True if a credential file still contains the example data."""
    example = example_path(path)
    if not os.path.exists(example):
        return False
    if os.path.abspath(example) == os.path.abspath(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()
        with open(example, "r", encoding="utf-8") as file:
            example_content = file.read()
    except OSError:
        return False
    return content.strip() == example_content.strip()


def warn_example(path, example):
    """Print a hint that the example template is used instead of a real file."""
    print(f"WARNING: '{path}' not found, using the example file '{example}'.")
    print("         Copy it and fill in your own credentials:")
    print(f"           cp {example} {path}")


def warn_placeholder(path):
    """Print a hint that a credential file still holds the placeholder data."""
    example = example_path(path)
    print(f"WARNING: '{path}' still contains the example placeholder data.")
    print(f"         Fill in your own credentials (template: '{example}').")


def config_path(path=None):
    """Return the path of the configuration file."""
    if path:
        return path
    return real_path(CONFIG_FILENAME)


def load_config(path=None, fallback=True, quiet=False):
    """Load the JSON configuration file that holds the settings.

    The file is looked up in this order:
      1. the ``path`` argument
      2. the ``A4S_CONFIG`` environment variable
      3. ``a4s_config.json`` in the current working directory

    If the file does not exist the tracked example template is used instead.
    Set ``fallback`` to False to get an empty configuration instead of the
    template and ``quiet`` to suppress the warnings.
    """
    path = config_path(path)
    if path in _CONFIG_CACHE:
        return _CONFIG_CACHE[path]

    if not os.path.exists(path):
        example = example_path(path)
        if not fallback or not os.path.exists(example):
            if not fallback:
                _CONFIG_CACHE[path] = {}
                return _CONFIG_CACHE[path]
            raise ConfigError(
                f"Configuration file '{path}' not found. "
                f"Copy '{example}' to '{path}' and fill in your credentials."
            )
        if not quiet:
            warn_example(path, example)
        path = example
    elif is_placeholder(path) and not quiet:
        warn_placeholder(path)

    try:
        with open(path, "r", encoding="utf-8") as file:
            config = json.load(file)
    except json.JSONDecodeError as error:
        raise ConfigError(f"Configuration file '{path}' is not valid JSON: {error}") from error

    if not isinstance(config, dict):
        raise ConfigError(f"Configuration file '{path}' must contain a JSON object.")
    _CONFIG_CACHE[path] = config
    return config


def get_setting(name, default=None, cast=None):
    """Return a setting from the environment or from the configuration file.

    The environment variable has the same name in upper case, for example
    ``A4S_SYNC_DAYS``. In the configuration file the setting is looked up in
    the section of its prefix, so ``A4S_SYNC_DAYS`` is the key "sync_days" in
    the "a4s" section and ``CALDAV_CALENDAR_NAME`` is the key "calendar_name"
    in the "caldav" section.
    """
    value = os.environ.get(name.upper())

    if value is None:
        config = load_config(fallback=False, quiet=True)
        prefix, _, key = name.upper().partition("_")
        section = config.get(prefix.lower()) or {}
        if key.lower() in section:
            value = section[key.lower()]
        else:
            for section_name in ("a4s", "caldav"):
                data = config.get(section_name) or {}
                if name.lower() in data:
                    value = data[name.lower()]
                    break

    if value is None:
        value = default

    if cast is bool:
        return str(value).strip().lower() in ("1", "true", "yes", "on")
    if cast:
        return cast(value)
    return value


def get_filters(default=None):
    """Return the list of filters.

    A filter is a subject name that is removed from the calendar, for example
    "StudioTimes". The list is read from the environment variable A4S_FILTERS
    (comma separated) or from the "filters" key of the configuration file. An
    empty list keeps every lesson.
    """
    value = os.environ.get("A4S_FILTERS")
    if value is not None:
        return [part.strip() for part in value.split(",") if part.strip()]

    config = load_config(fallback=False, quiet=True)
    filters = config.get("filters")
    if filters is None:
        filters = (config.get("a4s") or {}).get("filters")
    if filters is None:
        filters = default if default is not None else DEFAULT_FILTERS
    if isinstance(filters, str):
        filters = [filters]
    return [str(entry) for entry in filters]
