import sqlite3

# Connect to the database
conn = sqlite3.connect('dinksters_database.db')
cursor = conn.cursor()

# Update the format of dates to include microsecond
query = "UPDATE voice_log SET time = CASE WHEN time LIKE '%.%' THEN time ELSE strftime('%Y-%m-%d %H:%M:%S.000000', time) END"
cursor.execute(query)

# Commit the changes and close the connection
conn.commit()
conn.close()
