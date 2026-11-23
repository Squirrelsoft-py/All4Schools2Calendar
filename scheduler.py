"""Runs the calendar sync in a loop, for example inside a container.

The interval is taken from the environment variable SYNC_INTERVAL_HOURS
(default 24 hours).
"""

import datetime
import os
import time

import a4s_main_caldav

INTERVAL_HOURS = float(os.environ.get("SYNC_INTERVAL_HOURS", 24))


def main():
    while True:
        try:
            a4s_main_caldav.main()
        except Exception as error:
            # A failed sync must not stop the scheduler, the next run tries again
            print(f"Sync failed: {error}")

        next_sync = datetime.datetime.now() + datetime.timedelta(hours=INTERVAL_HOURS)
        print(f"Next sync at {next_sync.isoformat()}")
        time.sleep(INTERVAL_HOURS * 3600)


if __name__ == "__main__":
    main()
