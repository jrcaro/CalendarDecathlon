from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.identity_pool import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from constants import SCOPES
import os
import logging

def calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    try:
        # Github execution
        creds = Credentials.from_file(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"],
        scopes=SCOPES
    )

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
    except KeyError:
        # Local execution
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials_2526.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
    
    except HttpError as error:
        print(f"An error occurred: {error}")
    
    return service


def get_driver():
    # The log disable with the option headless=new is not working
    logging.getLogger('selenium').setLevel(logging.ERROR)

    chrome_service = Service('/usr/local/bin/chromedriver')

    chrome_options = Options()
    options = [
        '--headless',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--disable-extensions',
        '--start-maximized',
        '--disk-cache-size=1',
        '--media-cache-size=1',
        '--incognito',
        '--remote-debugging-port=9222',
        '--aggressive-cache-discard'
    ]
    for option in options:
        chrome_options.add_argument(option)

    chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    return webdriver.Chrome(service=chrome_service, options=chrome_options)

def log_filter(log_):
    return (
        log_["method"] == "Network.requestWillBeSent"
        and "Authorization" in log_["params"]["request"]["headers"]
    )

def uuid_filter(event_, uuid_):
    if "planningPeriodUuid" in event_.keys():
        return (
            event_["planningPeriodUuid"] == uuid_
        )
    else:
        return (
            event_["description"] == uuid_
        )