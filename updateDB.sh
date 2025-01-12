curl "https://api.sleeper.app/v1/players/nfl" -o players.json && python -c "import libs.dbutils as db; db.buildDB()"
