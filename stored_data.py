import sqlite3


class TSheetsCache:
    users_table = 'users'
    jobcodes_table = 'jobcodes'
    timesheets_table = 'timesheets'
    time_stamp_table = 'info_timestamp'


    def __init__(self, database_file="tsheets_info.db", update_rates: dict = None) -> None:
        super().__init__()
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()

    def table_exists(self, table):
        try:
            self.cursor.execute('''SELECT 1 FROM {} LIMIT 1;'''.format(table))
            return True
        except sqlite3.OperationalError:
            return False

    def create_username_table(self):
        if not self.table_exists(self.users_table):
            self.cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name text, email text) ")
            self.conn.commit()

    def create_timesheets_table(self):
        if not self.table_exists(self.timesheets_table):
            self.cursor.execute(
                "CREATE TABLE timesheets (id INTEGER PRIMARY KEY, date DATE, duration INTEGER, jobcode_id INTEGER)")
            self.conn.commit()

    def create_jobcodes_table(self):
        if not self.table_exists(self.jobcodes_table):
            self.cursor.execute("CREATE TABLE jobcodes (id INTEGER PRIMARY KEY, parent_id INTEGER,name TEXT)")
            self.conn.commit()

    def create_timestamp_table(self):
        if not self.table_exists(self.time_stamp_table):
            self.cursor.execute("CREATE TABLE info_timestamp (table_name text, time_stamp TIMESTAMP)")
            self.conn.commit()
    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

if __name__ == '__main__':
    with TSheetsCache() as database:
        # database.add_time_stamp("users")
        # database.add_time_stamp("users")
        database.needs_update("users")

        print(database.needs_update("users"))
    # c.create_username_table()
    # c.create_username_table()
