from flask import Flask
# We will import mysql.connector and manage connections in routes or helper functions

from flask import Flask
# We will import PyMySQL and manage connections in routes or helper functions

app = Flask(__name__)

# Secret key for flashing messages
app.secret_key = 'your_very_secret_key_here' # IMPORTANT: Change this in a real application!

# Database configuration
app.config['MYSQL_HOST'] = '127.0.0.1' # Explicitly use IPv4 loopback
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'aditya'
app.config['MYSQL_DB'] = 'tournament_db'

# No global MySQL object initialization here.
# Connections will be made on-demand using PyMySQL.

from app import routes
