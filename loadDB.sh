#! /bin/bash
cs166_psql cs166_db < schema.sql

cp -a ./data/*.csv $PGDATA/
cs166_psql cs166_db < insert.sql

cs166_psql cs166_db < index.sql