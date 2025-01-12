from . import sleeperapis as api
import sqlite3

# Calls the Sleeper api to get the user ID given the username
def getUserID(username):
    id = None
    try:
        res = api.getUserInfo(username)
        id = res.get('user_id')
    except:
        raise Exception("Failed to get User ID", username)

    return id

# Returns a list of league_ids for the leagues a user is in
def getUsersLeagueIds(user_id):
    league_ids = []
    leagues = api.getUserLeagues(user_id)
    for league in leagues:
        if league.get('league_id') not in league_ids:
            league_ids.append(league.get('league_id'))
    return league_ids

# Returns a list of tuples of (user_id, display_name) for all users in all leagues given a list of league_ids
def getAllUserIds(leagues):
    users = []
    for league_id in leagues:
        league_users = api.getLeagueUsers(league_id)
        for league_user in league_users:
            if league_user.get('user_id') not in users:
                users.append((league_user.get('user_id'), league_user.get('display_name')))
    return users

# Returns a list of completed draft_ids for a list of users completed drafts
def getAllCompletedDraftIds(users):
    drafts = []
    for user_id, _ in users:
        user_drafts = api.getUserDrafts(user_id)
        for user_draft in user_drafts:
            if user_draft.get('status') == 'complete' and user_draft.get('draft_id') not in drafts:
                drafts.append(user_draft.get('draft_id'))
    return drafts

# Returns a dictionary of tuples sorted in order of most frequent league mate
# { user_id : (user_name, number_of_shared_leagues) }
def mostCommonMates(user_id):
    league_mates = {}
    leagues = getUsersLeagueIds(user_id)
    for league in leagues:
        league_users = api.getLeagueUsers(league)
        for league_user in league_users:
            league_user_id = league_user.get('user_id')
            league_user_name = league_user.get('display_name')
            if league_user_id in league_mates:
                _, count = league_mates.get(league_user_id)
                league_mates[league_user_id] = (league_user_name, count + 1)
            else:
                league_mates[league_user_id] = (league_user_name, 1)

    sorted_dict = dict(reversed(sorted(league_mates.items(), key=lambda item: item[1][1])))

    return sorted_dict

# Prints the last person drafted IF a draft is happening
def getLastDrafted(user_id):
    drafts = api.getUserDrafts(user_id)
    for draft in drafts:
        if draft.get('status') == 'drafting':
            league_metadata = draft.get('metadata')
            league_name = league_metadata.get('name')
            picks = api.getDraftPicks(draft.get('draft_id'))
            last_pick = picks[-1]
            last_drafter = last_pick.get('picked_by')
            pick_num = last_pick.get('pick_no')
            player_metadata = last_pick.get('metadata')
            drafter_info = api.getUserInfo(last_drafter)
            username = drafter_info.get('username')
            player_first_name = player_metadata.get('first_name')
            player_last_name = player_metadata.get('last_name')
            player_pos = player_metadata.get('position')
            print(f"{username} drafted {player_pos} {player_first_name} {player_last_name} with pick number {pick_num} in {league_name}")
    return

# Returns a dictionary of one's most rostered players. Also returns the number of leagues one is in
# Only returns a player if the player is owned in more than one league
# Dictionary sorted by most rostered to least rostered
# { player_full_name : count }
def getMostRosteredPlayers(user_id, player_db="sleeperSpider.sqlite"):
    favorite_players = {}
    leagues = getUsersLeagueIds(user_id)
    league_count = len(leagues)
    # lol. Three nested for loops. This can definitely be improved.
    for league in leagues:
        rosters = api.getLeagueRosters(league)
        if rosters:
            for roster in rosters:
                if user_id != roster.get('owner_id'):
                    continue
                players = roster.get('players')
                if players:
                    for player in players:
                        count = favorite_players.get(player, 0)
                        favorite_players[player] = count + 1

    # A sorted dictionary of one's most rostered players
    # { player_id : count }
    sorted_dict = dict(reversed(sorted(favorite_players.items(), key=lambda item: item[1])))

    # Own function?
    favorites = {}
    con = sqlite3.connect(player_db)
    cur = con.cursor()
    # Replace the player_id with the player_name
    for player in sorted_dict:
        # Only keeps players that a player has in more than one league
        if sorted_dict[player] <= 1:
            continue
        res = cur.execute(f"SELECT full_name FROM players WHERE player_id='{player}'")
        player_name_tup = cur.fetchone()
        # The defenses don't have a full_name associated with them. This is for that edge case
        if not player_name_tup[0]:
            player_name = str(player) + " DEF"
        else:
            player_name = str(player_name_tup[0])
        # Don't need to use .get() since this is guaranteed to have a value
        count = sorted_dict[player]
        favorites[player_name] = count

    return favorites, league_count

# Returns a dictionary of a tuple of league count and the most rostered players for all players one shares a league with
# { user_name : (league_count, most_rostered_players) }
def getLeagueMatesFavorites(user_id, player_db="sleeperSpider.sqlite"):
    all_favorite_players = {}
    league_mates = mostCommonMates(user_id)
    for mate in league_mates:
        username, _ = league_mates[mate]
        favorite_players, league_count = getMostRosteredPlayers(mate, player_db)
        all_favorite_players[username] = (league_count, favorite_players)

    return all_favorite_players

# Stores all of a the most rostered players in an output file
def storeFavorites(id, output_filename, player_db="sleeperSpider.sqlite"):
    favs = getLeagueMatesFavorites(id, player_db)
    with open(output_filename, "w") as out:
        for username, favorites in favs.items():
            out.write(username + f"'s favorites in {favorites[0]} leagues\n")
            out.write(str(favorites[1]) + "\n")
        out.close()
