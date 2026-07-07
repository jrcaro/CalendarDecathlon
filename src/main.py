import logging
import requests
import time
import json
from datetime import datetime
from dateutil.rrule import rrule, MONTHLY
from constants import *
from utils import *
import argparse
import sys
from logger import logger

def main(
   user,
   password,
   calendar_id,
   collaborator_id     
):
    # Selenium driver
    logger.info("Create selenium driver")
    driver = get_driver()
    logger.info("Go to login endpoint")
    driver.get(LOGIN_ENDPOINT)
    time.sleep(2)

    # Login
    logger.info("Send user and password")
    driver.find_element(By.ID, "username").send_keys(user)
    driver.find_element(By.ID, "password").send_keys(password)
    driver.find_element(By.ID, "cnxbton").click()
    time.sleep(2)

    # Cookies
    #driver.find_element(By.ID, "didomi-notice-agree-button").click()

    # Get token
    logger.info("Get authentication header")
    logs = driver.get_log("performance")
    sel_requests = [json.loads(lr["message"])["message"] for lr in logs]
    sel_headers = list(filter(log_filter, sel_requests))[0]["params"]["request"]["headers"]

    # Exit selenium
    driver.quit()

    # Get contract end date
    logger.info("Call collaborator endpoint")
    res_contract = requests.get(f"{COLLABORATOR_ENDPOINT}/{collaborator_id}", headers=sel_headers)
    if res_contract.status_code:
        end_contract_date = "-".join(res_contract.json()["activeContract"]["endDate"].split("-")[0:2]) + "-01"
    else:
        raise Exception

    logger.info("Get available dates")
    planning_dates_ = [date for date in rrule(MONTHLY, dtstart=datetime.now(), until=datetime.strptime(end_contract_date,"%Y-%m-%d"))]
    planning_dates_.append(datetime.strptime(end_contract_date,"%Y-%m-%d"))
    planning_dates = [datetime.strftime(x,'%Y-%m')+"-01" for x in planning_dates_]
    collaborator_periods__ = None

    # Get all periods
    for month_filter in planning_dates:
        # Call Planning API
        logger.info(f"Call planning endpoint -> {month_filter}")
        res = requests.get(PLANNING_ENDPOINT, headers=sel_headers, params={
            "filter[month]": month_filter,
            "filter[collaboratorUuid]": collaborator_id
        })
        
        if res.status_code:
            # Extend to list
            if not collaborator_periods__:
                collaborator_periods__ = res.json()["collaboratorPeriods"]
            else:
                collaborator_periods__.extend(res.json()["collaboratorPeriods"])

    # Delete duplicates
    collaborator_periods_ = [dict(t) for t in {tuple(d.items()) for d in collaborator_periods__}]
    collaborator_periods = list(filter(lambda x: datetime.strptime(x["fromHour"],"%Y-%m-%dT%H:%M:%S") > datetime.now(),collaborator_periods_))

    # Get all Google events
    tmin = datetime.strftime(datetime.now(),"%Y-%m-%dT%H:%M:%SZ")
    tmax = datetime.strftime(max([datetime.strptime(x["fromHour"],"%Y-%m-%dT%H:%M:%S") for x in collaborator_periods]),"%Y-%m-%dT%H:%M:%SZ")
    service = calendar_service()

    logger.info("Get actual Google calendar events")
    
    eventsResult = service.events().list(
        calendarId=calendar_id,
        timeMin=tmin,
        timeMax=tmax,
        singleEvents=True,
        orderBy='startTime',
        timeZone='Europe/Madrid'
    ).execute()

    # Data key
    google_events = eventsResult.get("items", [])
    decathlon_uuid_periods = [x["planningPeriodUuid"] for x in collaborator_periods]

    # Google periods UUIDs
    if google_events:
        try:
            google_uuid_periods = [x["description"] for x in google_events]
        except KeyError:
            google_uuid_periods = []
    else:
        google_uuid_periods = []
            
    logger.info("Compare UUIDs")
    diff_uuids_google = list(set(google_uuid_periods)-(set(decathlon_uuid_periods)))
    diff_uuids_decathlon = list((set(decathlon_uuid_periods))-set(google_uuid_periods))

    if not diff_uuids_google and not diff_uuids_decathlon:
        logger.info("No new periods")
        sys.exit()

    # Insert all periods when UUID is not in Google
    for decathlon_uuid in diff_uuids_decathlon:
        decathlon_event = list(filter(lambda x: uuid_filter(x,decathlon_uuid),collaborator_periods))[0]                
        decathlon_datime_start = datetime.strptime(decathlon_event["fromHour"],"%Y-%m-%dT%H:%M:%S")
        decathlon_datime_end = datetime.strptime(decathlon_event["toHour"],"%Y-%m-%dT%H:%M:%S")
        summary = SECTION[decathlon_event["abbreviation"]]

        # Body
        event = {
            'summary': summary,
            'location': 'Cam. Loma de San Julián, Malaga',
            'description': decathlon_event["planningPeriodUuid"],
            'start': {
                'dateTime': datetime.strftime(decathlon_datime_start,"%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Europe/Madrid',
            },
            'end': {
                'dateTime': datetime.strftime(decathlon_datime_end,"%Y-%m-%dT%H:%M:%S"),
                'timeZone': 'Europe/Madrid',
            },
            'reminders': {
                'useDefault': True
            },
        }

        logger.info(f"Inserting {datetime.strptime(decathlon_event["fromHour"],"%Y-%m-%dT%H:%M:%S").date()}")
        service.events().insert(calendarId=calendar_id, body=event).execute()

    # Delete all periods when UUID is not in collaborator
    for google_uuid in diff_uuids_google:
        google_event = list(filter(lambda x: uuid_filter(x,google_uuid),google_events))[0]
        logger.info(f"Deleting {datetime.strptime(decathlon_event["start"]["datetime"],"%Y-%m-%dT%H:%M:%S").date()}")
        service.events().delete(calendarId=calendar_id, eventId=google_event['id']).execute()

if __name__ == "__main__":
    """
    python src/main.py
     --user your.email@mail.com
     --password 1234
     --calendar-id <calendar_id>@group.calendar.google.com
     --collaborator-id
    """
    parser = argparse.ArgumentParser(
        description="CLI tool to copy Decathlon planning to Google calendar"
    )

    parser.add_argument(
        "--user", required=True, type=str, help="Decathlon planning user name"
    )
    parser.add_argument(
        "--password", required=True, type=str, help="Decathlon planning password"
    )
    parser.add_argument(
        "--calendar-id", required=True, type=str, help="Google calendar ID"
    )
    parser.add_argument(
        "--collaborator-id", required=True, type=str, help="Decathlon collaborator ID"
    )

    args = parser.parse_args()
    input = {key: value for key, value in args.__dict__.items() if value is not None}
    main(**input)
