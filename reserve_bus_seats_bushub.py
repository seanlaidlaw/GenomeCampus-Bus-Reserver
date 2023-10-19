#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import logging


# configure the IDs for different bus stops
CASTLE_CODE = "0500CCITY275"
CENTENNIAL_CODE = "0500CCITY022"
CAMPUS_CODE = "BUSHUBd6ZTW0SS"

# configure the date and time of the bus you want to book
PICKUP_ATCOCODE = CENTENNIAL_CODE
DROPOFF_ATCOCODE = CAMPUS_CODE

# read in cookie file that contains the ; separated string for the BusHub cookie
# to obtain it, you open the developer tools in your browser, go to the network tab
# login to https://wellcomegenomecampus.bushub.co.uk/bookings and click on the
# bookings request, then copy the cookie string from the request headers
# save its contents into this file
with open("bushub_cookie.txt") as f:
    COOKIE = f.read()

# configuring the logger to info log levek
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)


# each combination of bus stops has its own route ID for NC/CC/EC etc.
LINE_ID = ""
if PICKUP_ATCOCODE == CASTLE_CODE or DROPOFF_ATCOCODE == CASTLE_CODE:
    LINE_ID = "85334"
elif PICKUP_ATCOCODE == CENTENNIAL_CODE or DROPOFF_ATCOCODE == CENTENNIAL_CODE:
    LINE_ID = "85336"

if LINE_ID == "":
    log.error("🚩 could not identify bus route from these stops")
    raise Exception()


def get_upcoming_dates(start_date):
    if start_date is None:
        start_date = datetime.now()
        start_date += timedelta(days=1)

    # Get date for two weeks later
    end_date = start_date + timedelta(weeks=2)

    # Initialize an empty list to store the dates
    date_list = []

    # Loop through the days
    current_date = start_date
    while current_date <= end_date:
        # Check if the day is a weekend
        if current_date.weekday() < 5:  # 0-4 denotes Monday to Friday
            # Add the date to the list in ISO format
            date_list.append(current_date.date().isoformat())
        # Move to the next day
        current_date += timedelta(days=1)

    return date_list


def get_available_buses(TRAVEL_DATE, LINE_ID, PICKUP_ATCOCODE, DROPOFF_ATCOCODE):
    url_get_buses = f"https://nextstopapp.bushub.co.uk/api/v1.0/service/{LINE_ID}/bookings/times?date={TRAVEL_DATE}&pickupAtcocode={PICKUP_ATCOCODE}&dropoffAtcocode={DROPOFF_ATCOCODE}"

    headers_get_buses = {
        "accept": "application/json, text/plain, */*",
        "referer": "https://wellcomegenomecampus.bushub.co.uk/booking/create",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    }

    log.info(
        f"🚍 for buses on route: {LINE_ID}, on {TRAVEL_DATE} between stops: {PICKUP_ATCOCODE} and {DROPOFF_ATCOCODE}"
    )

    # make the request and raise an exception if it fails
    response = requests.get(url_get_buses, headers=headers_get_buses)
    if not response.ok:
        log.error(
            "🚩 Something went wrong with request to fetch list of buses for this route. The request was not successful"
        )
        raise Exception(response.raise_for_status())

    # response.json() will return the json response as a Python dictionary
    data = response.json()

    items = data["items"]
    if len(items) == 0:
        log.error(
            "🚩 The request was successful, but there are no buses listed for this route at this date and time"
        )
        raise Exception()

    # Convert "scheduledDepartureTime" to datetime and sort items
    for item in items:
        item["scheduledDepartureTime"] = datetime.fromisoformat(
            item["scheduledDepartureTime"]
        )

    # sort by "scheduledDepartureTime" in descending order
    # from latest to earliest
    items.sort(key=lambda x: x["scheduledDepartureTime"], reverse=True)

    # Filter out items where "bookings" == "capacity"
    filtered_items = [
        item
        for item in items
        if item["bookingOptions"]["bookings"] != item["bookingOptions"]["capacity"]
    ]

    if len(filtered_items) == 0:
        log.error("🚩 there are buses on this route but none with any space remain")
        raise Exception()

    # Convert back "scheduledDepartureTime" to ISO format
    for item in filtered_items:
        item["scheduledDepartureTime"] = item["scheduledDepartureTime"].isoformat()

    log.info(
        f"🚍 Found {len(filtered_items)} buses with available seats on this route at: {list(map(lambda x: x['scheduledDepartureTime'], filtered_items))}"
    )
    return filtered_items


def get_booking_tickets(LINE_ID, COOKIE):
    url = "https://wellcomegenomecampus.bushub.co.uk/booking/tickets"

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": COOKIE,
        "origin": "https://wellcomegenomecampus.bushub.co.uk",
        "referer": "https://wellcomegenomecampus.bushub.co.uk/booking/create",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
    }

    data_raw = {
        "objects": [{"lineId": LINE_ID, "passengers": 1, "tickets": [], "fares": []}]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data_raw))
    if not response.ok:
        log.error(
            "🚩 Something went wrong with request to fetch current ticket  for this account"
        )
        raise Exception(response.raise_for_status())

    tickets = response.json()
    tickets = tickets["Outbound"]["MyTickets"]
    if len(tickets) == 0:
        log.error("🚩 no tickets found for this account")
        raise Exception()

    ticket_id = tickets[0]["Details"]["Id"]
    return ticket_id


