import gspread
import pandas as pd
from gspread import Worksheet
from oauth2client.service_account import ServiceAccountCredentials


def get_string_range(data_list: list, start='A1'):
    rows = len(data_list)
    cols = len(data_list[0])

    end = "{}{}".format(chr(ord(start[0]) + cols - 1), int(start[1]) + rows - 1)

    return "{}:{}".format(start, end)


def get_range(sheet: Worksheet, information: pd.DataFrame):
    data = information.values.tolist()
    column_header = list(information)
    data.insert(0, column_header)

    rows = len(data)
    cols = len(column_header)

    cell_range = sheet.range(get_string_range(data))

    for r in range(rows):
        for c in range(cols):
            cell_range[r * rows + c].value = data[r][c]

    return cell_range


if __name__ == '__main__':
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name("client_id.json", scope)
    client = gspread.authorize(credentials)

    sheet = client.open("Test").sheet1

    c = get_range(sheet, pd.DataFrame([['hello', "cheese"]], columns=["A", "B"]))
    sheet.update_cells(c)
    # Select a range
    # cell_list = sheet.range('A1:C7')

    # for cell in cell_list:
    #     cell.value = 'O_o'

    # Update in batch
    # sheet.update_cells(cell_list)
