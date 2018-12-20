import os

import pandas as pd
import requests


def get(url, filters=None, header=None):
    response = requests.api.get(url, params=filters, headers=header)
    response.raise_for_status()

    return response


def post(url, data=None, json=None, header=None):
    response = requests.api.post(url, data=data, json=json, headers=header)
    response.raise_for_status()

    return response


class TSheetsAPI:

    def __init__(self, tsheets_token, start_date, end_date=None, group_names=("Students",)) -> None:
        super().__init__()
        self.end_date = end_date
        self.start_date = start_date
        self.auth_options = {"Authorization": "Bearer {}".format(tsheets_token)}
        self.group_names = group_names

        self.groups_url = "https://rest.tsheets.com/api/v1/groups"
        self.users_url = "https://rest.tsheets.com/api/v1/users"
        self.timesheets_url = 'https://rest.tsheets.com/api/v1/timesheets'
        self.jobcodes_url = 'https://rest.tsheets.com/api/v1/jobcodes'

        self.group_ids = None

    def get(self, url, filters=None):
        return get(url, filters, header=self.auth_options)

    def post(self, url, data=None, json=None):
        return post(url, data=data, json=json, header=self.auth_options)

    def get_group_ids(self):
        group_filter = {
            "names": ",".join(self.group_names),
            "supplemental_data": "no"
        }

        group_ids = self.get(self.groups_url, group_filter).json()
        group_ids = tuple(group_ids["results"]["groups"])

        return group_ids

    def get_users(self):
        if self.group_ids is None:
            self.group_ids = self.get_group_ids()

        user_filters = {
            "supplemental_data": "no"
        }

        if self.group_ids is not None:
            user_filters["group_ids"] = ",".join(self.group_ids)

        users = self.get(self.users_url, filters=user_filters)
        return users.json()["results"]["users"]

    def users_to_dataframe(self):
        return pd.DataFrame(self.user_to_list(), columns=["id", "name", "email"])

    def user_to_list(self):
        users = self.get_users()
        data = []

        for key, value in users.items():
            name = " ".join([value["first_name"], value["last_name"]])
            email_address = value['email']
            data.append([key, name, email_address])

        return data

    def timesheets_to_dateframe(self):
        return pd.DataFrame(self.timesheets_to_list(), columns=["id", "date", "duration", 'jobcode_id'])

    def timesheets_to_list(self):
        timesheets = self.get_timesheets()
        data = []

        for key, value in timesheets.items():
            user_id = value["user_id"]
            date = value["date"]
            duration = value["duration"]
            job_code = value["jobcode_id"]

            data.append([key, user_id, date, duration, job_code])

        return data

    def get_timesheets(self):
        if self.group_ids is None:
            self.group_ids = self.get_group_ids()

        timesheet_filters = {
            "group_ids": ",".join(self.group_ids),
            "start_date": self.start_date,
            "supplemental_data": "no"
        }

        if self.end_date is not None:
            # now = datetime.now().strftime("%Y-%m-%d")
            timesheet_filters["end_date"] = self.end_date

        data = {}

        page_number = 1
        while True:
            timesheet_filters["page"] = page_number

            users = self.get(self.timesheets_url, filters=timesheet_filters)
            response = users.json()["results"]["timesheets"]

            if not response:
                break
            else:
                print(page_number)
                page_number += 1
                data.update(response)

        return data

    def get_jobcodes(self):

        jobcode_filters = {
            "supplemental_data": "no"
        }

        data = {}

        page_number = 1
        while True:
            jobcode_filters["page"] = page_number

            users = self.get(self.jobcodes_url, filters=jobcode_filters)
            response = users.json()["results"]["jobcodes"]

            if not response:
                break
            else:
                print(page_number)
                page_number += 1
                data.update(response)

        return data

    def jobcodes_to_list(self):
        jobcodes = self.get_jobcodes()
        data = []

        for value in jobcodes.values():
            id = value["id"]
            parent_id = value["parent_id"]
            name = value["name"]

            data.append([id, parent_id, name])

        return data


if __name__ == '__main__':
    from stored_data import TSheetsCache

    token = os.environ['TSHEETS_TOKEN']
    start_date = "2018-06-01"

    excluded_hours = {
        "Garden City": {
            "start": "2018-07-15",
            "end": "2018-07-20"
        },
        "Dobbins Air Force Camp": {
            "start": "2018-07-08",
            "end": "2018-07-12"
        }
    }

    tsheets_api = TSheetsAPI(token, start_date)
    with TSheetsCache(excluded_date_ranges=excluded_hours) as database:
        if database.needs_update(database.users_table):
            people = tsheets_api.user_to_list()
            success = database.insert_users(people)
            database.add_time_stamp(database.users_table, success)

        if database.needs_update(database.jobcodes_table):
            jobcodes = tsheets_api.jobcodes_to_list()
            success = database.insert_jobcodes(jobcodes)
            database.add_time_stamp(database.jobcodes_table, success)

        if database.needs_update(database.timesheets_table):
            timesheets = tsheets_api.timesheets_to_list()
            success = database.insert_timesheets(timesheets)
            database.add_time_stamp(database.timesheets_table, success)

        hours = database.fetch_outreach_participation_hours()

        print(hours)
