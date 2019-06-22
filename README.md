# TSheets-Helper
## Setup
1. If you are a new user or if you want to change google accounts for sending the information delete the storage.json file in the ./assets folder. 
   1. When you run the program it will ask to authenticate your google account
2. Go into the info.json file, this is where the information such as the spreadsheet id, the hours required and the excluded hours from the report are located.
   1. Be sure that the correct year is selected
   2. The date format expected is YYYY-MM-DD (SQL format)
   3. To find the spreadsheet id of any google sheet:
      1. Example: https://docs.google.com/spreadsheets/u/0/d/1ImtDrstD8OzobtIknXnsyYDxBsbggJhZRrS9oIiYJpI/edit 
      2. The spreadsheet id of this google sheet is the text between https://docs.google.com/spreadsheets/u/0/d/ and /edit (1ImtDrstD8OzobtIknXnsyYDxBsbggJhZRrS9oIiYJpI)
## Run
1. To run the program open up a command line interface and then run the executable with the necessary arguments
    1. The API token
    2. If you want to send notifications or not
    3. If you want to send the info to another spreadsheet
2. Example:
    1. `.\new_driver.exe -t TOKEN -n 0 -s SHEET_ID`
    


