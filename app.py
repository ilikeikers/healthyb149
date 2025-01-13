from flask import Flask, redirect, render_template, request
from time import localtime, strftime
from libs import helpers as do
from libs import dbutils as dbu
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

DB_FILE = "healthyb149.sqlite"
con, db = dbu.createConnection(DB_FILE, False)

@app.route("/")
def index():
    # [(pos, fname, lname, percent var, pos change), ()]

    raw_biggest_losers = db.execute("SELECT userid, first_name, last_name FROM users WHERE challenge == 0").fetchall()
    raw_muscle_madness = db.execute("SELECT userid, first_name, last_name FROM users WHERE challenge == 1").fetchall()
    raw_bl_leaderboard = db.execute("SELECT user, current_percent_loss, current_position, previous_position FROM leaderboard ORDER BY current_percent_loss DESC").fetchall()
    raw_mm_leaderboard = db.execute("SELECT user, current_percent_gain, current_position, previous_position FROM leaderboard ORDER BY current_percent_gain DESC").fetchall()
    bl_users = []
    for loser in raw_biggest_losers:
        for leaderboard_position in raw_bl_leaderboard:
            if loser[0] != leaderboard_position[0]:
                continue
            elif loser[0] == leaderboard_position[0]:
                userid = loser[0]
                fname = loser[1].title()
                lname = loser[2].title()
                percent_loss = round(leaderboard_position[1], 2)
                # fname, lname, percent_loss, current_position, previous_position
                bl_user = (fname, lname, percent_loss, leaderboard_position[2], leaderboard_position[3], userid)
                bl_users.append(bl_user)
            else:
                return "CONTACT IKE and let him know it failed to update the biggest loser leaderboard positions"
    mm_users = []
    for maniac in raw_muscle_madness:
        for leaderboard_position in raw_mm_leaderboard:
            if maniac[0] != leaderboard_position[0]:
                continue
            elif maniac[0] == leaderboard_position[0]:
                userid = maniac[0]
                fname = maniac[1].title()
                lname = maniac[2].title()
                percent_gain = round(leaderboard_position[1], 2)
                # fname, lname, percent_loss, current_position, previous_position
                mm_user = (fname, lname, percent_gain, leaderboard_position[2], leaderboard_position[3], userid)
                mm_users.append(mm_user)
            else:
                return "CONTACT IKE and let him know it failed to update the muscle madness leaderboard positions"
    sorted_bl_users = sorted(bl_users, key=lambda x:x[2], reverse=True)
    sorted_mm_users = sorted(mm_users, key=lambda x:x[2], reverse=True)
    bl_counted_users = []
    mm_counted_users = []
    count = 1
    for user in sorted_bl_users:
        userid = user[5]
        raw_previous_position = db.execute(f"SELECT current_position FROM leaderboard WHERE user='{userid}';").fetchone()
        previous_position = int(raw_previous_position[0])
        current_position = count
        position_change = previous_position - current_position
        db.execute(f"UPDATE leaderboard SET current_position={current_position} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET previous_position={previous_position} WHERE user={userid}")
        user_tup = (count, user[0], user[1], user[2], user[3], user[4], position_change)
        bl_counted_users.append(user_tup)
        count += 1
    count = 1
    for user in sorted_mm_users:
        userid = user[5]
        raw_previous_position = db.execute(f"SELECT current_position FROM leaderboard WHERE user='{userid}';").fetchone()
        previous_position = int(raw_previous_position[0])
        current_position = count
        position_change = previous_position - current_position
        db.execute(f"UPDATE leaderboard SET current_position={current_position} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET previous_position={previous_position} WHERE user={userid}")
        user_tup = (count, user[0], user[1], user[2], user[3], user[4], position_change)
        mm_counted_users.append(user_tup)
        count += 1

    return render_template("index.html", bl_users=bl_counted_users, mm_users=mm_counted_users)

