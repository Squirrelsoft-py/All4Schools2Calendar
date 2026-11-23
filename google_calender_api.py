import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path


class Main:
    def authenticate_google(self):
        creds = None
        # token.json speichert die Zugriffstoken – wird beim ersten Lauf erstellt
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        # Falls keine gültigen Anmeldeinformationen vorhanden sind, zum erneuten Login auffordern.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            # Token speichern
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds


    def __init__(self, calendar_id="", calendar_name=""):
        self.SCOPES = ['https://www.googleapis.com/auth/calendar']
        self.creds = self.authenticate_google()

        if calendar_name != "":
            self.calendar_id = self.get_calendar_id_by_name(calendar_name)
            print(self.calendar_id)
        elif calendar_id != "":
            self.calendar_id = calendar_id
        
        else:
            print("\nWARNING: Not given calendar name or id, assuming default. If you want to disable this message, set calendar_id = 'primary'\nThe following calendars are available:")
            calendars = self.list_calendars()
            for calendar in calendars:
                print(f"Name: {calendar.get('summary')}")
                print(f"ID: {calendar.get('id')}")
                print("-----")
            self.calendar_id = "primary"


    def create_event(self, name, description, start, end):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': name,
            'description': description,
            'start': {
                'dateTime': start,          # '2025-03-28T09:00:00+01:00' +01:00 ist die Standardzeit für Berlin (MEZ)
                'timeZone': 'Europe/Berlin',
            },
            'end': {
                'dateTime': end,
                'timeZone': 'Europe/Berlin',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 5}
                ]
            }
        }

        created_event = service.events().insert(calendarId=self.calendar_id, body=event).execute()
        print('Termin erstellt: %s' % (created_event.get('htmlLink')))

        return created_event.get('htmlLink')
    
    def delete_events_in_date_range(self, time_min, time_max):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)

        # List events in the specified time window
        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            print("No events found in the specified date window.")
        else:
            for event in events:
                event_id = event['id']
                service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
                print(f"Deleted event: {event.get('summary', 'No title')}")

    def list_calendars(self):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        return calendars

    def get_calendar_id_by_name(self, target_name):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        for calendar in calendars:
            # The "summary" field holds the calendar's name.
            if calendar.get('summary') == target_name:
                return calendar.get('id')
        return None
    
    def get_events_in_date_range(self, time_min, time_max):
        creds = self.creds
        service = build('calendar', 'v3', credentials=creds)

        # List events in the specified time window
        events_result = service.events().list(
            calendarId=self.calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return None
        else:
            return events