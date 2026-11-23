import datetime
import caldav
from caldav.elements import dav, cdav
import os.path
import getpass

import a4s_files

CREDENTIALS_FILENAME = "caldav_credentials.txt"


class CalDAVError(Exception):
    """Raised when the CalDAV server cannot be reached or does not work as expected."""


class Main:
    def authenticate_caldav(self):
        creds = None
        # Check if credentials file exists, fall back to the example template
        path, is_example = a4s_files.resolve(CREDENTIALS_FILENAME)
        if is_example:
            a4s_files.warn_example(a4s_files.real_path(CREDENTIALS_FILENAME), path)
        elif a4s_files.is_placeholder(path):
            a4s_files.warn_placeholder(path)

        if os.path.exists(path):
            with open(path, 'r') as file:
                lines = file.readlines()
                if len(lines) >= 3:
                    url = lines[0].strip()
                    username = lines[1].strip()
                    password = lines[2].strip()
                    creds = {
                        'url': url,
                        'username': username,
                        'password': password
                    }
        
        # If no valid credentials, prompt for login
        if not creds:
            print("Please enter your CalDAV server information:")
            url = input("CalDAV server URL (e.g. https://example.com/caldav/): ")
            username = input("Username: ")
            password = getpass.getpass("Password: ")
            
            creds = {
                'url': url,
                'username': username,
                'password': password
            }
            
            # Save credentials
            save = input("Save credentials for future use? (y/n): ")
            if save.lower() == 'y':
                target = a4s_files.real_path(CREDENTIALS_FILENAME)
                with open(target, 'w') as file:
                    file.write(f"{url}\n{username}\n{password}")
        
        return creds

    def __init__(self, calendar_id="", calendar_name="", t_start=datetime.datetime.now(), t_end=datetime.datetime.now() + datetime.timedelta(days=365)):
        self.start_time = t_start
        self.end_time = t_end
        self.creds = self.authenticate_caldav()
        
        # Connect to the CalDAV server
        try:
            self.client = caldav.DAVClient(
                url=self.creds['url'],
                username=self.creds['username'],
                password=self.creds['password']
            )

            # Get principal
            self.principal = self.client.principal()
        except Exception as error:
            raise CalDAVError(
                f"Could not connect to the CalDAV server '{self.creds['url']}': {error}\n"
                "Check the url, username and password in 'caldav_credentials.txt' "
                "(template: 'caldav_credentials.example.txt')."
            ) from error
        
        # Get calendar by name or ID if provided
        if calendar_name != "":
            self.calendar = self.get_calendar_by_name(calendar_name)
            if self.calendar:
                print(f"Using calendar: {calendar_name}")
            else:
                print(f"Calendar '{calendar_name}' not found.")
                self.select_default_calendar()
        elif calendar_id != "":
            try:
                self.calendar = self.principal.calendar(cal_id=calendar_id)
                print(f"Using calendar with ID: {calendar_id}")
            except:
                print(f"Calendar with ID '{calendar_id}' not found.")
                self.select_default_calendar()
        else:
            print("\nWARNING: Not given calendar name or id, listing available calendars:")
            self.select_default_calendar()
    
    def select_default_calendar(self):
        """Display available calendars and select the first one as default"""
        calendars = self.list_calendars()
        
        if not calendars:
            raise Exception("No calendars found in this account")
        
        for i, calendar in enumerate(calendars):
            print(f"{i+1}. {calendar.name} (ID: {calendar.id})")
        
        selection = input("Select a calendar number (or press Enter for first one): ")
        if selection.strip() and selection.isdigit() and 1 <= int(selection) <= len(calendars):
            self.calendar = calendars[int(selection)-1]
        else:
            self.calendar = calendars[0]
        
        print(f"Selected calendar: {self.calendar.name}")

    def create_event(self, name, description, start, end):
        """Create a new calendar event"""
        # Format the dates for CalDAV (RFC 5545 format)
        start_date = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))
        
        # Create the event
        event = self.calendar.save_event(
            dtstart=start_date,
            dtend=end_date,
            summary=name,
            description=description
        )
        
        print(f'Event created: {name}')
        return event.url
    
    def delete_events_in_date_range(self, time_min, time_max):
        """Delete all events in a specified time range"""
        # Convert string ISO dates to datetime objects
        start_date = datetime.datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Find events in the date range
        events = self.calendar.search(start=start_date, end=end_date)
        
        if not events:
            print("No events found in the specified date window.")
        else:
            for event in events:
                event_summary = self.get_event_summary(event)
                event.delete()
                print(f"Deleted event: {event_summary}")

    def list_calendars(self):
        """List all available calendars"""
        return self.principal.calendars()

    def get_calendar_by_name(self, target_name):
        """Find a calendar by its name"""
        calendars = self.list_calendars()
        
        for calendar in calendars:
            if calendar.name == target_name:
                return calendar
        return None
    
    def delete_event_by_id(self, event_id):
        """Delete a specific event by its ID"""
        try:
            # Try to find the event directly by ID if the calendar implementation supports it
            event = self.calendar.event_by_uid(event_id)
            event_summary = self.get_event_summary(event)

            # Delete the event
            event.delete()
            print(f"Deleted event: {event_summary} (ID: {event_id})")
            return True
        except Exception:
            # If direct access fails, try to find the event by searching all events
            # Note: This is less efficient but necessary for some CalDAV servers
            print(f"Event with ID {event_id} not found directly. Searching all events...")

            events = self.calendar.search(
                start=self.start_time,
                end=self.end_time
            )

            for event in events:
                if event.id == event_id:
                    event_summary = self.get_event_summary(event)
                    event.delete()
                    print(f"Deleted event: {event_summary} (ID: {event_id})")
                    return True

            print(f"No event found with ID: {event_id}")
            return False

    def get_event_component(self, event):
        """Return the icalendar component (VEVENT) of an event.

        The vobject based 'event.instance' is not used anymore, it needs the
        vobject package which is no longer a dependency of caldav.
        """
        try:
            return event.icalendar_component
        except Exception:
            return None

    def get_event_summary(self, event):
        """Return the title of an event"""
        component = self.get_event_component(event)
        if component is None:
            return 'No title'
        summary = component.get("summary")
        return str(summary) if summary is not None else 'No title'

    def get_event_dates(self, component, fallback_start, fallback_end):
        """Return the start and end of an event as ISO strings"""
        start = component.get("dtstart")
        end = component.get("dtend")
        start_dt = start.dt if start is not None else None
        end_dt = end.dt if end is not None else None

        if start_dt is None:
            start_dt = fallback_start
        if end_dt is None:
            # Default to start time + 1 hour if no end time
            end_dt = start_dt + datetime.timedelta(hours=1)

        if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
            start_dt = datetime.datetime.combine(start_dt, datetime.time())
        if isinstance(end_dt, datetime.date) and not isinstance(end_dt, datetime.datetime):
            end_dt = datetime.datetime.combine(end_dt, datetime.time())

        return start_dt.isoformat(), end_dt.isoformat()

    def get_events_in_date_range(self, time_min, time_max):
        """Get all events in a specified time range"""
        # Convert string ISO dates to datetime objects
        start_date = datetime.datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(time_max.replace('Z', '+00:00'))

        # Find events in the date range
        events = self.calendar.search(start=start_date, end=end_date)

        if not events:
            print("No events found in the specified date range.")
            return None
        else:
            # Format the events to match the Google Calendar API structure
            formatted_events = []
            for event in events:
                component = self.get_event_component(event)
                if component is None:
                    print(f"Skipping event without icalendar data: {event.url}")
                    continue

                # The UID is the most reliable identifier, fall back to the URL
                event_id = event.id
                if not event_id:
                    url_parts = event.url.split('/')
                    event_id = url_parts[-1]
                    if '.ics' in event_id:
                        event_id = event_id.split('.ics')[0]

                # Extract date/time information safely
                try:
                    start_iso, end_iso = self.get_event_dates(component, start_date, end_date)
                except Exception as e:
                    print(f"Error parsing event dates: {str(e)}")
                    # Use fallback dates
                    start_iso = start_date.isoformat()
                    end_iso = end_date.isoformat()

                summary = component.get("summary")
                description = component.get("description")

                # Extract basic event information
                event_data = {
                    'id': event_id,  # Using UID as the primary identifier
                    'caldav_url': event.url,  # Store the URL for direct access
                    'summary': str(summary) if summary is not None else 'No title',
                    'description': str(description) if description is not None else '',
                    'start': {
                        'dateTime': start_iso,
                        'timeZone': 'Europe/Berlin'
                    },
                    'end': {
                        'dateTime': end_iso,
                        'timeZone': 'Europe/Berlin'
                    }
                }

                # Debug print to verify we're getting the event properly
                print(f"Found event: {event_data['summary']} (ID: {event_data['id']})")

                formatted_events.append(event_data)

            print(f"Total events found: {len(formatted_events)}")
            return formatted_events