import datetime
import caldav
from caldav.elements import dav, cdav
import os.path
import getpass


class Main:
    def authenticate_caldav(self):
        creds = None
        # Check if credentials file exists
        if os.path.exists('caldav_credentials.txt'):
            with open('caldav_credentials.txt', 'r') as file:
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
                with open('caldav_credentials.txt', 'w') as file:
                    file.write(f"{url}\n{username}\n{password}")
        
        return creds

    def __init__(self, calendar_id="", calendar_name="", t_start=datetime.datetime.now(), t_end=datetime.datetime.now() + datetime.timedelta(days=365)):
        self.start_time = t_start
        self.end_time = t_end
        self.creds = self.authenticate_caldav()
        
        # Connect to the CalDAV server
        self.client = caldav.DAVClient(
            url=self.creds['url'],
            username=self.creds['username'],
            password=self.creds['password']
        )
        
        # Get principal
        self.principal = self.client.principal()
        
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
        events = self.calendar.date_search(start=start_date, end=end_date)
        
        if not events:
            print("No events found in the specified date window.")
        else:
            for event in events:
                event_data = event.instance.vevent
                event_summary = event_data.summary.value if hasattr(event_data, 'summary') else 'No title'
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
            event = self.calendar.event(event_id)
            event_summary = 'Unknown'
            
            try:
                # Try to get the event summary before deletion
                event_data = event.instance.vevent
                event_summary = event_data.summary.value if hasattr(event_data, 'summary') else 'No title'
            except:
                pass
                
            # Delete the event
            event.delete()
            print(f"Deleted event: {event_summary} (ID: {event_id})")
            return True
        except:
            # If direct access fails, try to find the event by searching all events
            # Note: This is less efficient but necessary for some CalDAV servers
            print(f"Event with ID {event_id} not found directly. Searching all events...")
            
            events = self.calendar.date_search(
                start=self.start_time,
                end=self.end_time
            )
            
            for event in events:
                if event.id == event_id:
                    event_data = event.instance.vevent
                    event_summary = event_data.summary.value if hasattr(event_data, 'summary') else 'No title'
                    event.delete()
                    print(f"Deleted event: {event_summary} (ID: {event_id})")
                    return True
            
            print(f"No event found with ID: {event_id}")
            return False
    
    def get_events_in_date_range(self, time_min, time_max):
        """Get all events in a specified time range"""
        # Convert string ISO dates to datetime objects
        start_date = datetime.datetime.fromisoformat(time_min.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(time_max.replace('Z', '+00:00'))
        
        # Find events in the date range
        events = self.calendar.date_search(start=start_date, end=end_date)
        
        if not events:
            print("No events found in the specified date range.")
            return None
        else:
            # Format the events to match the Google Calendar API structure
            formatted_events = []
            for event in events:
                vevent = event.instance.vevent
                
                # Extract event ID from URL (fallback method)
                # The URL typically ends with the ID
                url_parts = event.url.split('/')
                event_id = url_parts[-1]
                if '.ics' in event_id:
                    event_id = event_id.split('.ics')[0]
                
                # Get event UID which is a more reliable identifier
                event_uid = vevent.uid.value if hasattr(vevent, 'uid') else event_id
                
                # Extract date/time information safely
                try:
                    start_dt = vevent.dtstart.value
                    if isinstance(start_dt, datetime.date) and not isinstance(start_dt, datetime.datetime):
                        start_dt = datetime.datetime.combine(start_dt, datetime.time())
                    start_iso = start_dt.isoformat()
                    
                    # Handle end time (might be missing in some events)
                    if hasattr(vevent, 'dtend'):
                        end_dt = vevent.dtend.value
                        if isinstance(end_dt, datetime.date) and not isinstance(end_dt, datetime.datetime):
                            end_dt = datetime.datetime.combine(end_dt, datetime.time())
                        end_iso = end_dt.isoformat()
                    else:
                        # Default to start time + 1 hour if no end time
                        end_dt = start_dt + datetime.timedelta(hours=1)
                        end_iso = end_dt.isoformat()
                        
                except Exception as e:
                    print(f"Error parsing event dates: {str(e)}")
                    # Use fallback dates
                    start_iso = start_date.isoformat()
                    end_iso = end_date.isoformat()
                
                # Extract basic event information
                event_data = {
                    'id': event_uid,  # Using UID as the primary identifier
                    'caldav_url': event.url,  # Store the URL for direct access
                    'summary': vevent.summary.value if hasattr(vevent, 'summary') else 'No title',
                    'description': vevent.description.value if hasattr(vevent, 'description') else '',
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