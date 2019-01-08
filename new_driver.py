import os

from google_sheets import GoogleSheets
from list_formatting import Runner

if __name__ == '__main__':
    token = os.environ['TSHEETS_TOKEN']
    print(token)

    formatter = Runner(token, "info.json")
    info = formatter.run()

    spreadsheet_id = '1eSk-VW24hnpfvbqGCInvkSLFMC5ml7UcrKq1DmObAmY'

    google_sheets = GoogleSheets(spreadsheet_id)
    google_sheets.send_to_google_sheets(formatter)
    google_sheets.open_spreadsheet()

    print(os.environ['SEND_NOTIFICATIONS'])
    if os.environ['SEND_NOTIFICATIONS'] == "1":
        print("Sent notifications")
        formatter.compose_and_send_notifications(google_sheets)
