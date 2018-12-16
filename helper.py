def clean_up_formatting(service, spreadsheet_id):
    request = service.spreadsheets().get(spreadsheetId=spreadsheet_id, includeGridData=False)
    response = request.execute()

    number_of_conditionals = 0

    if "conditionalFormats" in response["sheets"][0]:
        number_of_conditionals = len(response["sheets"][0]['conditionalFormats'])

    return {
        "requests": [
            *delete_previous_conditions(number_of_conditionals)
        ]
    }


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


green = get_color(183 / 255, 225 / 255, 205 / 255)
red = get_color(244 / 255, 199 / 255, 195 / 255)
orange = get_color(252 / 255, 232 / 255, 178 / 255)
