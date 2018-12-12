"""
BEFORE RUNNING:
---------------
1. If not already done, enable the Google Sheets API
   and check the quota for your project at
   https://console.developers.google.com/apis/api/sheets
2. Install the Python client library for Google APIs by running
   `pip install --upgrade google-api-python-client`
"""

from googleapiclient import discovery
from googleapiclient.discovery import Resource
from oauth2client import file, client
from oauth2client.tools import run_flow

from googlesheets.simple_sending import get_string_range


def get_credentials():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']

    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = run_flow(flow, store)

    return creds


def get_service(credentials):
    return discovery.build('sheets', 'v4', credentials=credentials)


def update_value(service: Resource, spreadsheet_id: str, values: list, range_: str = None,
                 value_input_option='USER_ENTERED'):
    value_range_body = {
        "values":
            values

    }

    if range_ is None:
        range_ = get_string_range(values)

    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_,
                                                     valueInputOption=value_input_option, body=value_range_body)
    return request.execute()


# values = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
# response = update_value(service, spreadsheet_id, values)


def add_freeze_col(number_of_columns=1):
    return {'updateSheetProperties': {
        'properties':
            {'gridProperties':
                 {'frozenColumnCount': number_of_columns},
             },
        'fields': 'gridProperties.frozenColumnCount'
    }}


def add_freeze_row(number_of_rows=1):
    return {'updateSheetProperties': {
        'properties':
            {'gridProperties':
                 {'frozenRowCount': number_of_rows},
             },
        'fields': 'gridProperties.frozenRowCount'
    }}


def add_bold_row(start_row=0, end_row=1):
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


index = 0


def add_custom_condition(equation, color, column, index=0):
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


def get_color(red, green, blue):
    return {
        "backgroundColor": {
            "blue": blue,
            "green": green,
            "red": red
        }
    }


def add_text_condition(conditional, value, color: dict, check_column, index=0):
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


green = get_color(183 / 255, 225 / 255, 205 / 255)
red = get_color(244 / 255, 199 / 255, 195 / 255)
orange = get_color(252 / 255, 232 / 255, 178 / 255)


def delete_previous_conditions(number_of_conditionals) -> list:
    return [
        {
            "deleteConditionalFormatRule": {
                "index": 0,
            }
        }
        for _ in range(number_of_conditionals)
    ]


def add_filter(filter_column):
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


def add_date_format(check_date_row, check_date_column):
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


def formatting(outreach_cell, participation_cell, check_column, outreach_column, participation_column, check_date_row,
               check_date_column,
               filter_stop_column=0):
    equation = '=AND(${1}1<{0},NOT(${1}1=""))'

    outreach_column_name = chr(ord('A') + outreach_column)
    participation_column_name = chr(ord('A') + participation_column)

    print(outreach_cell, participation_cell, check_column, outreach_column, participation_column)

    reqs = {'requests': [
        add_freeze_row(),
        add_freeze_col(),
        add_bold_row(),

        add_text_condition("TEXT_CONTAINS", "GOOD", green, check_column),
        add_text_condition("TEXT_CONTAINS", "PARTICIPATION", orange, check_column),
        add_text_condition("TEXT_CONTAINS", "OUTREACH", orange, check_column),
        add_text_condition("TEXT_CONTAINS", "BOTH", red, check_column),

        add_filter(filter_stop_column),

        add_custom_condition(equation.format(outreach_cell, outreach_column_name), red, outreach_column),
        add_custom_condition(equation.format(participation_cell, participation_column_name), orange,
                             participation_column),

        add_date_format(check_date_row, check_date_column)
    ]}

    return reqs


def clean_up_formatting(service, spreadsheet_id):
    request = service.spreadsheets().get(spreadsheetId=spreadsheet_id, includeGridData=False)
    response = request.execute()
    print(response)

    number_of_conditionals = 0

    if "conditionalFormats" in response["sheets"][0]:
        number_of_conditionals = len(response["sheets"][0]['conditionalFormats'])

    return {
        "requests": [
            *delete_previous_conditions(number_of_conditionals)
        ]
    }


if __name__ == '__main__':
    credentials = get_credentials()
    service = get_service(credentials)

    spreadsheet_id = '1eSk-VW24hnpfvbqGCInvkSLFMC5ml7UcrKq1DmObAmY'

    #
    reqs = formatting("$F$2", "$F$3", 3, 1, 2, "N2", 10)
    #
    res = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=reqs).execute()
    #
    # reqs = formatting("$F$2", "$F$3", 6, 4, 5, 2)
    #
    # res = service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=reqs).execute()
