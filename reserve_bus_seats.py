#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR
import json
import requests
from requests.structures import CaseInsensitiveDict


def create_headers(api_key, bearer_token):
    headers = CaseInsensitiveDict()
    headers["Authorization"] = bearer_token
    headers["Accept-Language"] = "en-GB;q=1.0, fr-GB;q=0.9, es-GB;q=0.8, he-GB;q=0.7"
    headers["Connection"] = "keep-alive"
    headers["Timezone"] = "Europe/London"
    headers["Accept"] = "application/vnd.ticketless.reservations+json; version=3"
    headers["Host"] = "ticketless-app.api.urbanthings.cloud"
    headers["Content-Type"] = "application/json"
    headers["x-api-key"] = api_key
    headers["X-UT-Firebase-Push-Token"] = "epjBGixdM0LUoLXPGc0v5X:APA91bHZOdFdHu6Lw1nZ7b6HLnAo9UMfAwJ7CBFMyyk0EQVRZ4c8ERrkki3XDadRsrY9MjTJnGOrCiu_orPefFdwMlLUOSMhwxyZsF6umVFItuyYiDtVYAIUeY7LQKuO8--vYBXHNYFz"
    headers["X-UT-App"] = "travel.ticketless.app.richmonds; platform=ios"
    headers["User-Agent"] = "Richmonds/224 CFNetwork/1390 Darwin/22.0.0"
    headers["Content-Type"] = "application/json"
    headers["X-UT-App-Instance-Id"] = "2701E4DC-6379-4394-B308-DCEDE9CEEC97"

    return headers


def get_token(api_key):
    url = "https://ticketless-identity.api.urbanthings.cloud/identity/connect/token"
    headers = CaseInsensitiveDict()
    headers["Host"] = "ticketless-identity.api.urbanthings.cloud"
    headers["Accept"] = "*/*"
    headers["X-UT-Firebase-Push-Token"] = "epjBGixdM0LUoLXPGc0v5X:APA91bHZOdFdHu6Lw1nZ7b6HLnAo9UMfAwJ7CBFMyyk0EQVRZ4c8ERrkki3XDadRsrY9MjTJnGOrCiu_orPefFdwMlLUOSMhwxyZsF6umVFItuyYiDtVYAIUeY7LQKuO8--vYBXHNYFz"
    headers["Accept-Language"] = "en-GB;q=1.0, fr-GB;q=0.9, es-GB;q=0.8, he-GB;q=0.7"
    headers["x-api-key"] = api_key
    headers["X-UT-App"] = "travel.ticketless.app.richmonds; platform=ios"
    headers["User-Agent"] = "Richmonds/224 CFNetwork/1390 Darwin/22.0.0"
    headers["Connection"] = "keep-alive"

    headers["Timezone"] = "Europe/London"
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["X-UT-App-Instance-Id"] = "2701E4DC-6379-4394-B308-DCEDE9CEEC97"
    resp = requests.post(url, headers=headers)
    print(resp.status_code)
    print(resp.text)
    token = json.loads(resp.json())["id_token"]
    return token


def get_reservations(headers):
    url = "https://ticketless-app.api.urbanthings.cloud/api/2/reservations"
    resp = requests.get(url, headers=headers)
    return resp


def process_reservations(resp):
    response_data = json.loads(resp.text)
    # available_trips = []

    for item in response_data['items']:
        print(item)
        # print(item['scheduledTripStartTime'])

    # return available_trips


def create_search_request_body(date, from_stop, to_stop, route_id):
    return {
        "originStopId": from_stop,
        "destinationStopId": to_stop,
        "date": date,
        "passengers": [
            {
                "type": "Adult",
                "count": 1
            },
            {
                "type": "Child",
                "count": 0
            }
        ],
        "reservableRouteId": route_id,
        "direction": "Outbound"
    }


def search_trips(headers, data):
    url = "https://ticketless-app.api.urbanthings.cloud/api/2/reservations/trips"
    resp = requests.post(url, headers=headers, data=data)
    return resp


def process_search_results(resp):
    response_data = json.loads(resp.text)
    available_trips = []

    for item in response_data['items']:
        if item['availableSeats'] > 0:
            available_trips.append({
                "scheduled_trip_start_time": item['scheduledTripStartTime'],
                "scheduled_trip_route_id": item['reservableRouteId'],
                "scheduled_trip_id": item['reservableTripId']
            })

    return available_trips


def create_confirm_request_body(trip_id, route_id, from_stop, to_stop):
    return {
        "items": [
            {
                "originStopId": from_stop,
                "destinationStopId": to_stop,
                "passengers": [
                    {
                        "type": "Adult",
                        "count": 1
                    }
                ],
                "reservableTripId": trip_id,
                "reservableRouteId": route_id
            }
        ]
    }


def confirm_trip(headers, data):
    url = "https://ticketless-app.api.urbanthings.cloud/api/2/reservations/confirm"
    resp = requests.post(url, headers=headers, data=data)
    return resp

def get_upcoming_workdays():
    date = datetime.datetime.now().date()
    days_to_reserve = []
    for i in range(14):
        # Get the date for the current iteration
        current_date = date + datetime.timedelta(days=i)
        next_weekday = current_date + \
            relativedelta(weekday=(MO, TU, WE, TH, FR)[i % 5])

        days_to_reserve.append(next_weekday.strftime('%Y-%m-%d'))
    return days_to_reserve




def main():
    bearer_token = "<BEARER_TOKEN>"
    api_key = "<API_KEY>"

    home_stop = "UK_TNDS_NOC_RCHC_SP_111"  # Hills Rd, Centennial Hotel - S
    work_stop = "UK_TNDS_NOC_RCHC_SP_100"  # Wellcome Genome Campus
    route_ids = ["4fbb703f-f543-4135-afea-dedb2b7249bb",
                 "722bfef1-42fb-44b8-8993-e46ef44b5247"]


    # get list of next 2 weeks of work days
    days_to_reserve = get_upcoming_workdays()
    for day in days_to_reserve:
        print(day)
        headers = create_headers(api_key, bearer_token)

        # loop over possible routes to get latest of all available trips
        available_trips = []
        for route_id in route_ids:
            search_request_body = create_search_request_body(
                day, from_stop=home_stop, to_stop=work_stop, route_id=route_id)
            search_data = json.dumps(search_request_body)

            search_resp = search_trips(headers, search_data)
            print(search_resp.status_code)

            available_trips = available_trips + \
                process_search_results(search_resp)

        # sort all available trips by scheduled_trip_start_time
        available_trips = sorted(
            available_trips, key=lambda k: k['scheduled_trip_start_time'], reverse=True)

        print(available_trips)

        for trip in available_trips:
            confirm_request_body = create_confirm_request_body(
                trip["scheduled_trip_id"], trip["scheduled_trip_route_id"], from_stop=home_stop, to_stop=work_stop)
            confirm_data = json.dumps(confirm_request_body)

            confirm_resp = confirm_trip(headers, confirm_data)
            print(confirm_resp.text)
            break
            if confirm_resp.status_code == 200:
                break  # we only want to confirm the first trip as its the latest available one
        break


if __name__ == "__main__":
    main()
