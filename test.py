import psycopg2

#postgresql://neondb_owner:DOmsUa0TMQ4k@ep-delicate-brook-a8o8z0ui.eastus2.azure.neon.tech/neondb?sslmode=require

conn = psycopg2.connect(
    dbname="neondb",
    user="neondb_owner",
    password="DOmsUa0TMQ4k",
    host="ep-delicate-brook-a8o8z0ui.eastus2.azure.neon.tech",
    port="5432",
    sslmode="require"
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())

cursor.close()
conn.close()
