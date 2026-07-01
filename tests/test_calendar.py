import os
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.core.config import settings

# 1. Define the required scope
SCOPES = ['https://www.googleapis.com/auth/calendar']

# 2. Update these two strings with your file and your actual Gmail
SERVICE_ACCOUNT_FILE = settings.GOOGLE_SERVICE_ACCOUNT_FILE
YOUR_PERSONAL_GMAIL = 'Your Gmail that you used to give access to the service account.' 

def test_google_connection():
    print("🔄 Initializing Google Calendar Service Account connection...")
    
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        print(f"❌ Error: Could not find '{SERVICE_ACCOUNT_FILE}' in this directory.")
        return

    try:
        # Load credentials from file
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=creds)
        
        # Define time window starting from right now
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        print(f"📅 Fetching next 5 events from calendar: {YOUR_PERSONAL_GMAIL}...")
        
        # Execute basic list request
        events_result = service.events().list(
            calendarId=YOUR_PERSONAL_GMAIL, 
            timeMin=now,
            maxResults=5, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        print("\n✅ CONNECTION SUCCESSFUL!")
        if not events:
            print("No upcoming events found (but the API call worked perfectly).")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            print(f" - [{start}] {event.get('summary', 'No Title')}")
            
    except Exception as e:
        print("\n❌ CONNECTION FAILED!")
        print(f"Error Details: {str(e)}")
        print("\nCommon fixes if you see a '404 / Not Found' or '403 / Forbidden':")
        print("1. Did you share your Google Calendar with the service account email found inside the JSON?")
        print("2. Did you give that email permission to 'Make changes to events'?")

if __name__ == '__main__':
    test_google_connection()