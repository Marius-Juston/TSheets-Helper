import os

from google_sheets import GoogleSheets
from list_formatting import Formatter

if __name__ == '__main__':
    token = os.environ['TSHEETS_TOKEN']
    print(token)

    # api = TSheetsAPI(token, '2018-06-01')
    # api.get_group_ids()

    formatter = Formatter(token, "info.json")
    info = formatter.run()

    spreadsheet_id = '1eSk-VW24hnpfvbqGCInvkSLFMC5ml7UcrKq1DmObAmY'

    google_sheets = GoogleSheets(spreadsheet_id)
    google_sheets.send_to_google_sheets(formatter)
    google_sheets.open_spreadsheet()
    # driver.quit()
