import sqlite3

import pandas as pd


class TSheetsCache:
    users_table = 'users'
    jobcodes_table = 'jobcodes'
    timesheets_table = 'timesheets'
    time_stamp_table = 'info_timestamp'

    __update_rates = {
        users_table: 100,
        jobcodes_table: 100,
        timesheets_table: 12.0 / 24,
    }

    def __init__(self, database_file="tsheets_info.db", update_rates: dict = None, excluded_date_ranges=None) -> None:
        super().__init__()
        self.excluded_date_ranges = self.format_excluded_date_ranges(excluded_date_ranges)

        print(self.excluded_date_ranges)
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()

        if update_rates is not None:
            self.__update_rates = update_rates

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
            self.cursor.execute("CREATE TABLE users (user_id INTEGER NOT NULL PRIMARY KEY, name text, email text) ")
            self.conn.commit()

    def create_timesheets_table(self):
        if not self.table_exists(self.timesheets_table):
            self.cursor.execute(
                '''CREATE TABLE timesheets 
                    (
                        timesheet_id INTEGER NOT NULL PRIMARY KEY, 
                        user_id INTEGER not null,
                        date DATE, 
                        duration INTEGER, 
                        jobcode_id INTEGER,
                        FOREIGN KEY (user_id)
                            REFERENCES users(user_id) ,
                        FOREIGN KEY (jobcode_id) 
                            REFERENCES jobcodes(jobcode_id) 
                    )'''
            )
            self.conn.commit()

    def create_jobcodes_table(self):
        if not self.table_exists(self.jobcodes_table):
            self.cursor.execute('''CREATE TABLE jobcodes 
                                    (
                                    jobcode_id INTEGER NOT NULL PRIMARY KEY, 
                                    parent_id INTEGER NOT NULL ,
                                    name TEXT,
                                    FOREIGN KEY (parent_id) 
                                        REFERENCES jobcodes(jobcode_id) 
                                    )''')
            self.conn.commit()

    def create_timestamp_table(self):
        if not self.table_exists(self.time_stamp_table):
            self.cursor.execute("CREATE TABLE info_timestamp (table_name text, time_stamp TIMESTAMP,successful BOOL )")
            self.conn.commit()

    def names_to_id(self, names):
        data = {}

        for name in names:
            data[name[0]] = {'user_id': self.name_to_id(name)}

        return data

    def name_to_id(self, name):
        result = self.cursor.execute("SELECT users.user_id from users where name==? LIMIT 1", name)
        result = result.fetchone()[0]

        return result

    def add_time_stamp(self, tables, successful):
        # if isinstance(tables, str):
        #     tables = ((tables,),)

        self.cursor.executemany("INSERT INTO info_timestamp VALUES (?, CURRENT_TIMESTAMP, ?)", [[tables, successful]])
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
        try:
            if purge_table:
                self.delete_information(self.users_table)

            self.cursor.executemany("INSERT INTO users VALUES (?, ?, ?)", users)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            return False

    def insert_timesheets(self, timesheets, purge_table=True):
        try:
            if purge_table:
                self.delete_information(self.timesheets_table)

            self.cursor.executemany("INSERT INTO timesheets VALUES (?, ?, ?, ?, ?)", timesheets)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            return False

    def insert_jobcodes(self, jobcodes, purge_table=True):
        try:
            if purge_table:
                self.delete_information(self.jobcodes_table)

            self.cursor.executemany("INSERT INTO jobcodes VALUES (?, ?, ? )", jobcodes)
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(e)
            return False

    def needs_update(self, table_name: str):
        # if isinstance(table_names, str):
        #     table_names = (table_names,)

        time = self.__update_rates[table_name]

        a = self.cursor.execute(
            '''SELECT time_stamp
                from info_timestamp
                where (
                          successful
                          AND table_name = ?
                          AND (JULIANDAY('now') - JULIANDAY(time_stamp)) <= ?
                        )
                ORDER BY time_stamp DESC LIMIT 1''',
            [table_name, time])

        a = a.fetchone()

        return a is None

    def fetch_participation_hours(self):
        hours = self.cursor.execute(
            '''
            SELECT users.name                                         as student_name
                   , SUM(T.duration / 3600.0)                         as hours
            FROM users
                JOIN timesheets T
                    ON T.user_id = users.user_id
                JOIN jobcodes j 
                    ON T.jobcode_id = j.jobcode_id
                INNER JOIN jobcodes j2 
                    ON j.parent_id = j2.jobcode_id
            WHERE j2.name == 'Participation' OR j2.name == 'Training'{}
            GROUP BY student_name;
            '''.format(self.excluded_date_ranges))

        return hours.fetchall()

    def fetch_outreach_hours(self):
        hours = self.cursor.execute(
            '''
                SELECT users.name                       as student_name
                       , SUM(T.duration / 3600.0)       as hours
                FROM users
                    JOIN timesheets T
                        ON T.user_id = users.user_id
                    JOIN jobcodes j 
                        ON T.jobcode_id = j.jobcode_id
                    INNER JOIN jobcodes j2 
                        ON j.parent_id = j2.jobcode_id
                WHERE j2.name == 'O&S'{}
                GROUP BY student_name;
                '''.format(self.excluded_date_ranges))
        return hours.fetchall()

    def fetch_outreach_participation_hours(self):
        particiaption = pd.DataFrame(self.fetch_participation_hours(), columns=["Name", "Participation"])
        outreach = pd.DataFrame(self.fetch_outreach_hours(), columns=["Name", "Outreach"])

        merged = pd.merge(outreach, particiaption, on="Name")
        return merged

    def format_excluded_date_ranges(self, excluded_date_ranges):
        if excluded_date_ranges is None:
            return ''

        date_condition = []

        for event in excluded_date_ranges:
            start_date = excluded_date_ranges[event]['start']
            end_date = excluded_date_ranges[event]['end']
            date_condition.extend([start_date, end_date])

        return (" AND T.date NOT BETWEEN '{}' AND '{}'" * int(len(date_condition) / 2)).format(*date_condition)


if __name__ == '__main__':
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

    with TSheetsCache(excluded_date_ranges=excluded_hours) as database:
        print(database.fetch_outreach_participation_hours())

        # print(a)
        # a = database.insert_timesheets([[1, 1, "2018-06-01", 4, 5]])
        # print(a)
        # database.add_time_stamp(database.timesheets_table, a)

        # database.add_time_stamp("users")
        # database.add_time_stamp("users")
        # database.needs_update("users")

        # print(database.needs_update(database.timesheets_table))
        # c.create_username_table()
        # c.create_username_table()
