import sqlite3


class TSheetsCache:
    users_table = 'users'
    jobcodes_table = 'jobcodes'
    timesheets_table = 'timesheets'
    time_stamp_table = 'info_timestamp'

    update_rates = {
        users_table: 365,
        jobcodes_table: 365,
        timesheets_table: 1.0 / 24,
    }

    def __init__(self, database_file="tsheets_info.db", update_rates: dict = None) -> None:
        super().__init__()
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()

        if update_rates is not None:
            self.update_rates = update_rates

        self.create_timestamp_table()
        self.create_username_table()
        self.create_jobcodes_table()
        self.create_timesheets_table()

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

    def add_time_stamp(self, tables):
        if isinstance(tables, str):
            tables = ((tables,),)

        self.cursor.executemany("INSERT INTO info_timestamp VALUES (?, CURRENT_TIMESTAMP)", tables)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def delete_information(self, table):
        self.cursor.execute("DELETE FROM {}".format(table))
        self.conn.commit()

    def insert_users(self, users, purge_table=True):
        if purge_table:
            self.delete_information(self.users_table)

        self.cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", users)
        self.conn.commit()

    def insert_timesheets(self, timesheets, purge_table=True):
        if purge_table:
            self.delete_information(self.timesheets_table)

        self.cursor.executemany("INSERT INTO timesheets VALUES (?, ?, ?, ?, ?)", timesheets)
        self.conn.commit()

    def insert_jobcodes(self, jobcodes, purge_table=True):
        if purge_table:
            self.delete_information(self.jobcodes_table)

        self.cursor.executemany("INSERT INTO users VALUES (?, ?, ? )", jobcodes)
        self.conn.commit()

    def needs_update(self, table_name: str):
        # if isinstance(table_names, str):
        #     table_names = (table_names,)

        time = self.update_rates[table_name]

        a = self.cursor.execute(
            '''SELECT time_stamp
                from info_timestamp
                where (
                          table_name = ?
                          AND (JULIANDAY('now') - JULIANDAY(time_stamp)) <= ?
                        )
                ORDER BY time_stamp DESC LIMIT 1''',
            [table_name, time])

        a = a.fetchone()
        print(a)

        return a is None


if __name__ == '__main__':
    with TSheetsCache() as database:
        # database.insert_timesheets([[1, 3, "2018-01-06", 4, 5]])

        # database.add_time_stamp("users")
        # database.add_time_stamp("users")
        # database.needs_update("users")

        print(database.needs_update("users"))
    # c.create_username_table()
    # c.create_username_table()
