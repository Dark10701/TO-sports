from flask import render_template, request, redirect, url_for, flash
from app import app
import pymysql # For database operations

# Helper function to get DB connection (consider moving to a db_utils.py later if more complex)
def get_db_connection():
    try:
        connection = pymysql.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DB'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except pymysql.MySQLError as e:
        # Log the error e
        flash(f"Database connection error: {e}", "danger")
        return None

@app.route('/')
@app.route('/index')
def index():
    # Placeholder for listing tournaments later
    # For now, just render the index page
    return render_template('index.html', tournaments=[]) # Pass empty list for now

@app.route('/create_tournament', methods=['GET', 'POST'])
def create_tournament():
    if request.method == 'POST':
        name = request.form.get('name')
        sport = request.form.get('sport')
        tournament_format = request.form.get('format') # 'format' is a keyword, using tournament_format

        if not name or not sport or not tournament_format:
            flash('All fields are required!', 'danger')
            return render_template('create_tournament.html')

        # ** DATABASE INTERACTION - Placeholder until connection is resolved **
        # print(f"Attempting to create tournament: {name}, {sport}, {tournament_format}")
        # connection = get_db_connection()
        # if connection:
        #     try:
        #         with connection.cursor() as cursor:
        #             sql = "INSERT INTO `tournaments` (`name`, `sport`, `format`) VALUES (%s, %s, %s)"
        #             cursor.execute(sql, (name, sport, tournament_format))
        #         connection.commit()
        #         flash(f"Tournament '{name}' created successfully!", 'success')
        #         return redirect(url_for('index')) # Or a page showing all tournaments
        #     except pymysql.MySQLError as e:
        #         flash(f"Error creating tournament: {e}", 'danger')
        #         # Log error e
        #     finally:
        #         if connection.open:
        #             connection.close()
        # else:
        #     # Flash message about DB connection error is handled by get_db_connection
        #     pass # Stay on the same page or redirect to an error page

        # --- Fallback for when DB connection is not working ---
        flash(f"Tournament '{name}' ({sport}, {tournament_format}) would be created (DB connection pending).", 'info')
        return redirect(url_for('index'))
        # --- End Fallback ---

    return render_template('create_tournament.html')
