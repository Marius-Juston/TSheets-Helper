import sqlite3


class TSheetsCache:
    def __init__(self, database_file="tsheets_info.db") -> None:
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
        if self.table_exists('users'):
            self.cursor.execute("CREATE TABLE users (id INTEGER, name text, email text)")
            self.conn.commit()

    def create_timesheets_table(self):
        if self.table_exists('timesheets'):
            self.cursor.execute("CREATE TABLE timesheets (id INTEGER, date DATE, duration INTEGER, jobcode_id INTEGER)")
            self.conn.commit()

    def create_jobcodes_table(self):
        if self.table_exists('jobcodes'):
            self.cursor.execute("CREATE TABLE jobcodes (id INTEGER, parent_id INTEGER,name TEXT)")
            self.conn.commit()

    def close(self):
        self.conn.close()


if __name__ == '__main__':
    c = TSheetsCache()
    # c.create_username_table()
    print(c.table_exists('users'))
    # c.create_username_table()
