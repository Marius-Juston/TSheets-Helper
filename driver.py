import os
import webbrowser
from datetime import datetime

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup, Tag
from googleapiclient import discovery
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from oauth2client import file, client
from oauth2client.tools import run_flow
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

from googlesheets.formater import formatting, clean_up_formatting
from googlesheets.simple_sending import get_string_range

login_page = "https://waltonroboticsteam.tsheets.com/page/login"
username = os.environ['TSHEETS_USERNAME']  # See run configuration for environment variables
password = os.environ['TSHEETS_PASSWORD']  # See run configuration for environment variables
# TODO https://slackapi.github.io/python-slackclient/basic_usage.html#sending-a-message make it so that it sends
#  a message when finishing

start_date = "6/01/2018"

participation = "Participation"
training = "Training"
outreach = "O&S"

spreadsheet_id = '1eSk-VW24hnpfvbqGCInvkSLFMC5ml7UcrKq1DmObAmY'

hours_check = {
    "pre-GRITS": {
        "date": "2018-10-12",
        "outreach": 10,
        "participation": 25
    },
    "pre-Build": {
        "date": "2018-12-10",
        "outreach": 35,
        "participation": 50
    },
    "Districts": {
        "date": "2018-12-20",
        "outreach": 35,
        "participation": 80
    },
    "States": {
        "date": "2019-2-10",
        "outreach": 35,
        "participation": 80
    },
    "Championships": {
        "date": "2019-3-10",
        "outreach": 35,
        "participation": 80
    }
}

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

participation_row = 4
outreach_row = 3

dynamic_date_formula = '=ARRAYFORMULA(IFERROR(MIN(FILTER({0}, {0}-NOW()>0)), FILTER({0},{0}-NOW()=MIN({0}-NOW()))))'

# =ARRAYFORMULA(IFERROR(MIN(FILTER(H2:L2, H2:L2-NOW()>0)), FILTER(H2:L2,H2:L2-NOW()=MIN(H2:L2-NOW()))))

hours_finding_formula = '=INDEX({3}:{4},MATCH("{0}",H:H),MATCH({2},TRANSPOSE({1}:{1}),0))'


# =INDEX($A$1:$L$4,MATCH("Outreach",H:H),MATCH($N$2,TRANSPOSE($2:$2),0))
# =INDEX($A$1:$L$4,MATCH("Participation",H:H),MATCH($N$2,TRANSPOSE($2:$2),0))

def select_option(select: Select, choice):
    for o in select.options:
        if o.text == choice:
            return o


def job_transform(job_category: str):
    if job_category.startswith(outreach):
        return 0
    else:
        return 1


def find_id_and_click(driver: WebDriver, page_id: str):
    input_element = driver.find_element_by_id(page_id)
    input_element.click()
    return


def complete_login_page(driver: WebDriver):
    input_element = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'username')))
    input_element.send_keys(username)

    input_element = driver.find_element_by_id("password")
    input_element.send_keys(password)
    input_element.submit()


def open_payroll_filters(driver: WebDriver):
    input_element = WebDriverWait(driver, delay).until(EC.presence_of_element_located((By.ID, 'reports_shortcut')))
    input_element.click()

    find_id_and_click(driver, "reporting_payroll_shortcut")


def complete_filter_form(driver: WebDriver):
    input_element = Select(WebDriverWait(driver, delay).until(
        EC.presence_of_element_located((By.ID, 'reporting_payroll_date_filter_options'))))

    input_element = select_option(input_element, 'Custom date range')
    input_element.click()

    input_element = driver.find_element_by_id("reporting_payroll_start_date")
    input_element.clear()

    if input_element.text != "":
        input_element.sendKeys(Keys.CONTROL + "a")
        input_element.sendKeys(Keys.DELETE)

    input_element.send_keys(start_date)

    find_id_and_click(driver, "reporting_payroll_exclude_zero_time")
    find_id_and_click(driver, "reporting_payroll_multi_group_link")

    input_element = WebDriverWait(driver, delay).until(
        EC.presence_of_element_located((By.ID, 'tt_assign_groups_reporting_payroll_uncheck_all')))
    input_element.click()

    find_id_and_click(driver, "tt_assign_groups_reporting_payroll_group_select_source_96322")

    input_element = driver.find_element_by_xpath('//button[@class="flat primary action" and @value="Save"]')
    input_element.click()


