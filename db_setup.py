import pymysql

# Database configuration from app.config (or define directly)
DB_HOST = '127.0.0.1' # Explicitly use IPv4 loopback
DB_USER = 'root'
DB_PASSWORD = 'aditya'
DB_NAME = 'tournament_db' # This is the database we want to create/use

def create_database():
    try:
        # Connect to MySQL server (without specifying a database initially to create it)
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            charset='utf8mb4' # Good practice for character encoding
        )
        
        with connection.cursor() as cursor:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"Database '{DB_NAME}' created or already exists.")
            
    except pymysql.MySQLError as e:
        print(f"Error connecting to MySQL or creating database: {e}")
        exit(1) # Exit if database creation/connection fails
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

def create_tables():
    try:
        # Connect specifically to the tournament_db for table creation
        connection = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME, # Connect to our specific database
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor # Optional, but good for consistency
        )
        
        with connection.cursor() as cursor:
            # SQL to create tournaments table
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS `tournaments` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `name` VARCHAR(255) NOT NULL,
                `sport` VARCHAR(100) NOT NULL,
                `format` VARCHAR(50) NOT NULL COMMENT 'e.g., league, knockout',
                `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_table_sql)
            print("Table 'tournaments' created or already exists.")

            # SQL to create participants table
            create_participants_table_sql = """
            CREATE TABLE IF NOT EXISTS `participants` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `tournament_id` INT,
                `name` VARCHAR(255) NOT NULL,
                FOREIGN KEY (`tournament_id`) REFERENCES `tournaments`(`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_participants_table_sql)
            print("Table 'participants' created or already exists.")

            # SQL to create fixtures table
            create_fixtures_table_sql = """
            CREATE TABLE IF NOT EXISTS `fixtures` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `tournament_id` INT,
                `round_number` INT,
                `match_number_in_round` INT,
                `team1_id` INT,
                `team2_id` INT NULL, 
                `status` VARCHAR(50) DEFAULT 'Scheduled',
                `score1` INT NULL,
                `score2` INT NULL,
                `winner_id` INT NULL,
                FOREIGN KEY (`tournament_id`) REFERENCES `tournaments`(`id`) ON DELETE CASCADE,
                FOREIGN KEY (`team1_id`) REFERENCES `participants`(`id`) ON DELETE SET NULL,
                FOREIGN KEY (`team2_id`) REFERENCES `participants`(`id`) ON DELETE SET NULL,
                FOREIGN KEY (`winner_id`) REFERENCES `participants`(`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
            cursor.execute(create_fixtures_table_sql)
            print("Table 'fixtures' created or already exists.")
            
        connection.commit() # Commit changes for table creation
            
    except pymysql.MySQLError as e:
        print(f"Error connecting to DB '{DB_NAME}' or creating tables: {e}")
        # Depending on desired behavior, you might want to exit or handle this
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == '__main__':
    create_database() # Ensure database exists
    create_tables()   # Create tables within the database
    print(f"Database '{DB_NAME}' and table 'tournaments' setup process complete.")

