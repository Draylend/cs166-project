# Using PostgreSQL to store database

import psycopg2
import psycopg2.extras

import os, getpass

def get_db():
    return psycopg2.connect(
        database="cs166_db",
        user=getpass.getuser(),
        password="",
        host="localhost",
        port=os.getenv("PGPORT", "5432")
    )
