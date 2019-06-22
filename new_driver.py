import argparse

from google_sheets import GoogleSheets
from list_formatting import Runner


def get_input_args():
    # Creates Argument Parser object named parser
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', "--token", required=True, type=str, help="The TSheets token to be able to use the API")
    parser.add_argument('-n', "--notification", type=int,
                        help="If you want to send notifications or not (0 for false, 1 for true)")
    parser.add_argument("-s", '--spreadsheet_id', type=str, help="The google sheets id to paste the information to")

    return parser


if __name__ == '__main__':
    args = get_input_args().parse_args()

    print(args.token)
    print(args.notification)

    formatter = Runner(args.token, "info.json")
    info = formatter.run()

    spreadsheet_id = formatter.info['spreadsheet_id']

    if args.spreadsheet_id is not None:
        spreadsheet_id = args.spreadsheet_id

    google_sheets = GoogleSheets(spreadsheet_id)
    google_sheets.send_to_google_sheets(formatter)
    google_sheets.open_spreadsheet()

    if args.notification:
        print("Sent notifications")
        formatter.compose_and_send_notifications(google_sheets)
