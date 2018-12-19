from datetime import datetime

import requests


def get(url, filters=None, header=None):
    response = requests.api.get(url, params=filters, headers=header)
    response.raise_for_status()

    return response


def get_group_ids(group_names=("Students",)):
    url = "https://rest.tsheets.com/api/v1/groups"

    # group_names = ["Students", "Mentors"]

    group_filter = {
        "names": ",".join(group_names),
        "supplemental_data": "no"
    }

    group_ids = get(url, filters=group_filter, header=auth_options).json()
    group_ids = tuple(group_ids["results"]["groups"])

    return group_ids


def get_users(groups_ids=None):
    url = "https://rest.tsheets.com/api/v1/users"

    user_filters = {
        "supplemental_data": "no"
    }

    if groups_ids is not None:
        user_filters["group_ids"] = ",".join(groups_ids)

    users = get(url, filters=user_filters, header=auth_options)
    return users.json()["results"]["users"]


import pandas as pd


def users_to_dataframe(users):
    data = []

    for key, value in users.items():
        name = " ".join([value["first_name"], value["last_name"]])
        email_address = value['email']
        data.append([key, name, email_address])

    return pd.DataFrame(data, columns=["id", "name", "email"])


def timesheets_to_dateframe(timesheets: dict):
    data = []

    for value in timesheets.values():
        user_id = value["user_id"]
        date = value["date"]
        duration = value["duration"]
        job_code = value["jobcode_id"]

        data.append([user_id, date, duration, job_code])

    return pd.DataFrame(data, columns=["id", "date", "duration", 'jobcode_id'])


def get_timesheets(group_ids, start_date, end_date=None):
    url = 'https://rest.tsheets.com/api/v1/timesheets'

    timesheet_filters = {
        "group_ids": ",".join(group_ids),
        "start_date": start_date,
        "supplemental_data": "no"
    }

    if end_date is not None:
        # now = datetime.now().strftime("%Y-%m-%d")
        timesheet_filters["end_date"] = end_date

    data = {}

    page_number = 1
    while True:
        timesheet_filters["page"] = page_number

        users = get(url, filters=timesheet_filters, header=auth_options)
        response = users.json()["results"]["timesheets"]

        if not response:
            break
        else:
            print(page_number)
            page_number += 1
            data.update(response)

    return data


import os

if __name__ == '__main__':
    token = os.environ['TSHEETS_TOKEN']
    auth_options = {"Authorization": "Bearer {}".format(token)}

    ids = get_group_ids()
    # print(ids)
    people = get_users(ids)
    # pprint(people)
    people = users_to_dataframe(people)
    # print(people)

    start_date = "2018-01-06"

    start_time = datetime.now()
    timesheets = get_timesheets(ids, start_date)
    # pprint(timesheets)
    print((datetime.now() - start_time).total_seconds())
    print(len(timesheets))

    timesheets = timesheets_to_dateframe(timesheets)
    print(timesheets)
