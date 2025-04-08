from configuration.db_config import USERS_TABLE, TRANSACTIONS_TABLE
from configuration.config import FACE_RECOGNITION_THRESHOLD

# Register user query
register_user_query = f"""
            INSERT INTO {USERS_TABLE}
                (
                    username, 
                    face_info,
                    face_image,
                    refId,
                    associatedVerificationId,
                    companyId 
                ) 
                
                VALUES (%s, %s, %s, %s, %s, %s)
            """

get_all_users_query = f"""
            SELECT username,
                    face_image,
                    time,
                    refId,
                    companyId,
                    associatedVerificationId,
            FROM
                {USERS_TABLE}
            ORDER BY 
                time DESC;

            """

# Search before Register user query
search_before_register_query = f"""
        SELECT username , associatedverificationid  FROM {USERS_TABLE}
            WHERE (
                SELECT ( SUM(a*b) / ( SQRT(SUM(POWER(a,2))) * SQRT(SUM(POWER(b,2))) ) ) 
                        
                FROM unnest
                    (
                        ARRAY[face_info], 
                        ARRAY[%s] 
                    ) AS t(a,b)
                    
            ) > 0.4228
            AND companyId = %s
    """

# Search user query
search_query = f"""
        SELECT username, face_info FROM {USERS_TABLE}
            WHERE (
                SELECT ( SUM(a*b) / ( SQRT(SUM(POWER(a,2))) * SQRT(SUM(POWER(b,2))) ) ) 
                        
                FROM unnest
                    (
                        ARRAY[face_info], 
                        ARRAY[%s] 
                    ) AS t(a,b)
                    
            ) > {FACE_RECOGNITION_THRESHOLD}
    """


# User's picture update query
modify_user_query = f"""
                UPDATE {USERS_TABLE}
                    SET 
                        face_info = %s
                    WHERE
                    username = %s AND companyId = %s
                """


# Delete USER Query
delete_user_query = f"""
                DELETE FROM {USERS_TABLE}
                WHERE
                    username=%s AND companyId = %s
                """


# check if unique id exists are not
check_username_query = f"""
            SELECT username FROM {USERS_TABLE}
            WHERE
                username=%s AND companyId = %s
            """


# Queries related to Transactions

# Add a Transaction
add_transaction_query = f"""
            INSERT INTO {TRANSACTIONS_TABLE}
                (
                    username,
                    face_image,
                    matching_score,
                    transaction_id,
                    type,
                    status,
                    reason, 
                    refId,
                    associatedVerificationId,
                    companyId
                ) 
                
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """


# get all transactions

all_transactions_query = f"""
            SELECT username,
                    face_image,
                    matching_score,
                    transaction_id,
                    type,
                    time,
                    status,
                    reason,
                    refId,
                    associatedVerificationId,
                    companyId
            FROM
                {TRANSACTIONS_TABLE}
            ORDER BY 
                time DESC;

            """

# Delete Transaction Query
delete_transaction_query = f"""
                DELETE FROM {TRANSACTIONS_TABLE}
                WHERE
                    transaction_id=%s
                """