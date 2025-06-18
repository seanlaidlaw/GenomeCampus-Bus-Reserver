#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import os
from datetime import datetime, timedelta

import requests
import yaml
from bs4 import BeautifulSoup

# configuring the logger to info log levek
log = logging.getLogger()
logging.basicConfig(level=logging.INFO)


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


def login_and_save_cookie(username, password):
    # Define the login page and endpoint URLs
    login_page_url = "https://wellcomegenomecampus.bushub.co.uk/"
    login_endpoint_url = (
        "https://wellcomegenomecampus.bushub.co.uk/account/BushubLoginMainResult"
    )

    # Headers extracted from the curl command
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "Origin": "https://wellcomegenomecampus.bushub.co.uk",
        "Referer": "https://wellcomegenomecampus.bushub.co.uk/?redirectUrl=/bookings",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,fr;q=0.7",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    with requests.Session() as session:
        # Fetch the login page to get the CSRF token
        response = session.get(login_page_url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        token = soup.find("input", {"name": "__RequestVerificationToken"}).get(
            "value", ""
        )

        # Prepare the form data
        payload = {
            "__RequestVerificationToken": token,
            "RedirectUrl": "/bookings",
            "username": username,
            "password": password,
        }

        # Post login details
        response = session.post(login_endpoint_url, data=payload, headers=headers)

        # Check if login is successful by examining the response content or URL
        if response.status_code == 200 and "Log In" not in response.text:
            with open("bushub_cookie.txt", "w") as cookie_file:
                for cookie in session.cookies:
                    cookie_file.write(f"{cookie.name}={cookie.value}\n")
            print("Login successful and cookies saved!")
        else:
            log.error(
                "🚩 Something went wrong with login request. Please check your credentials and try again."
            )
            raise Exception(response.raise_for_status())

def get_bus_stops(COOKIE):
    """
    Fetches bus stop information from the BusHub API.
    Returns a dictionary mapping bus route numbers to their stops.
    """
    url = "https://nextstopapp.bushub.co.uk/api/v1.0/service/region/490"

    # Get next weekday date in ISO format for the query parameter
    current_date = datetime.now()
    next_weekday = current_date + timedelta(days=1)
    while next_weekday.weekday() >= 5:  # Skip weekends (5=Saturday, 6=Sunday)
        next_weekday += timedelta(days=1)

    current_date = next_weekday.isoformat()

    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "cookie": COOKIE,
        "origin": "https://wellcomegenomecampus.bushub.co.uk",
        "referer": "https://wellcomegenomecampus.bushub.co.uk/booking/create",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest"
    }

    params = {
        "date": current_date,
        "includeRunBy": "true",
        "canBook": "true"
    }

    response = requests.get(url, headers=headers, params=params)
    if not response.ok:
        log.error("🚩 Failed to fetch bus stop information")
        log.error(response.text)
        raise Exception(response.raise_for_status())

    data = response.json()
    bus_routes = []

    for item in data["items"]:
        if 'lineId' not in item:
            log.error("🚩 No lineId found for bus route")
            continue

        # Create separate services for AM and PM directions
        am_service = {
            "Service": item['lineId'],
            "name": item.get("name"),
            "direction": "AM",
            "stops": []
        }

        pm_service = {
            "Service": item['lineId'],
            "name": item.get("name"),
            "direction": "PM",
            "stops": []
        }

        if "journeyPatterns" in item:
            for pattern in item["journeyPatterns"]:
                if "busHubRouteRefs" in pattern and pattern["busHubRouteRefs"]:
                    # Extract stops from journey patterns
                    for stop in pattern["journeyPatterns"]:
                        if "atcoCode" in stop and "name" in stop:
                            stop_info = {
                                "atcoCode": stop["atcoCode"],
                                "name": stop["name"]
                            }

                            # Assign stop to appropriate direction service
                            if "direction" in stop:
                                if stop["direction"] == 2:
                                    am_service["stops"].append(stop_info)
                                elif stop["direction"] == 1:
                                    pm_service["stops"].append(stop_info)
                            else:
                                # If no direction field, add to both (fallback)
                                am_service["stops"].append(stop_info)
                                pm_service["stops"].append(stop_info)

        # Only add services that have stops
        if am_service["stops"]:
            bus_routes.append(am_service)
        if pm_service["stops"]:
            bus_routes.append(pm_service)

    return bus_routes


