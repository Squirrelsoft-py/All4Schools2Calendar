"""Runs the calendar sync in a loop, for example inside a container.

The interval is taken from the setting "refresh" (in minutes) of the
configuration file or from the environment variable A4S_REFRESH.
"""

import datetime
import signal
import sys
import time

import all4s_lib
import a4s_main_caldav

INTERVAL_MINUTES = float(all4s_lib.get_setting("A4S_REFRESH", 1440, cast=float))


def stop(signum, frame):
    """Stop the scheduler cleanly when the container is stopped or updated."""
    print("Stopped")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    while True:
        try:
            a4s_main_caldav.main()
        except Exception as error:
            # A failed sync must not stop the scheduler, the next run tries again
            print(f"Sync failed: {error}")

        next_sync = datetime.datetime.now() + datetime.timedelta(minutes=INTERVAL_MINUTES)
        print(f"Next sync at {next_sync.isoformat()}")
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
