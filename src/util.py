import sqlite3
import pandas as pd

# # Connect to the database
conn = sqlite3.connect('larrys_database.db')
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

# query = "DELETE FROM points WHERE points_awarded > 49.86 and points_awarded < 49.87"
query = "DROP TABLE 'larrys_database.db'"
# query = "SELECT name FROM sqlite_master WHERE type='table'"
cursor.execute(query)
# print(pd.read_sql_query(query, conn))

# Commit the changes and close the connection
conn.commit()
conn.close()
