import os
from datetime import datetime

import pandas as pd
import requests

from stored_data import TSheetsCache


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


def users_to_dataframe(users):
    return pd.DataFrame(user_to_list(users), columns=["id", "name", "email"])


def user_to_list(users):
    data = []

    for key, value in users.items():
        name = " ".join([value["first_name"], value["last_name"]])
        email_address = value['email']
        data.append([key, name, email_address])

    return data


def timesheets_to_dateframe(timesheets: dict):
    return pd.DataFrame(timesheets_to_list(timesheets), columns=["id", "date", "duration", 'jobcode_id'])


def timesheets_to_list(timesheets):
    data = []

    for key, value in timesheets.items():
        user_id = value["user_id"]
        date = value["date"]
        duration = value["duration"]
        job_code = value["jobcode_id"]

        data.append([key, user_id, date, duration, job_code])

    return data


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


def get_jobcodes():
    url = 'https://rest.tsheets.com/api/v1/jobcodes'

    jobcode_filters = {
        "supplemental_data": "no"
    }

    data = {}

    page_number = 1
    while True:
        jobcode_filters["page"] = page_number

        users = get(url, filters=jobcode_filters, header=auth_options)
        response = users.json()["results"]["jobcodes"]

        if not response:
            break
        else:
            print(page_number)
            page_number += 1
            data.update(response)

    return data


def jobcodes_to_list(jobcodes):
    data = []

    for value in jobcodes.values():
        id = value["id"]
        parent_id = value["parent_id"]
        name = value["name"]

        data.append([id, parent_id, name])

    return data


if __name__ == '__main__':
    token = os.environ['TSHEETS_TOKEN']
    auth_options = {"Authorization": "Bearer {}".format(token)}
    start_date = "2018-01-06"

    with TSheetsCache() as database:
        ids = None

        if database.needs_update(database.users_table):
            ids = get_group_ids()

            people = get_users(ids)
            people = user_to_list(people)
            success = database.insert_users(people)
            database.add_time_stamp(database.users_table, success)

        if database.needs_update(database.jobcodes_table):
            jobcodes = get_jobcodes()
            jobcodes = jobcodes_to_list(jobcodes)
            success = database.insert_jobcodes(jobcodes)
            database.add_time_stamp(database.jobcodes_table, success)

        if database.needs_update(database.timesheets_table):
            if ids is None:
                ids = get_group_ids()

            start_time = datetime.now()
            timesheets = get_timesheets(ids, start_date)
            print((datetime.now() - start_time).total_seconds())
            print(len(timesheets))

            timesheets = timesheets_to_list(timesheets)
            success = database.insert_timesheets(timesheets)
            database.add_time_stamp(database.timesheets_table, success)
