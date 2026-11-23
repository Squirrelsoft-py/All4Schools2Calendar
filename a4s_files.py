"""Locating of the local credential files and their example templates.

Every credential file used by this project has a tracked example twin with the
same name plus the ``.example`` infix, e.g. ``credentials.json`` and
``credentials.example.json``. The example files only contain placeholder data
and are meant to be copied over the real file and filled in.
"""

import os

ENV_VARS = {
    "a4s_config.json": "A4S_CONFIG",
    "caldav_credentials.txt": "CALDAV_CREDENTIALS",
    "credentials.json": "GOOGLE_CREDENTIALS_FILE",
    "token.json": "GOOGLE_TOKEN_FILE",
}


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
