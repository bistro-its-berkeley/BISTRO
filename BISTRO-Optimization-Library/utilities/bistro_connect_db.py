import configparser

import mysql.connector
from mysql.connector import Error, errorcode

from utilities.bistro_dbschema import TABLES_LIST, COLUMNS, INSERT


def parse_credential(db_profile):
    config = configparser.ConfigParser()
    config.read(db_profile)
    db_login = config['DB_LOGIN']
    bistro_db=BistroDB(db_name=db_login['DATABASE_NAME'],user_name=db_login['DATABASE_USER_NAME'],
    db_key=db_login['DATABASE_KEY'],host=db_login['DATABASE_HOST'])
    return bistro_db


class BistroDB(object):

    db_name = None
    user_name = None
    db_key = None

    connection = None
    cursor = None

    def __init__(self, db_name, user_name, db_key, host='localhost'):

        self.db_name = db_name
        self.user_name = user_name
        self.db_key = db_key
        self.host = host

        self.connection = self.connect_to_db(self.host, self.user_name, self.db_key)
        self.cursor = self.get_cursor()

    def __del__(self):
        if self.connection and (self.connection.is_connected()):
            self.connection.close()
            print("Connection to DB {} closed".format(self.db_name))

    @staticmethod
    def connect_to_db(host, user_name, db_key):
        """
        Takes in the Database name, user name and password return connection to the database.
        If input invalid or connection has problem, return None

        """

        if not user_name or not db_key:
            print("You have not set user_name or db_key for BistroDB")
            return None

        try:
            connection = mysql.connector.connect(
                host=host, user=user_name, password=db_key
            )

            if connection.is_connected():
                print("Connected to DB at {}".format(host))
                return connection
            else:
                print("Not able to connect DB")
                return None

        except Error as e:
            print("[DB ERROR] while connection to DB", e)
            return None

    def create_db(self, cursor, db_name):
        """
        Create a database with the provided cursor and return the cursor in that database
        """

        try:
            cursor.execute("CREATE DATABASE {}".format(db_name))
            print("Created database {}".format(db_name))
            cursor.execute("USE {}".format(db_name))
            return cursor
        except Error as e:
            print("Failed to create database {}".format(db_name))
            raise e

    def get_cursor(self):
        """
        return the cursor from connection that's using the db_name database
        """
        if not self.db_name:
            print("You have not set db_name for BistroDB")
            return 

        cursor = self.connection.cursor()

        try:
            cursor.execute("USE {}".format(self.db_name))
            return cursor
        except Error as e:
            if e.errno == errorcode.ER_BAD_DB_ERROR:
                # the database has not been created yet
                return self.create_db(cursor, self.db_name)
            else:
                raise e

    def create_table(self, table_name, schema):
        """
        take a defined schema and create the table in the database
        if the table name already exist in the database, this will not do anything.
        """
        try:
            self.cursor.execute("CREATE TABLE `{}` ({})".format(table_name, schema))
            print("Created DB table {}".format(table_name))
        except Error as e:
            if e.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("Table {} already exists.".format(table_name))
            else:
                raise e

    def drop_table(self, table_name):
        sql = "DROP TABLE IF EXISTS {}".format(table_name)
        self.cursor.execute(sql)
        print("Dropped table {}".format(table_name))

    def drop_all_tables(self):
        for table in TABLES_LIST[::-1]:
            # drop the table in reverse order to avoid foreign key conflict
            self.drop_table(table)

    def query(self, q):
        """sent customized query to database"""
        self.cursor.execute(q)
        return self.cursor.fetchall()

    def insert(self, table_name, data, commit=False, skip_existing=False):
        """
        will follow the columns and required data for specific table and insert
        data to the table.
        """
        # when skip_existing is true, the database will skip the row that
        # already exist in the database instead of creating a new row.
        skip = 'IGNORE' if skip_existing else ''
        sql = "INSERT {} INTO {} ({}) VALUES ({})".format(
            skip, table_name, COLUMNS[table_name], INSERT[table_name])
        length = len(data)
        if length < 50000:
            self.cursor.executemany(sql, data)
        else:
            for i in range((length // 50000)+1):
                lo = 50000 * i
                hi = 50000 * (i+1)
                if table_name == 'pathtraversal_link':
                    print('pathtraversal_link...')
                self.cursor.executemany(sql, data[lo: min(length, hi)])                
                print(f'inserting {i} of {(length // 50000)}')

        print("Inserted {} row(s) to {} table".format(len(data), table_name))
        if commit:
            self.connection.commit()

    def fixed_data_in_db(self, scenario_name):
        """
        Check for `scenario` whether the fixed-data already exists in the
        database
        """
        scenarios = self.query(
            """
            SELECT fixed_data_stored FROM scenario
            WHERE scenario='{}'
            """.format(scenario_name))

        if not scenarios:
            self.insert('scenario', [[scenario_name, False]], commit=True)
            return False
        else:
            return scenarios[0][0]

    def fixed_data_finish_parsing(self, scenario_name):
        self.cursor.execute(
            """
            UPDATE scenario SET fixed_data_stored=true
            WHERE scenario='{}'
            """.format(scenario_name))
        self.connection.commit()

