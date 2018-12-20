import json

import pandas as pd

from google_sheets import cell, constant_cell
from stored_data import TSheetsCache
from tsheets_retriever import TSheetsAPI


class Runner:
    dynamic_date_formula = '=ARRAYFORMULA(IFERROR(MIN(FILTER({0}, {0}-NOW()>0)), FILTER({0},{0}-NOW()=MIN({0}-NOW()))))'
    hours_finding_formula = '=INDEX({4}:{5},MATCH("{0}",{6}:{6}),MATCH({3},TRANSPOSE({1}:{2}),0))'
    outreach_equation = '=MIN({},{})'
    participation_equation = '={1}+IF({2}>{0},{2}-{0},0)'
    if_statement = '=IF(AND({2}<{0},{3}<{1}),"BOTH",IF({2}<{0},"OUTREACH",IF({3}<{1},"PARTICIPATION","GOOD")))'

    def __init__(self, tsheets_token, info_json, participation_row=4, participation_column=2,
                 outreach_row=3, outreach_column=1, date_row=2) -> None:
        super().__init__()
        self.date_row = date_row
        self.participation_column = participation_column
        self.outreach_column = outreach_column
        self.outreach_row = outreach_row
        self.participation_row = participation_row
        self.info_json = info_json
        self.info = self.retrieve_checks()

        self.tsheets_api = TSheetsAPI(tsheets_token, self.info['start_date'])

        self.hours = None
        self.values = None
        self.check_column_index, self.check_date_row, self.check_date_column = 0, 0, 0
        self.check_date_row, self.check_date_column = 0, 0

        self.check_column = self.get_check_column()
        self.outreach_cell, self.participation_cell = self.get_outreach_participation_cell()

    def run(self):
        self.collect_hours()
        # print(self.hours)
        self.sort_hours(["Outreach", "Participation"])
        # print(self.hours)
        self.add_extra_info()
        print(self.hours)
        self.values = self.to_list()
        return self.values

    def collect_hours(self):
        with TSheetsCache(excluded_date_ranges=self.info['excluded_hours']) as database:
            if database.needs_update(database.users_table):
                people = self.tsheets_api.user_to_list()
                success = database.insert_users(people)
                database.add_time_stamp(database.users_table, success)

            if database.needs_update(database.jobcodes_table):
                jobcodes = self.tsheets_api.jobcodes_to_list()
                success = database.insert_jobcodes(jobcodes)
                database.add_time_stamp(database.jobcodes_table, success)

            if database.needs_update(database.timesheets_table):
                timesheets = self.tsheets_api.timesheets_to_list()
                success = database.insert_timesheets(timesheets)
                database.add_time_stamp(database.timesheets_table, success)

            self.hours = database.fetch_outreach_participation_hours()

    def to_list(self) -> list:
        data = self.hours.fillna("").values.tolist()
        column_header = list(self.hours)
        data.insert(0, column_header)

        return data

    def sort_hours(self, sorting_order):
        if self.hours is not None:
            self.hours = self.hours.sort_values(by=sorting_order).reset_index(drop=True)

    def retrieve_checks(self):
        with open(self.info_json, 'r') as file:
            return json.load(file)

    def get_outreach_participation_cell(self):
        column_name = self.check_column + 1
        outreach_cell = constant_cell(self.outreach_row, column_name)
        participation_cell = constant_cell(self.participation_row, column_name)

        return outreach_cell, participation_cell

    def get_check_column(self):
        return 1 + 3 + 3 + len(self.info['hours_check'])

    def add_extra_info(self):
        self.add_hours_check()
        self.check_column_index = len(self.hours.columns) - 1

        self.add_maxed_hours()
        self.add_hours_check(column_name="Check Calculated")

        self.add_hours_constrains()
        start_date_column = len(self.hours.columns) - len(self.info['hours_check'])
        end_date_column = len(self.hours.columns) - 1

        self.add_dynamic_hours(start_date_column, end_date_column)

    def add_maxed_hours(self):

        equation = [
            self.outreach_equation.format(self.outreach_cell, cell(i, self.outreach_column))
            for i in range(2, len(self.hours) + 2)
        ]

        self.hours = self.hours.assign(Outreach_Calculated=pd.Series(equation))

        equation = [
            self.participation_equation.format(self.outreach_cell, cell(i, self.participation_column),
                                               cell(i, self.outreach_column))
            for i in range(2, len(self.hours) + 2)
        ]

        self.hours = self.hours.assign(Participation_Calculated=pd.Series(equation))

    def add_hours_check(self, column_name="Check") -> (pd.DataFrame, str, str):

        equation = [
            self.if_statement.format(self.outreach_cell, self.participation_cell, cell(i, self.outreach_column),
                                     cell(i, self.participation_column))
            for i in range(2, len(self.hours) + 2)
        ]

        self.hours = pd.concat((self.hours, pd.Series(equation, name=column_name)), axis=1)

    def add_hours_constrains(self):
        if len(self.info['hours_check']) > 0:
            self.hours = pd.concat([self.hours, pd.Series(["Date", "Outreach", "Participation"], name="Event")], axis=1)

        for check in self.info['hours_check']:
            self.hours = pd.concat([self.hours, pd.Series([self.info['hours_check'][check]["date"],
                                                           self.info['hours_check'][check]["outreach"],
                                                           self.info['hours_check'][check]["participation"]],
                                                          name=check)],
                                   axis=1)

    def add_dynamic_hours(self, start_date_column, end_date_column):
        start_cell = constant_cell(self.date_row, start_date_column)
        end_cell = constant_cell(self.date_row, end_date_column)

        filled_dynamic_date_formula = self.dynamic_date_formula.format("{}:{}".format(start_cell, end_cell))

        start_cell = constant_cell(1, start_date_column)

        check_date_row, check_date_column = self.date_row, end_date_column + 1
        dynamic_date_cell = constant_cell(check_date_row, check_date_column)

        self.check_date_row, self.check_date_column, = check_date_row - 1, check_date_column

        end_search_cell = constant_cell(4, end_date_column)
        title_column = "${}".format(chr(ord('A') + start_date_column - 1))

        transpose_start = constant_cell(2, start_date_column)
        transpose_end = constant_cell(self.date_row, end_date_column)

        self.hours = pd.concat([self.hours, pd.Series([
            filled_dynamic_date_formula,
            self.hours_finding_formula.format("Outreach", transpose_start, transpose_end, dynamic_date_cell, start_cell,
                                              end_search_cell, title_column),
            self.hours_finding_formula.format("Participation", transpose_start, transpose_end, dynamic_date_cell,
                                              start_cell,
                                              end_search_cell, title_column),
        ], name="Checked Date")], axis=1)
