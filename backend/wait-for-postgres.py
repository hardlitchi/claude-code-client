#!/usr/bin/env python3
"""
PostgreSQLが起動するまで待機するスクリプト
"""

import time
import psycopg2
import os
import sys

def wait_for_postgres():
    """PostgreSQLが利用可能になるまで待機"""
    
    # 環境変数から接続情報を取得
    db_host = os.getenv('DB_HOST', 'db')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('POSTGRES_DB', 'claude_db')
    db_user = os.getenv('POSTGRES_USER', 'claude_user')
    db_password = os.getenv('POSTGRES_PASSWORD', 'claude_password')
    
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            print(f"Attempting to connect to PostgreSQL... (attempt {i+1}/{max_retries})")
            
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_password
            )
            
            conn.close()
            print("PostgreSQL is ready!")
            return True
            
        except psycopg2.OperationalError as e:
            print(f"PostgreSQL is not ready yet: {e}")
            if i < max_retries - 1:
                print(f"Waiting {retry_interval} seconds...")
                time.sleep(retry_interval)
            else:
                print("Max retries reached. PostgreSQL is not available.")
                return False
    
    return False

if __name__ == "__main__":
    if wait_for_postgres():
        sys.exit(0)
    else:
        sys.exit(1)