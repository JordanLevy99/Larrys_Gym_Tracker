from datetime import datetime
import sqlite3
import pandas as pd
from datetime import timedelta
# # Connect to the database
# conn = sqlite3.connect('C:\\Users\\jdlevy\\Downloads\\larrys_database_updated.db')
if __name__ == '__main__':
    conn = sqlite3.connect('../larrys_database.db')
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
    cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_of_the_day
                    (exercise text, date datetime, response text)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS exercise_log
                    (name text, id int, exercise text, time datetime)''')


    response = "Rise and shine! For a burst of morning energy, sprinkle in 50 burpees over 5 minutes. That's 10 invigorating leaps per minute to kickstart your day!"
    date = datetime.now().date()
    exercise = "Burpees"
    # insert_query = f"""INSERT INTO exercise_of_the_day (?, ?, ?)"""

    cursor.execute('INSERT INTO exercise_of_the_day (exercise, date, response) VALUES (?, ?, ?)',
                   (exercise, date, response))

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