@app.route("/addmember", methods=["POST"])
def addMember():
    user = {}
    raw_challenge = request.form.get("challenge")
    if raw_challenge == "Biggest Loser":
        challenge = 0
    elif raw_challenge == "Muscle Madness":
        challenge = 1
    else:
        return "CONTACT IKE and say it failed to add your challenge when joining: 231-670-0244 or ike.patton16@gmail.com"
    user["challenge"] = challenge
    raw_first_name = request.form.get("firstname")
    first_name = raw_first_name.lower()
    user["first_name"] = first_name
    raw_last_name = request.form.get("lastname")
    last_name = raw_last_name.lower()
    user["last_name"] = last_name
    username = first_name + last_name
    user["username"] = username
    raw_pin = request.form.get("pin")
    pin = int(raw_pin)
    user["pin"] = pin
    raw_height = request.form.get("height")
    if len(raw_height) < 1:
        raw_height = 0.00
    if raw_height == 0.00 and challenge == 1:
        return "HEIGHT REQUIRED FOR MUSCLE MADNESS CHALLENGE"
    height_units = request.form.get("heightunits")
    if height_units == "in":
        height = round(float(raw_height), 2)
    elif height_units == "cm":
        height = round(float(raw_height) / 2.54, 2)
    else:
        return "CONTACT IKE and say it failed to add your height when joining: 231-670-0244 or ike.patton16@gmail.com"
    user["height"] = height
    raw_private = request.form.get("private")
    if raw_private == "on":
        private = 1
    elif raw_private is None:
        private = 0
    else:
        return "CONTACT IKE and say it failed to add your privacy setting when joining: 231-670-0244 or ike.patton16@gmail.com"
    user["private"] = private

    db.execute("INSERT INTO users (first_name, last_name, username, pin, height, challenge, private) VALUES(?, ?, ?, ?, ?, ?, ?);",
               (user["first_name"], user["last_name"], user["username"], user["pin"], user["height"], user["challenge"], user["private"]))
    con.commit()
    raw_userid = db.execute(f"SELECT userid FROM users WHERE username='{user["username"]}';").fetchone()
    userid = raw_userid[0]
    db.execute(f"INSERT INTO leaderboard (user, starting_weight, current_weight, starting_musclemass, current_musclemass, current_percent_loss, current_percent_gain, current_position, previous_position) VALUES({userid}, 0, 0, 0, 0, 0, 0, 0, 0);")
    con.commit()

    return index()
    #return render_template("/getstats/<id>")

@app.route("/weighin")
def weighIn():
    raw_names = db.execute("SELECT first_name, last_name FROM users").fetchall()
    names = []
    for name in raw_names:
        fname = name[0].title()
        lname = name[1].title()
        names.append((fname, lname))
    names = sorted(names)
    return render_template("weighin.html", names=names)

