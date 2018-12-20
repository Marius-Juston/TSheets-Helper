import webbrowser

from googleapiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client import file, client
from oauth2client.tools import run_flow


def cell(row, column) -> str:
    return chr(ord("A") + column) + str(row)


def constant_cell(row, column) -> str:
    return "${}${}".format(chr(ord("A") + column), row)


class GoogleSheets:
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']

    def __init__(self, spreadsheet_id, client_id='assets/client_id.json', storage='assets/storage.json') -> None:
        super().__init__()
        self.spreadsheet_id = spreadsheet_id
        self.storage = storage
        self.client_id = client_id

        self.credentials = self.get_credentials()
        self.service = self.get_service()

        self.green = self.get_color(183 / 255, 225 / 255, 205 / 255)
        self.red = self.get_color(244 / 255, 199 / 255, 195 / 255)
        self.orange = self.get_color(252 / 255, 232 / 255, 178 / 255)

        self.clean_up_sheet()

    def get_credentials(self):

        store = file.Storage(self.storage)
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(self.client_id, self.SCOPES)
            creds = run_flow(flow, store)

        return creds

    def get_service(self):
        return discovery.build('sheets', 'v4', credentials=self.credentials)

    def update_value(self, values: list, range_: str = None,
                     value_input_option='USER_ENTERED'):
        value_range_body = {
            "values":
                values
        }

        if range_ is None:
            range_ = self.get_string_range(values)

        request = self.service.spreadsheets().values().update(spreadsheetId=self.spreadsheet_id, range=range_,
                                                              valueInputOption=value_input_option,
                                                              body=value_range_body)
        return request.execute()

    def send_to_google_sheets(self, formatter):
        response = self.update_value(formatter.values)

        # TODO use the formulas above to make it even more dynamic for dates
        self.clean_up_sheet()
        print(formatter.check_date_row, formatter.check_date_column)

        self.format_sheet(formatter.outreach_cell, formatter.participation_cell, formatter.check_column_index,
                          formatter.outreach_column, formatter.participation_column,
                          formatter.check_date_row, formatter.check_date_column, formatter.offset)

    def format_sheet(self, outreach_cell, participation_cell, check_column_index,
                     outreach_column,
                     participation_column, check_date_row, check_date_column, calculated_offset=3):
        reqs = self.formatting(outreach_cell, participation_cell, check_column_index, outreach_column,
                               participation_column,
                               check_date_row, check_date_column,
                               filter_stop_column=check_column_index + calculated_offset,
                               offset=calculated_offset)
        return self.run_batch_update(reqs)

    def clean_up_sheet(self):
        reqs = self.clean_up_formatting()

        try:
            res = self.run_batch_update(reqs)
            return True
        except HttpError:
            return False

    def formatting(self, outreach_cell, participation_cell, check_column, outreach_column, participation_column,
                   check_date_row,
                   check_date_column,
                   filter_stop_column=0, offset=3):
        equation = '=AND(${1}1<{0},NOT(${1}1=""))'

        outreach_column_name = chr(ord('A') + outreach_column)
        participation_column_name = chr(ord('A') + participation_column)

        check_column_c = check_column + offset
        outreach_column_c, participation_column_c = outreach_column + offset, participation_column + offset
        outreach_column_name_c = chr(ord('A') + outreach_column_c)
        participation_column_name_c = chr(ord('A') + participation_column_c)

        print(outreach_cell, participation_cell, outreach_column_name_c, check_column, outreach_column,
              participation_column)

        reqs = {'requests': [
            self.__add_freeze_row(),
            self.__add_freeze_col(),
            self.__add_bold_row(),

            self.__add_text_condition("TEXT_CONTAINS", "GOOD", self.green, check_column),
            self.__add_text_condition("TEXT_CONTAINS", "PARTICIPATION", self.orange, check_column),
            self.__add_text_condition("TEXT_CONTAINS", "OUTREACH", self.orange, check_column),
            self.__add_text_condition("TEXT_CONTAINS", "BOTH", self.red, check_column),

            self.__add_filter(filter_stop_column),

            self.__add_custom_condition(equation.format(outreach_cell, outreach_column_name), self.red,
                                        outreach_column),
            self.__add_custom_condition(equation.format(participation_cell, participation_column_name), self.orange,
                                        participation_column),

            self.__add_text_condition("TEXT_CONTAINS", "GOOD", self.green, check_column_c),
            self.__add_text_condition("TEXT_CONTAINS", "PARTICIPATION", self.orange, check_column_c),
            self.__add_text_condition("TEXT_CONTAINS", "OUTREACH", self.orange, check_column_c),
            self.__add_text_condition("TEXT_CONTAINS", "BOTH", self.red, check_column_c),

            self.__add_custom_condition(equation.format(outreach_cell, outreach_column_name_c), self.red,
                                        outreach_column_c),
            self.__add_custom_condition(equation.format(participation_cell, participation_column_name_c), self.orange,
                                        participation_column_c),

            self.__add_date_format(check_date_row, check_date_column)
        ]}

        return reqs

    @staticmethod
    def get_string_range(data_list: list, start=None):
        rows = len(data_list)
        cols = len(data_list[0])

        if start is None:
            start = cell(1, 0)

        end = cell(int(start[1]) + rows - 1, ord(start[0]) - ord('A') + cols - 1)

        return "{}:{}".format(start, end)

    def run_batch_update(self, reqs):
        return self.service.spreadsheets().batchUpdate(spreadsheetId=self.spreadsheet_id, body=reqs).execute()

    def clean_up_formatting(self):
        request = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id, includeGridData=False)
        response = request.execute()

        number_of_conditionals = 0

        if "conditionalFormats" in response["sheets"][0]:
            number_of_conditionals = len(response["sheets"][0]['conditionalFormats'])

        return {
            "requests": [
                *self.__delete_previous_conditions(number_of_conditionals)
            ]
        }

    @staticmethod
    def __delete_previous_conditions(number_of_conditionals) -> list:
        return [
            {
                "deleteConditionalFormatRule": {
                    "index": 0,
                }
            }
            for _ in range(number_of_conditionals)
        ]

    @staticmethod
    def __add_filter(filter_column):
        return {"setBasicFilter": {
            "filter": {
                # "title": title,
                # "filterViewId": 10,

                "range": {
                    # "startColumnIndex": filter_column,
                    "endColumnIndex": filter_column + 1

                    # TODO make it so that a column range can be set, right now if there is a filter it will be replaced
                },
                "sortSpecs": [
                    # {
                    #     "dimensionIndex": filter_column,
                    #     "sortOrder": "ASCENDING"
                    # }
                ],
                "criteria": {
                    0: {"hiddenValues": [
                        ""
                    ]}
                }
            }
        }}

    @staticmethod
    def __add_date_format(check_date_row, check_date_column):
        return {
            "repeatCell": {
                "range": {
                    "startRowIndex": check_date_row,
                    "endRowIndex": check_date_row + 1,
                    "startColumnIndex": check_date_column,
                    "endColumnIndex": check_date_column + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": "DATE",
                        }
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        }

    @staticmethod
    def __add_bold_row(start_row=0, end_row=1):
        return {'repeatCell': {
            'range': {
                'startRowIndex': start_row,
                'endRowIndex': end_row
            },
            'cell':
                {'userEnteredFormat':
                     {'textFormat':
                          {'bold': True
                           }
                      }
                 },
            'fields': 'userEnteredFormat.textFormat.bold',
        }}

    @staticmethod
    def __add_freeze_row(number_of_rows=1):
        return {'updateSheetProperties': {
            'properties':
                {'gridProperties':
                     {'frozenRowCount': number_of_rows},
                 },
            'fields': 'gridProperties.frozenRowCount'
        }}

    @staticmethod
    def __add_freeze_col(number_of_columns=1):
        return {'updateSheetProperties': {
            'properties':
                {'gridProperties':
                     {'frozenColumnCount': number_of_columns},
                 },
            'fields': 'gridProperties.frozenColumnCount'
        }}

    @staticmethod
    def __add_text_condition(conditional, value, color: dict, check_column, index=0):
        return {"addConditionalFormatRule": {
            "rule": {
                "ranges": [
                    {
                        "startColumnIndex": check_column,
                        "endColumnIndex": check_column + 1,
                    }
                ],
                "booleanRule": {
                    "condition": {
                        "type": conditional,
                        "values": [
                            {
                                "userEnteredValue": value
                            }
                        ]
                    },
                    "format": color
                }
            },
            "index": index
        }}

    @staticmethod
    def get_color(red, green, blue):
        return {
            "backgroundColor": {
                "blue": blue,
                "green": green,
                "red": red
            }
        }

    @staticmethod
    def __add_custom_condition(equation, color, column, index=0):
        return {"addConditionalFormatRule": {
            "rule": {
                "ranges": [
                    {
                        "startColumnIndex": column,
                        "endColumnIndex": column + 1,
                    }
                ],
                "booleanRule": {
                    "condition": {
                        "type": "CUSTOM_FORMULA",
                        "values": [
                            {
                                "userEnteredValue": equation
                            }
                        ]
                    },
                    "format": color
                }
            },
            "index": index
        }}

    def open_spreadsheet(self):
        url = 'https://docs.google.com/spreadsheets/d/{}'.format(self.spreadsheet_id)

        # MacOS
        # chrome_path = 'open -a /Applications/Google\ Chrome.app %s'

        # Windows
        chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

        # Linux
        # chrome_path = '/usr/bin/google-chrome %s'

        webbrowser.get(chrome_path).open(url)
