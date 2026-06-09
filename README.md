# cs166-project
CS166 Final Project

## How to Run
### Install Dependencies
```
pip install Flask
```
If the above doesn't work, try:
```
python3 -m pip install Flask
```

### Create Database
```
source createPostgreDB.sh
```

### Start Database
```
source startPostgreSQL.sh
```

### Load Database
This will create tables, indices, and load data into the database.
```
source loadDB.sh
```

### Running Web Interface (GUI)
```
python3 app.py
```

### Stop Database (when done)
```
source stopPostgreDB.sh
```
