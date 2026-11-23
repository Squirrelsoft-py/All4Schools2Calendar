# Build:  docker build -t all4schools2calendar .
# Run:    docker run --rm --env-file .env all4schools2calendar
#
# The settings are read from the environment, see .env.example and README.md.

# syntax=docker/dockerfile:1
# check=skip=SecretsUsedInArgOrEnv

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Europe/Berlin \
    A4S_CONFIG=/config/a4s_config.json \
    CALDAV_CREDENTIALS=/config/caldav_credentials.txt

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

COPY all4s_lib.py a4s_files.py caldav_api.py ./
COPY a4s_console.py a4s_main_caldav.py scheduler.py ./
COPY a4s_config.example.json caldav_credentials.example.txt ./

RUN useradd --create-home --uid 1000 a4s \
    && mkdir -p /config \
    && chown -R a4s:a4s /app /config
USER a4s

# The command can be changed, for example "a4s_console.py" or "scheduler.py"
ENTRYPOINT ["python"]
CMD ["a4s_main_caldav.py"]