def find_names_and_tables(driver: WebDriver):
    input_element = WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.XPATH, "//div[starts-with(@id,'reporting_payroll_uid_')]")))

    uid_to_name = {
        "reporting_payroll_ts_table_{0}".format(element.get_attribute("id").split("_")[-1]):
            {"name": driver.find_element_by_xpath(
                "//div[@id='{0}']//div[@class='payroll_reports_employee_name']".format(
                    element.get_attribute("id"))).text,
             "hours": None
             }
        for element in input_element}

    return uid_to_name


def open_all_info(driver: WebDriver, uid_to_name: dict):
    find_id_and_click(driver, "reporting_payroll_expand_all_button")

    WebDriverWait(driver, 120).until(
        EC.presence_of_all_elements_located((By.XPATH,
                                             '//button['
                                             '@id="reporting_payroll_expand_all_button" '
                                             'and '
                                             '@title="Hide details for all employees"]'
                                             )))

    for table_id in uid_to_name.keys():
        WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.ID, table_id)))


def retrieve_table_data(table: Tag):
    rows = table.findAll(lambda tag: tag.name == 'tr')

    data = None

    for row in rows:
        values = row.findAll(lambda tag: tag.name == 'td')

        if len(values) == 10:
            # date, day, in, out, hours, day_total, week_total, job, attachments, notes =
            date, _, _, _, hours, _, _, job, _, _ = map(lambda x: x.text.strip(), values)

            month, day, year = date.split("/", 2)
            date = np.datetime64("{}-{}-{}".format(year, month, day))
            job = job_transform(job)
            hours = float(hours)

            if data is None:
                data = np.array([[date, hours, job]])
            else:
                data = np.append(data, [[date, hours, job]], axis=0)

    return data


def retrieve_all_table_data(page_source: str, uid_to_name: dict):
    soup = BeautifulSoup(page_source, features="html5lib")

    tables = soup.find_all(lambda tag: tag.name == 'table' and tag.has_attr('id') and tag["id"] in uid_to_name)
    print(len(tables))

    for table in tables:
        data = uid_to_name[table["id"]]
        data["hours"] = retrieve_table_data(table)

        print(data['name'])
        print(data["hours"])


def remove_hours_by_date_constraints(uid_to_name: dict, constraints: dict):
    for table in uid_to_name:
        table = uid_to_name[table]
        date_filter = None

        dates = table["hours"][:, 0]

        for event in constraints:
            start = np.datetime64(constraints[event]["start"])
            end = np.datetime64(constraints[event]["end"])

            if date_filter is None:
                date_filter = np.logical_or(dates < start, dates > end)
            else:
                date_filter = np.logical_and(date_filter,
                                             np.logical_or(dates < start, dates > end))

        if date_filter is not None:
            table["hours"] = table["hours"][date_filter]


def aggregating_hours(uid_to_name):
    fieldnames = ['Name', 'Outreach', "Participation"]
    data = pd.DataFrame(columns=fieldnames)
    print(data)

    for i, table in enumerate(uid_to_name):
        info = uid_to_name[table]

        if info['hours'] is None:
            outreach_hours = 0
            participation_hours = 0
        else:
            outreach_hours = np.sum(info['hours'][info['hours'][:, -1] == 0][:, 1])
            participation_hours = np.sum(info['hours'][info['hours'][:, -1] == 1][:, 1])

        data.loc[i] = [info['name'], outreach_hours, participation_hours]

    return data


# def get_sheet(sheet_name):
#     scope = ['https://spreadsheets.google.com/feeds',
#              'https://www.googleapis.com/auth/drive']
#
#     # TODO either remove this method because I am using OAuth or move this comment
#     import gspread
#
#     credentials = ServiceAccountCredentials.from_json_keyfile_name("client_id.json", scope)
#     client = gspread.authorize(credentials)
#
#     return client.open(sheet_name).sheet1


# def get_range(sheet, information: pd.DataFrame):
#     """
#
#     :param sheet:
#     :type sheet: gspread.Worksheet
#     :param information:
#     :return:
#     """
#     data = information.values.tolist()
#     column_header = list(information)
#     data.insert(0, column_header)
#
#     rows = len(data)
#     cols = len(column_header)
#
#     start = "A1"
#     end = "{}{}".format(chr(ord('A') + cols - 1), rows)
#
#     print(start)
#     print(end)
#
#     cell_range = sheet.range("{}:{}".format(start, end))
#
#     i = 0
#     for r in range(rows):
#         for c in range(cols):
#             cell_range[i].value = data[r][c]
#             i += 1
#
#     return cell_range


