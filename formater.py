"""
BEFORE RUNNING:
---------------
1. If not already done, enable the Google Sheets API
   and check the quota for your project at
   https://console.developers.google.com/apis/api/sheets
2. Install the Python client library for Google APIs by running
   `pip install --upgrade google-api-python-client`
"""

# from driver import formatting

# values = [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]]
# response = update_value(service, spreadsheet_id, values)
from driver import get_credentials, get_service, formatting

if __name__ == '__main__':
    credentials = get_credentials()
    service = get_service(credentials)

    spreadsheet_id = '1eSk-VW24hnpfvbqGCInvkSLFMC5ml7UcrKq1DmObAmY'

    #
    reqs = formatting("$F$2", "$F$3", 3, 1, 2, 1, 14, 5)

    # clean_up_formatting(service, spreadsheet_id)
    res = service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=reqs).execute()
    #
    # reqs = formatting("$F$2", "$F$3", 6, 4, 5, 2)
    #
    # res = service.spreadsheets().batchUpdate(
    #     spreadsheetId=spreadsheet_id, body=reqs).execute()
