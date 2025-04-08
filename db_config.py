import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
load_dotenv()

# Register UUID
psycopg2.extras.register_uuid()

conn = psycopg2.connect(
        host=os.environ.get("HOST1"),
        database=os.environ.get("DB"),
        user=os.environ.get("USER1"),
        password=os.environ.get("PASSWORD"),
        port = int(os.environ.get("PORT"))
    )

cur = conn.cursor()



# DEFINE Table Names
USERS_TABLE = "users"
TRANSACTIONS_TABLE = "transactions"



# ==================== CREATE TABLE ========================

cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
            username text UNIQUE PRIMARY KEY NOT NULL,
            face_info decimal[] NOT NULL,
            face_image text NOT NULL,
            time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            refId text,
            companyId TEXT,
            associatedVerificationId TEXT
        );
        """
    )

conn.commit()

# ============================================================


# ==================== CREATE TRANSACTIONS TABLE ========================
"""
Table Columns,
        id(BIG-SERIAL), username, 
        type(LOGIN or REGISTER), time,
        face_image(text, path/filename), matching_score(float), 
        transaction_id(UUID), status, reason
"""


cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {TRANSACTIONS_TABLE} (
            id bigserial UNIQUE PRIMARY KEY,
            username text NOT NULL,
            face_image text NOT NULL,
            matching_score real NOT NULL,
            transaction_id uuid NOT NULL,
            type text NOT NULL,
            time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            status text NOT NULL,
            reason text NOT NULL,
            refid text,
            associatedVerificationId TEXT,
            companyId TEXT
        );
        """
    )

conn.commit()

# ============================================================