def generate_busroutes_yaml(bus_stops_data, existing_config=None):
    """
    Generate busroutes.yaml structure from bus stops data.
    Preserves existing route mappings if available.
    """
    if existing_config is None:
        existing_config = {}

    # Create a mapping of service IDs to route codes and periods
    service_to_route_mapping = {}

    # Extract existing mappings to preserve them
    for route_code, route_data in existing_config.items():
        for period in ["AM", "PM"]:
            if period in route_data:
                service_id = route_data[period]["Service"]
                service_to_route_mapping[service_id] = {
                    "route_code": route_code,
                    "period": period
                }

    # Generate new structure
    new_routes = {}

    # Process each service from the bus_stops_data list
    for service_data in bus_stops_data:
        service_id = service_data["Service"]
        direction = service_data["direction"]
        route_name = service_data["name"]

        # Check if this service already has a mapping
        if service_id in service_to_route_mapping:
            mapping = service_to_route_mapping[service_id]
            route_code = mapping["route_code"]
            period = mapping["period"]
        else:
            # Use the route name from the API data
            route_code = route_name
            period = direction

        # Initialize route structure if needed
        if route_code not in new_routes:
            new_routes[route_code] = {}

        if period not in new_routes[route_code]:
            new_routes[route_code][period] = {
                "Service": str(service_id),
                "Stops": {}
            }

        # Add all stops for this service
        for stop in service_data["stops"]:
            new_routes[route_code][period]["Stops"][stop["name"]] = stop["atcoCode"]

    return new_routes


def save_busroutes_yaml(bus_routes_data, filename="busroutes.yaml"):
    """
    Save the bus routes data to a YAML file.
    """
    try:
        with open(filename, "w") as file:
            yaml.dump(bus_routes_data, file, default_flow_style=False, sort_keys=False)
        log.info(f"✅ Successfully saved bus routes to {filename}")
    except Exception as e:
        log.error(f"🚩 Failed to save bus routes to {filename}: {e}")
        raise

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

    # filter down array of tickets to only those with remaining activations
    tickets = [ticket for ticket in tickets if ticket["Activations"]["Remaining"] > 0]

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
            f"🚩 Couldn't find table with existing reservations on usual webpage. This can happen if there are no reservations at all on the app."
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


# if login_details file exists, read in username and password
login_details = "login_details.txt"
if not os.path.exists(login_details):
    log.error(
        f"🚩 {login_details} file does not exist. Please create it and add your username and password in the format: username,password"
    )
    raise Exception()

with open(login_details) as f:
    username, password = f.read().strip().split(",")
login_and_save_cookie(username, password)

# read in cookie file that contains the ; separated string for the BusHub cookie
# to obtain it, you open the developer tools in your browser, go to the network tab
# login to https://wellcomegenomecampus.bushub.co.uk/bookings and click on the
# bookings request, then copy the cookie string from the request headers
# save its contents into this file
with open("bushub_cookie.txt") as f:
    COOKIE = f.read().strip()
    COOKIE = COOKIE.replace("\n", "; ")

# Dynamically update busroutes.yaml with latest bus stop information
log.info("🔄 Fetching latest bus stop information...")
try:
    # Load existing busroutes.yaml if it exists
    existing_busroutes = {}
    if os.path.exists("busroutes.yaml"):
        with open("busroutes.yaml", "r") as file:
            existing_busroutes = yaml.safe_load(file) or {}

    # Get current bus stops from API
    current_bus_stops = get_bus_stops(COOKIE)

    # Generate new busroutes structure
    updated_busroutes = generate_busroutes_yaml(current_bus_stops, existing_busroutes)

    # Save updated busroutes.yaml
    save_busroutes_yaml(updated_busroutes)

