from datetime import datetime
import sqlite3
import pandas as pd
from datetime import timedelta
# # Connect to the database
# conn = sqlite3.connect('C:\\Users\\jdlevy\\Downloads\\larrys_database_updated.db')
if __name__ == '__main__':
    conn = sqlite3.connect('../test.db')
    cursor = conn.cursor()

    # # Update the format of dates to include microsecond
    # query = "UPDATE voice_log SET time = CASE WHEN time LIKE '%.%' THEN time ELSE strftime('%Y-%m-%d %H:%M:%S.000000', time) END"
    # cursor.execute(query)

    # query = """INSERT INTO voice_log
    #             VALUES ('dinkstar', 353332394541187074, '2024-01-07 07:00:01.000000', "Larry's Gym", 1),
    #                    ('jam4bears', 390403088722165762, '2024-01-07 07:00:01.000000', "Larry's Gym", 1),
    #                     ('shamupete', 621938294422241301, '2024-01-07 07:00:03.000000', "Larry's Gym", 1),
    #                     ('bemno', 369989877229682688, '2024-01-07 07:02:04.000000', "Larry's Gym", 1),
    #                     ('dinkstar', 353332394541187074, '2024-01-07 07:49:01.000000', "Larry's Gym", 0),
    #                    ('jam4bears', 390403088722165762, '2024-01-07 07:49:01.000000', "Larry's Gym", 0),
    #                     ('shamupete', 621938294422241301, '2024-01-07 07:49:03.000000', "Larry's Gym", 0),
    #                     ('bemno', 369989877229682688, '2024-01-07 07:49:04.000000', "Larry's Gym", 0)
    #         """

    # query = "SELECT DISTINCT * FROM points"
    # query = "DROP TABLE 'larrys_database.db'"
    # query = "UPDATE points SET points_awarded = points_awarded - 2000 WHERE points_awarded > 2000"

    # query = "SELECT name FROM sqlite_master WHERE type='table'"
    # cursor.execute(query)
    # query = "DELETE FROM points WHERE rowid NOT IN (SELECT MIN(rowid) FROM points GROUP BY name, id, points_awarded, day, type)"

    # Select all rows from the points table
    # leaderboard_query = f"""SELECT name, MIN(time) as 'total'
    #                         FROM (
    #                             SELECT name, id, time
    #                             FROM voice_log
    #                             WHERE time >= "{datetime.now().date()}"
    #                         )
    #                         GROUP BY id"""

    # leaderboard_query = f"""SELECT name, SUM(points_awarded) as 'total'
    #                             FROM (
    #                                 SELECT name, id, points_awarded, day, type
    #                                 FROM points
    #
    #                             )
    #
    #                         GROUP BY id"""
    # print(leaderboard_query)
    # eight_am_today = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    # delete_query = f"DELETE FROM voice_log WHERE time > '{eight_am_today}'"
    # delete_query = f"""DELETE FROM voice_log
    #                 WHERE name = 'dinkstar'
    #                 AND time >= '2024-03-31 07:00:00.000000'"""
    #
    # cursor.execute(delete_query)

    # cursor.execute('''DROP TABLE exercise_of_the_day''')

    # points_df = pd.read_sql_query("SELECT * FROM points", conn)
    # points_df.loc[(points_df['name'] == 'dinkstar') & (points_df['day'] == '2024-04-11') & (points_df['type'] == 'DURATION'), 'points_awarded'] = 50
    # points_df.loc[(points_df['name'] == 'bemno') & (points_df['day'] == '2024-04-05'), 'points_awarded'] = 0
    # points_df.to_sql('points', conn, if_exists='replace', index=False)

    # cursor.execute("""ALTER TABLE exercise_of_the_day
    #  RENAME TO exercise_of_the_day_old;""")
    # cursor.execute("""CREATE TABLE IF NOT EXISTS exercise_of_the_day
    #                 (exercise text, date datetime, sets integer, reps integer, duration text, difficulty text, points integer, full_response text,
    #                 tldr_response text)""")
    today = datetime.now().date()
    cursor.execute(f"""DELETE FROM voice_log WHERE time >= '{today}'""")

    # latest_exercise_log_row = pd.read_sql_query("SELECT * FROM exercise_log", conn).iloc[-1]
    # cursor.execute("""INSERT INTO exercise_log (name, id, exercise, time) VALUES (?, ?, ?, ?)""", ('jam4bears', 390403088722165762, 'Boxing punches', str(pd.to_datetime(latest_exercise_log_row['time'])+ timedelta(minutes=10))))

    # cursor.execute("DELETE FROM exercise_of_the_day")
    # cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_of_the_day
    #                 (exercise text, date datetime, response text)''')
    #
    # cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_log
    #                 (name text, id int, exercise text, time datetime)''')
    #
    #
    # exercise_of_the_day_df = pd.read_sql_query("SELECT * FROM exercise_of_the_day", conn)
    # exercise = "Mountain Climbers"
    # response = "Rise and shine with a burst of energy! For your 5-minute morning spark, tackle mountain climbers at a vigorous pace of 30 seconds on, 10 seconds off. Aim for 5 rounds to scale those morning heights!"
    # date = datetime.now().date()
    # print(date)
    # print(exercise_of_the_day_df)
    # print(exercise_of_the_day_df.loc[(exercise_of_the_day_df['date'] == date)])
    # exercise_of_the_day_df.loc[(exercise_of_the_day_df['date'] == str(date)), 'response'] = response
    # exercise_of_the_day_df.loc[(exercise_of_the_day_df['date'] == str(date)), 'exercise'] = exercise
    # print(exercise_of_the_day_df)
    # exercise_of_the_day_df.to_sql('exercise_of_the_day', conn, if_exists='replace', index=False)
    # exercise = "Burpees"
    # # insert_query = f"""INSERT INTO exercise_of_the_day (?, ?, ?)"""
    #
    # cursor.execute('INSERT INTO exercise_of_the_day (exercise, date, response) VALUES (?, ?, ?)',
    #                (exercise, date, response))

    # delete_query = f"""DELETE FROM points
    #                 WHERE name = 'bemno'
    #                 AND day = '2024-01-11'"""
    #
    # cursor.execute(delete_query)

    # leaderboard_df = pd.read_sql_query(leaderboard_query, conn)
    # print(leaderboard_df)

    # print(pd.read_sql_query(query, conn))
    # cursor.execute(query)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