def get_credentials():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
              'https://www.googleapis.com/auth/drive']

    store = file.Storage('storage.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_id.json', SCOPES)
        creds = run_flow(flow, store)

    return creds


def get_service(credentials):
    return discovery.build('sheets', 'v4', credentials=credentials)


def get_string_range(data_list: list, start='A1'):
    rows = len(data_list)
    cols = len(data_list[0])

    end = "{}{}".format(chr(ord(start[0]) + cols - 1), int(start[1]) + rows - 1)

    return "{}:{}".format(start, end)


def update_value(service: Resource, spreadsheet_id: str, values: list, range_: str = None,
                 value_input_option='USER_ENTERED'):
    value_range_body = {
        "values":
            values
    }

    if range_ is None:
        range_ = get_string_range(values)

    print(range_)

    request = service.spreadsheets().values().update(spreadsheetId=spreadsheet_id, range=range_,
                                                     valueInputOption=value_input_option, body=value_range_body)
    return request.execute()


def to_list(information: pd.DataFrame) -> list:
    data = information.fillna("").values.tolist()
    column_header = list(information)
    data.insert(0, column_header)

    return data


def add_hours_constrains(hours_verification: dict, data: pd.DataFrame):
    if len(hours_verification) > 0:
        data = pd.concat([data, pd.Series(["Date", "Outreach", "Participation"], name="Event")], axis=1)

    for check in hours_verification:
        data = pd.concat([data, pd.Series([hours_verification[check]["date"],
                                           hours_verification[check]["outreach"],
                                           hours_verification[check]["participation"]], name=check)], axis=1)

    return data


def add_dynamic_hours(hours, start_date_column, end_date_column, date_row=2):
    start_cell = constant_cell(2, start_date_column)
    end_cell = constant_cell(2, end_date_column)

    check_date_row, check_date_column = 2, end_date_column + 1
    dynamic_date_cell = constant_cell(check_date_row, check_date_column)

    origin_cell = constant_cell(1, 0)
    end_search_cell = constant_cell(4, end_date_column)
    dates_row = "${}".format(date_row)

    # =INDEX($A$1:$L$4,MATCH("Outreach",H:H),MATCH($N$2,TRANSPOSE($2:$2),0))
    # =INDEX({3}:{4},MATCH({0},H:H),MATCH({2},TRANSPOSE({1}:{1}),0))

    return pd.concat([hours, pd.Series([
        dynamic_date_formula.format("{}:{}".format(start_cell, end_cell)),
        hours_finding_formula.format("Outreach", dates_row, dynamic_date_cell, origin_cell, end_search_cell),
        hours_finding_formula.format("Participation", dates_row, dynamic_date_cell, origin_cell, end_search_cell),
    ], name="Checked Date")], axis=1), check_date_row - 1, check_date_column


def get_closest_hour_index(hours_check: dict):
    now = pd.Timestamp.now()

    dates = []
    for check in hours_check:
        dates.append(hours_check[check]["date"])

    dates = pd.DatetimeIndex(dates)

    return np.argmax((dates - now).total_seconds() >= -24 * 60 * 60)

    # for check in hours_check:


def get_outreach_participation_cell(check_column, outreach_row=3, participation_row=4):
    column_name = chr(ord('A') + check_column + 1)
    outreach_cell = "${}${}".format(column_name, outreach_row)
    participation_cell = "${}${}".format(column_name, participation_row)

    return outreach_cell, participation_cell


def cell(row, column) -> str:
    return chr(ord("A") + column) + str(row)


def constant_cell(row, column) -> str:
    return "${}${}".format(chr(ord("A") + column), row)


def add_hours_check(hours: pd.DataFrame, outreach_cell, participation_cell, outreach_column=1,
                    participation_column=2, column_name="Check") -> (pd.DataFrame, str, str):
    if_statement = '=IF(AND({2}<{0},{3}<{1}),"BOTH",IF({2}<{0},"OUTREACH",IF({3}<{1},"PARTICIPATION","GOOD")))'

    equation = [
        if_statement.format(outreach_cell, participation_cell, cell(i, outreach_column),
                            cell(i, participation_column))
        for i in range(2, len(hours) + 2)
    ]

    hours = pd.concat((hours, pd.Series(equation, name=column_name)), axis=1)
    # hours = hours.assign(Check=pd.Series(equation))
    return hours


def sort_hours(data: pd.DataFrame, sorting_order: list):
    return data.sort_values(by=sorting_order).reset_index(drop=True)


