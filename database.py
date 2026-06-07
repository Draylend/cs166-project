# Using PostgreSQL to store database

import psycopg2
import psycopg2.extras

def get_db():
    return psycopg2.connect(
        database="cs166_db",
        user="dchow001",
        password="",
        host="localhost",
        port="36260"
    )
