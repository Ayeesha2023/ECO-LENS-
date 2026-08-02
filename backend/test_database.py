import os
from dotenv import load_dotenv
import mysql.connector

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

    print("="*50)
    print("DATABASE CONNECTED SUCCESSFULLY")
    print("="*50)

    cursor = conn.cursor()

    cursor.execute("SELECT DATABASE();")
    print("Current Database:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM users;")
    print("Users:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM waste_categories;")
    print("Waste Categories:", cursor.fetchone()[0])

    cursor.execute("SELECT COUNT(*) FROM bd_rag_knowledge;")
    print("Knowledge Records:", cursor.fetchone()[0])

    cursor.close()
    conn.close()

except Exception as e:
    print("Connection Failed")
    print(e)