import json
import sqlite3

"""
A collection of utilities to make storing data from the Sleeper API calls easier

When calling the players, Sleeper's api call returns a pretty large file to download (like 12 MB).
They request that that API endpoint is only called once per day. I call that endpoint manually and store it in a file.

Example commands in a terminal:
cd ~/path/to/working/directory
curl "https://api.sleeper.app/v1/players/nfl" -o players.json

This saves that data in a file that I can use throughout these function.
"""

# Flattens a dictionary. This will fail if a list is present in the dictionary
def flatten(humpy_dict, acc):

    for k, v in humpy_dict.items():
        if type(v) is dict:
            flatten(v, acc)
        else:
            if type(v) is list:
                raise Exception("NEED TO IMPLEMENT LIST IN FLATTEN FUNCTION WITH DBUTILS")
            # Makes the value a string if it exists. If the value is 'None' it just adds it
            acc[k] = str(v).replace("'", "") if v else v

    return acc

# Cleans the player dictionary that comes from the api call.
# Lists are removed prior to flattening and stored in their own table
def cleanPlayer(player_dict):
    competitions = player_dict.pop('competitions', None)
    # Competitions is empty for every player currently. This is here in case that gets filled at some point
    if competitions:
        raise Exception("'Competition' List filled in cleanPlayer function", competitions, player_dict)
    # Most players only have one position. This is stored in a seperate table
    fantasy_positions = player_dict.pop('fantasy_positions', None)
    flat_player = flatten(player_dict, {})
    # Metadata should have been flattened if it was populated in the api return.
    # When it isn't used, the 'metadata' dict never gets flattened. This is hear to remove the col from the table
    # If metadata is not empty, but wasn't flattened this check will catch that edge case
    failed = flat_player.pop('metadata', None)
    if failed:
        raise Exception("Failed to clean player dictionary in cleanPlayer function", failed, player_dict, flat_player)

    return flat_player, competitions, fantasy_positions

# Drops the players table
def dropPlayersTable(db):

    query = f"DROP TABLE IF EXISTS players;"
    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute(query)
            con.commit()
    except sqlite3.Error as e:
        print(e)

    return

# Drops the fantasy positions table
def dropFantasyPositionsTable(db):

    query = f"DROP TABLE IF EXISTS fantasy_positions;"
    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute(query)
            con.commit()
    except sqlite3.Error as e:
        print(e)

    return

# Drops both tables
def dropPlayerTables(db):

    dropPlayersTable(db)
    dropFantasyPositionsTable(db)

    return

# Gets all the columns present from every player.
# This is mainly used to get the column names for initially building the players table
def getAllColumns(players):
    cols = []
    for player_id, player_data in players.items():
        clean_player, competitions, fantasy_positions = cleanPlayer(player_data)
        for col in clean_player.keys():
            if col in cols or not col:
                continue
            else:
                cols.append(col)

    return cols

# Builds the column query used when initially building the playerstable
def buildColQuery(cols):
    # "key_id" : primary key
    # "player_id" : text NOT NULL
    # all other text that can be NULL
    col_query = "key_id INTEGER PRIMARY KEY, player_id TEXT NOT NULL"
    for col in cols:
        if col == "player_id":
            continue
        else:
            col_query = col_query + ", " + col + " TEXT"

    return col_query

# Creates the player table
def createPlayerTable(col_query, db):

    query = f"CREATE TABLE IF NOT EXISTS players ({col_query});"
    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute(query)
            con.commit()
    except sqlite3.Error as e:
        print(e)

    return

# Creates the fantasy_positions table
def createFantasyPositionsTable(db):
    query = """
            CREATE TABLE IF NOT EXISTS fantasy_positions (
                id INTEGER PRIMARY KEY,
                player_key INTEGER NOT NULL,
                position TEXT NOT NULL,
                FOREIGN KEY (player_key) REFERENCES players (key_id)
                ); """
    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
            cur.execute(query)
            con.commit()
    except sqlite3.Error as e:
        print(e)

    return

# Creates both tables
def buildPlayerTables(input, database):

    with open(input) as player_data:
        players = json.load(player_data)
        player_data.close()

    cols = getAllColumns(players)
    col_query = buildColQuery(cols)
    dropPlayerTables(database)
    createPlayerTable(col_query, database)
    createFantasyPositionsTable(database)

    return

# Inserts data into both players and fantasy_positions tables
def insertPlayersData(input, database):

    with open(input) as player_data:
        players = json.load(player_data)
        player_data.close()

    con = sqlite3.connect(database)
    cur = con.cursor()
    key_id = 1
    pos_id = 1
    for player_id, player_data in players.items():
        player_id = str(player_id)
        clean_player, competitions, fantasy_positions = cleanPlayer(player_data)
        cur.execute(f"INSERT INTO players ('key_id', 'player_id') VALUES ({key_id}, '{player_id}');")
        for col, val in clean_player.items():
            if col == 'player_id':
                continue
            elif not val:
                q = f"UPDATE players SET {col} = NULL WHERE key_id = {key_id};"
                cur.execute(q)
            else:
                val =  str(val)
                q = f"UPDATE players SET {col} = '{val}' WHERE key_id = {key_id};"
                cur.execute(q)
        if fantasy_positions:
            for position in fantasy_positions:
                cur.execute(f"INSERT INTO fantasy_positions ('id', 'position', 'player_key') VALUES ({pos_id}, '{position}', {key_id});")
                pos_id += 1
        key_id += 1

    con.commit()

    return

def buildDB(input="players.json", database="sleeperSpider.sqlite"):

    buildPlayerTables(input, database)
    insertPlayersData(input, database)

    return

# Utility Functions To Help Build Timeline

import sqlite3
from sqlite3 import OperationalError

def createConnection(db_file, thread_check=True):
    con = sqlite3.connect(db_file, check_same_thread=thread_check)
    cur = con.cursor()

    return con, cur

def commitClose(con, cur):
    con.commit()
    cur.close()
    con.close()

    return

# THIS SCRIPT WILL FAIL IF THERE IS A ';' IN A TEXT BLOCK
def executeScriptsFromFile(db_file, filename):

    f = open(filename, 'r')
    sql_file = f.read()
    f.close()

    sql_commands = sql_file.split(';')

    con, cur = createConnection(db_file)
    for command in sql_commands:
        try:
            cur.execute(command)
        except (OperationalError, msg):
            print("Command Skipped: ", msg)
    commitClose(con, cur)

    return

def insertData(db_file, table_name, cols, data):
    query = f"INSERT INTO {table_name} {cols} VALUES(?)"
    con, cur = createConnection(db_file)
    cur.execute(query, data)
    commitClose(con, cur)

    return

def insertDataMany(db_file, table_name, cols, data):
    count = len(cols)
    q_marks = "?"
    while count > 1:
        q_marks = q_marks + ", ?"
        count -= 1
    query = f"INSERT INTO {table_name} {cols} VALUES({q_marks})"
    con, cur = createConnection(db_file)
    cur.executemany(query, data)
    commitClose(con, cur)

    return
