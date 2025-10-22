#!/usr/bin/env python3
import psycopg2
from config import Config

def test_redshift_connection():
    try:
        Config.validate_config()
        conn_string = Config.get_redshift_connection_string()
        print(f"Connecting to: {Config.REDSHIFT_HOST}:{Config.REDSHIFT_PORT}")
        
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        print("✅ RedShift connection successful!")
        print(f"Test query result: {result}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ RedShift connection failed: {e}")
        return False

if __name__ == '__main__':
    test_redshift_connection()