def get_existing_reservations(COOKIE):
    url = "https://wellcomegenomecampus.bushub.co.uk/bookings?take=100"

    headers = {
        "accept": "text/html, */*",
        "content-type": "application/json",
        "cookie": COOKIE,
        "referer": "https://wellcomegenomecampus.bushub.co.uk/booking/create",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    }

    response = requests.get(url, headers=headers)
    if not response.ok:
        log.error(
            f"🚩 Something went wrong with request to get existing bus reservations."
        )
        log.error(response.text)
        raise Exception(response.raise_for_status())

    soup = BeautifulSoup(response.text, "html.parser")

    # Find the table with class "table"
    table = soup.find("table", class_="table")
    if not table:
        log.error(
            f"🚩 Couldn't find table with existing reservations on usual webpage."
        )
        raise Exception()

    # Initialize an empty list to store dictionaries representing each row
    table_data = []

    # Extract rows from the table
    rows = table.find_all("tr")

    # Get the column names from the header row (assuming they are in <th> tags)
    header_row = rows[0]
    column_names = [header.text.strip() for header in header_row.find_all("th")]

    # Process each row (skip the header row)
    for row in rows[1:]:
        # Get the data cells from the current row
        cells = row.find_all("td")

        # Create a dictionary for the current row
        row_data = {}
        for i, cell in enumerate(cells):
            row_data[column_names[i]] = cell.text.strip()

        # Convert 'Date' and 'Time' to datetime object and add 'datetimeISO'
        date_time_str = row_data["Date"] + " " + row_data["Time"]
        row_data["datetimeISO"] = datetime.strptime(
            date_time_str, "%d/%m/%Y %H:%M"
        ).isoformat()

        # Extract the date part from 'datetimeISO'
        row_data["dateISO"] = datetime.strptime(
            row_data["datetimeISO"], "%Y-%m-%dT%H:%M:%S"
        ).date()

        # Append the row data dictionary to the table_data list
        table_data.append(row_data)

    return table_data


def reserve_bus(
    TRAVEL_DATE, LINE_ID, PICKUP_ATCOCODE, DROPOFF_ATCOCODE, COOKIE, ticket_id
):
    url = "https://wellcomegenomecampus.bushub.co.uk/booking"

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": COOKIE,
        "referer": "https://wellcomegenomecampus.bushub.co.uk/booking/create",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    }

    data_raw = {
        "objects": [
            {
                "lineId": LINE_ID,
                "date": TRAVEL_DATE,
                "pickupAtcocode": PICKUP_ATCOCODE,
                "dropoffAtcocode": DROPOFF_ATCOCODE,
                "direction": "Inbound",
                "passengers": 1,
                "tickets": [int(ticket_id)],
                "fares": [],
            }
        ]
    }

    response = requests.post(url, headers=headers, data=json.dumps(data_raw))
    if not response.ok:
        log.error(
            f"🚩 Something went wrong with request to reserve bus on route: {LINE_ID}, on {TRAVEL_DATE} between stops: {PICKUP_ATCOCODE} and {DROPOFF_ATCOCODE}."
        )
        log.error(response.text)
        break_error_msgs = [
            "This service cannot be found at this time.",
            "Future bookings are limited on this service.",
        ]
        response_text = response.text.strip('"').strip("'").strip()
        if any([response_text.startswith(msg) for msg in break_error_msgs]):
            return None
        else:
            raise Exception(response.raise_for_status())
    return response


# get details of existing bus reservations
existing_reservations = get_existing_reservations(COOKIE)
# convert time of reservations to string format for comparing with available reservations
existing_reserved_days = [
    datetime.strftime(item["dateISO"], "%Y-%m-%d") for item in existing_reservations
]

# get string format of every date in next week (bar weekends)
next_dates = get_upcoming_dates(start_date=None)
for TRAVEL_DATE in next_dates:
    dateISO = datetime.strptime(TRAVEL_DATE, "%Y-%m-%d").date()
    if TRAVEL_DATE in existing_reserved_days:
        log.info(f"🚌 Bus already booked for {TRAVEL_DATE}.")
        continue

    # get list of buses with available seats on the desired date
    available_buses = get_available_buses(
        TRAVEL_DATE, LINE_ID, PICKUP_ATCOCODE, DROPOFF_ATCOCODE
    )

    # attempt booking bus ticket in order of latest departure time
    for item in available_buses:
        # get bus departure time and id of bus route (line id)
        bus_time = item["scheduledDepartureTime"]
        bus_line = item["lineId"]

        # get id of currently owned ticket
        ticket_id = get_booking_tickets(bus_line, COOKIE)

        # attempt to reserve bus ticket
        # on error (e.g. bus is full), try next bus
        reserved = reserve_bus(
            bus_time, bus_line, PICKUP_ATCOCODE, DROPOFF_ATCOCODE, COOKIE, ticket_id)
        if reserved:
            if reserved.ok:
                break  # break to not book multiple buses for same day
        else:
            break