except Exception as e:
    log.warning(f"⚠️ Failed to update busroutes.yaml dynamically: {e}")
    log.info("📝 Continuing with existing busroutes.yaml file...")

# get details of existing bus reservations
existing_reservations = get_existing_reservations(COOKIE)
# convert time of reservations to string format for comparing with available reservations
# split into two lists one for morning and one for evening so we can check if we
# have already booked a bus for that part of day
existing_reserved_mornings = []
existing_reserved_evenings = []
for item in existing_reservations:
    if item[""] != "Cancelled":
        # if the datetime is before noon
        if datetime.strptime(item["datetimeISO"], "%Y-%m-%dT%H:%M:%S").hour < 12:
            existing_reserved_mornings.append(item["dateISO"].strftime("%Y-%m-%d"))
        else:
            existing_reserved_evenings.append(item["dateISO"].strftime("%Y-%m-%d"))


# Load configuration from YAML file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Load bus routes and available stops
# these codes can be found by using the chrome app to monitor network traffic when selecting a bus reservation between two stops
# in the request that starts with "times?", the preview pane has items, and items in that list will have value lineID
with open("busroutes.yaml", "r") as file:
    busroutes = yaml.safe_load(file)

# get string format of every date in next week (bar weekends)
next_dates = get_upcoming_dates(start_date=None)


# Function to find the correct route and stop codes based on labels
def find_route_and_stop_code(period, pickup_label, dropoff_label):
    for route_code, route_data in busroutes.items():
        if period in route_data:
            bus_service_data = route_data[period]

            pickup_code = bus_service_data["Stops"].get(pickup_label)
            dropoff_code = bus_service_data["Stops"].get(dropoff_label)

            if pickup_code and dropoff_code:
                return bus_service_data["Service"], pickup_code, dropoff_code
    return None, None, None


for TRAVEL_DATE in next_dates:
    dateISO = datetime.strptime(TRAVEL_DATE, "%Y-%m-%d").date()
    day_name = dateISO.strftime("%A")  # Get day name like Monday, Tuesday, etc.

    # Skip if day not in config
    if day_name not in config["days"]:
        log.info(f"⛔ No configuration for {day_name}. Skipping...")
        continue

    for period in ["AM", "PM"]:
        LINE_ID, PICKUP_ATCOCODE, DROPOFF_ATCOCODE = None, None, None
        bus_service = None

        if period in config["days"][day_name]:
            pickup_label = config["days"][day_name][period].get("pickup")
            dropoff_label = config["days"][day_name][period].get("dropoff")

            if pickup_label and dropoff_label:
                # Find the service and stop codes from busroutes.yaml
                LINE_ID, PICKUP_ATCOCODE, DROPOFF_ATCOCODE = find_route_and_stop_code(
                    period, pickup_label, dropoff_label
                )

        # If either pickup or dropoff codes are missing, skip this period
        if PICKUP_ATCOCODE is None or DROPOFF_ATCOCODE is None:
            log.info(
                f"⛔ No valid configuration for {day_name} {period}. Check spelling on stop names. Skipping..."
            )
            continue

        if not LINE_ID:
            log.error("🚩 could not identify bus route from these stops")
            raise Exception()

        existing_reservations_period = (
            existing_reserved_mornings if period == "AM" else existing_reserved_evenings
        )
        if TRAVEL_DATE in existing_reservations_period:
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
                bus_time, bus_line, PICKUP_ATCOCODE, DROPOFF_ATCOCODE, COOKIE, ticket_id
            )
            if reserved:
                if reserved.ok:
                    break  # break to not book multiple buses for same day
            else:
                break