@app.route("/addweight", methods=["POST"])
def addWeight():
    # Get the date for stats
    datetime = strftime("%Y-%m-%d %H:%M", localtime())

    # Cleanup form inputs
    raw_name = request.form.get("name")
    name = "".join(raw_name.lower().split())
    raw_pin = request.form.get("pin")
    pin = int(raw_pin)
    raw_weight = request.form.get("weight")
    weight_units = request.form.get("units")
    if weight_units == "lb":
        weight = round(float(raw_weight), 2)
        weight_kilo = round(float(raw_weight) / 2.2046, 2)
    elif weight_units == "kg":
        weight_kilo = round(float(raw_weight), 2)
        weight = round(float(raw_weight) * 2.2046, 2)
    else:
        return "CONTACT IKE and say it failed to add your weight when weighing in: 231-670-0244 or ike.patton16@gmail.com"
    scaleid = request.form.get("scaleid")
    checked_by = request.form.get("checkedby")

    # Confim the pin
    raw_verification_pin = db.execute(f"SELECT pin FROM users WHERE username='{name}'").fetchone()
    verification_pin = int(raw_verification_pin[0])
    if pin != verification_pin:
        return "PIN DOESN'T MATCH"

    # Get the challenge the user is in (0 for biggest loser. 1 for muscle madness)
    raw_challenge_type = db.execute(f"SELECT challenge FROM users WHERE username='{name}'").fetchone()
    challenge_type = raw_challenge_type[0]

    if challenge_type == 1:
        raw_height = db.execute(f"SELECT height FROM users WHERE username='{name}'").fetchone()
        # Height is saved in inches. This converts it to cm for the calculations
        height = round(float(raw_height[0]) * 2.54, 2)
        # All three formulas require a height in cm and a weight in kg
        boer_formula_mm = (0.407 * weight_kilo) + (0.267 * height) - 19.2
        james_formula_mm = (1.1 * weight_kilo) - 128 * (weight_kilo / height) ** 2
        hume_formula_mm = (0.32810 * weight_kilo) + (0.33929 * height) - 29.5336
        current_muscle_mass = (boer_formula_mm + james_formula_mm + hume_formula_mm) / 3
    else:
        current_muscle_mass = 0

    raw_userid = db.execute(f"SELECT userid FROM users WHERE username='{name}'").fetchone()
    userid = raw_userid[0]

    raw_starting_weight = db.execute(f"SELECT starting_weight FROM leaderboard WHERE user={userid}").fetchone()
    if raw_starting_weight[0] == 0:
        db.execute(f"UPDATE leaderboard SET starting_weight={weight} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET current_weight={weight} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET starting_musclemass={current_muscle_mass} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET current_musclemass={current_muscle_mass} WHERE user={userid}")
        #db.execute(f"UPDATE leaderboard SET current_percent_loss=0 WHERE user={userid}")
        #db.execute(f"UPDATE leaderboard SET current_percent_gain=0 WHERE user={userid}")
        percent_loss = 0
        percent_gain = 0
    else:
        db.execute(f"UPDATE leaderboard SET current_musclemass={current_muscle_mass} WHERE user={userid}")
        db.execute(f"UPDATE leaderboard SET current_weight={weight} WHERE user={userid}")
        if challenge_type == 0:
            percent_gain = 0
            raw_starting_weight = db.execute(f"SELECT starting_weight FROM leaderboard WHERE user={userid}").fetchone()
            starting_weight = raw_starting_weight[0]
            weight_loss = starting_weight - weight
            percent_loss = weight_loss / starting_weight * 100
            db.execute(f"UPDATE leaderboard SET current_percent_loss={percent_loss} WHERE user={userid}")
        elif challenge_type == 1:
            percent_loss = 0
            raw_muscle_mass = db.execute(f"SELECT starting_musclemass FROM leaderboard WHERE user={userid}").fetchone()
            starting_muscle_mass = raw_muscle_mass[0]
            muscle_gain = current_muscle_mass - starting_muscle_mass
            percent_gain = muscle_gain / starting_muscle_mass * 100
            db.execute(f"UPDATE leaderboard SET current_percent_gain={percent_gain} WHERE user={userid}")
        else:
            return "CONTACT IKE and tell him that the program failed to update your percent gain/loss on the leaderboard"
        con.commit()
    # NEED TO UPDATE LEADERBOARD POSITIONS FOR ALL USERS
    current_position = 0
    if challenge_type == 0:
        raw_results = db.execute(f"SELECT current_percent_loss FROM leaderboard ORDER BY current_percent_loss DESC").fetchmany()
        current_position = 1
        for result in raw_results:
            if result[0] == percent_loss:
                break
            else:
                current_position += 1
    elif challenge_type == 1:
        current_position = 1
        raw_results = db.execute(f"SELECT current_percent_gain FROM leaderboard ORDER BY current_percent_gain DESC").fetchmany()
        for result in raw_results:
            if result[0] == percent_gain:
                break
            else:
                current_position += 1
    else:
        return "CONTACT IKE and tell him that the program failed to update your current position on the leaderboard"

    db.execute(f"INSERT INTO stats (user, datetime, weight, checked_by, position_snapshot, percent_loss, percent_gain, scaleid) VALUES({userid}, '{datetime}', {weight}, '{checked_by}', {current_position}, {percent_loss}, {percent_gain}, '{scaleid}');")
    con.commit()

    return index()

@app.route("/getstats")
def getStats():
    return render_template("stats.html")

@app.route("/join")
def join():
    return render_template("join.html")
