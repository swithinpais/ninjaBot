from os import read
import sqlite3
def create_connection(db_file):

    conn = None
    try:
        conn = sqlite3.connect(db_file)
        print(f"Established connection with {db_file}")
        print(f"Running sqlite3 version {sqlite3.version}")
    except Exception as e:
        raise e

    return conn

def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Exception as e:
        print(e)

def add_data(conn, table, **kwargs):

    sql = f"INSERT INTO {table}("#base sql command
    for argName in kwargs:
        sql = sql + argName + ","#adds each argument name they want to add to the table
    sql = sql[0:-1]#removes the final ,
    sql = sql + ") VALUES("#adds the values
    for _ in kwargs:
        sql = sql + "?,"#adds a ?, for each argument passed
    sql = sql[0:-1]#removes the final ,
    sql = sql + ")"#closes the value args

    args = [kwargs[arg] for arg in kwargs]

    c = conn.cursor()
    c.execute(sql, args)
    conn.commit()
    return

def read_data(conn, read, table, check=None, value=None):
    if not(isinstance(read, str)):
        raise ValueError("read must be string")
    if not(isinstance(table, str)):
        raise ValueError("table must be string")
    if check is None and value is None:
        sql = f"SELECT {read} FROM {table}"
        c = conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        return rows
    elif check is not None and value is not None:
        sql = f"SELECT {read} FROM {table} WHERE {check}={value}"
        c = conn.cursor()
        c.execute(sql)
        rows = c.fetchall()
        return rows
    else:
        raise ValueError("check and value must both be None or both not None")

def update_data(conn, table, check, value, **kwargs):
    sql = f"""UPDATE {table}
    SET """
    for kwarg in kwargs:
        sql += f"{kwarg} = {kwargs[kwarg]}, "
    sql = sql[0:-1]
    sql += f"\nWHERE {check}={value};"

def delete_data(conn, table, check, value):
    sql = f"DELETE FROM {table} WHERE {check}={value}"
    c = conn.cursor()
    c.execute(sql)
    conn.commit()


def main():
    conn = create_connection("tradeBanned.db")
    create_table(conn, sql)

sql = """CREATE TABLE IF NOT EXISTS tradeBanned(
    id integer PRIMARY KEY,
    user_id integer NOT NULL
);
"""

if __name__ == "__main__":
    main()


