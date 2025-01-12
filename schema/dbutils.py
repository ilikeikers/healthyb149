import sqlite3

#A collection of utilities to make working with the database easier


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

# Cleans the user input that comes from the forms.
# Lists are removed prior to flattening and stored in their own table
def cleanInput(player_dict):
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


# Drops tables
def dropTable(db, *tables):

    if len(tables) == 0:
        print("Command ran without table name. Run 'fullReset' to fully reset db tables.")

    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
    except sqlite3.Error as e:
        print(e)

    for table in tables:
        query = f"DROP TABLE IF EXISTS {table}; "
        cur.execute(query)

    con.commit()

    return

# Creates tables
def createTable(db, *tables):

    if len(tables) == 0:
        print("Command ran without table name. Run 'fullReset' to fully reset db tables.")

    try:
        with sqlite3.connect(db) as con:
            cur = con.cursor()
    except sqlite3.Error as e:
        print("SQLITE ERROR: " + e)

    for table in tables:
        match table:
            case "users":
                query = """
                        CREATE TABLE IF NOT EXISTS users(
                            userid INTEGER PRIMARY KEY,
                            pin INTEGER NOT NULL,
                            challenge INTEGER NOT NULL,
                            first_name TEXT NOT NULL,
                            last_name TEXT NOT NULL,
                            username TEXT NOT NULL,
                            private INTEGER NOT NULL,
                            height INTEGER
                            ); """
                cur.execute(query)
            case "leaderboard":
                query = """
                        CREATE TABLE IF NOT EXISTS leaderboard(
                            id INTEGER PRIMARY KEY,
                            user INTEGER NOT NULL,
                            starting_weight INTEGER NOT NULL,
                            current_weight INTEGER NOT NULL,
                            starting_musclemass INTEGER NOT NULL,
                            current_musclemass INTEGER NOT NULL,
                            current_percent_loss INTEGER NOT NULL,
                            current_percent_gain INTEGER NOT NULL,
                            current_position INTEGER NOT NULL,
                            previous_position INTEGER,
                            FOREIGN KEY (user) REFERENCES users (userid)
                            ); """
                cur.execute(query)
            case "stats":
                # datetime stored as YYYY-MM-DD HH:MM
                query = """
                        CREATE TABLE IF NOT EXISTS stats(
                            id INTEGER PRIMARY KEY,
                            user INTEGER NOT NULL,
                            datetime TEXT NOT NULL,
                            weight INTEGER NOT NULL,
                            checked_by TEXT NOT NULL,
                            position_snapshot INTEGER,
                            percent_loss INTEGER,
                            percent_gain INTEGER,
                            scaleid TEXT,
                            FOREIGN KEY (user) REFERENCES users (userid)
                            ); """
                cur.execute(query)

        con.commit()

    return

def fullReset(db):
    dropTable(db, "users", "stats", "leaderboard")
    createTable(db, "users", "stats", "leaderboard")

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