def format_sheet(service, spreadsheet_id, outreach_cell, participation_cell, check_column_index, outreach_column,
                 participation_column, check_date_row, check_date_column, calculated_offset=3):
    reqs = formatting(outreach_cell, participation_cell, check_column_index, outreach_column, participation_column,
                      check_date_row, check_date_column)
    res = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=reqs).execute()

    reqs = formatting(outreach_cell, participation_cell, check_column_index + calculated_offset,
                      outreach_column + calculated_offset, participation_column + calculated_offset,
                      check_date_row, check_date_column, check_column_index + calculated_offset)
    res = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=reqs).execute()


def clean_up_sheet(service, spreadsheet_id):
    reqs = clean_up_formatting(service, spreadsheet_id)

    try:
        res = service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=reqs).execute()
        return True
    except HttpError:
        return False


def add_maxed_hours(hours, outreach_cell, outreach_column=1,
                    participation_column=2):
    outreach_equation = '=MIN({},{})'

    equation = [
        outreach_equation.format(outreach_cell, cell(i, outreach_column))
        for i in range(2, len(hours) + 2)
    ]

    hours = hours.assign(Outreach_Calculated=pd.Series(equation))

    participation_equation = '={1}+IF({2}>{0},{2}-{0},0)'

    equation = [
        participation_equation.format(outreach_cell, cell(i, participation_column), cell(i, outreach_column))
        for i in range(2, len(hours) + 2)
    ]

    hours = hours.assign(Participation_Calculated=pd.Series(equation))

    return hours


def open_spreadsheet(spreadsheet_id):
    url = 'https://docs.google.com/spreadsheets/d/{}'.format(spreadsheet_id)

    # MacOS
    # chrome_path = 'open -a /Applications/Google\ Chrome.app %s'

    # Windows
    chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

    # Linux
    # chrome_path = '/usr/bin/google-chrome %s'

    webbrowser.get(chrome_path).open(url)


if __name__ == '__main__':
    start_total = datetime.now()

    driver = webdriver.Chrome()
    driver.maximize_window()
    driver.get(login_page)
    delay = 3  # seconds

    try:
        complete_login_page(driver)
        open_payroll_filters(driver)
        complete_filter_form(driver)

        find_id_and_click(driver, "reporting_payroll_submit_button")

        uid_to_name = find_names_and_tables(driver)

        print(len(uid_to_name))

        start_time = datetime.now()

        open_all_info(driver, uid_to_name)

        print((datetime.now() - start_time).total_seconds())
        source = driver.page_source

        driver.close()

        retrieve_all_table_data(source, uid_to_name)

        remove_hours_by_date_constraints(uid_to_name, excluded_hours)

        hours = aggregating_hours(uid_to_name)
        hours = sort_hours(hours, ["Outreach", "Participation"])

        print(hours)

        # sheet = get_sheet("Test")
        # cell_range = get_range(sheet, hours)
        # sheet.update_cells(cell_range)

        credentials = get_credentials()
        service = get_service(credentials)

        closest_date = get_closest_hour_index(hours_check)

        print(hours_check)

        # TODO make 6 more dynamic the problem is that len(hours.columns) changes after this
        check_column = 6 + closest_date
        print(check_column)
        print(closest_date)

        outreach_cell, participation_cell = get_outreach_participation_cell(check_column, outreach_row,
                                                                            participation_row)

        hours = add_hours_check(hours, outreach_cell, participation_cell)
        check_column_index = len(hours.columns) - 1

        hours = add_maxed_hours(hours, outreach_cell)
        hours = add_hours_check(hours, outreach_cell, participation_cell, outreach_column=4, participation_column=5,
                                column_name="Check Calculated")

        hours = add_hours_constrains(hours_check, hours)
        hours, check_date_row, check_date_column = add_dynamic_hours(hours, len(hours.columns) - len(hours_check),
                                                                     len(hours.columns) - 1)

        print(hours)
        values = to_list(hours)
        print(values)

        response = update_value(service, spreadsheet_id, values)

        # TODO use the formulas above to make it even more dynamic for dates
        clean_up_sheet(service, spreadsheet_id)
        print(check_date_row, check_date_column)

        format_sheet(service, spreadsheet_id, outreach_cell, participation_cell, check_column_index, 1, 2,
                     check_date_row, check_date_column)
    except TimeoutException:
        print("Loading took too much time!")

    print("Program took: {}s to finish".format((datetime.now() - start_total).total_seconds()))

    open_spreadsheet(spreadsheet_id)

    # driver.quit()
