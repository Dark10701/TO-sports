from flask import render_template, request, redirect, url_for, flash
from app import app
import pymysql # For database operations
from datetime import datetime # For formatting dates
from app import fixture_logic # Import fixture generation functions

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

# --- Helper Functions for Knockout Progression ---
def get_max_round(cursor, tournament_id):
    cursor.execute("SELECT MAX(round_number) as max_round FROM fixtures WHERE tournament_id = %s", (tournament_id,))
    result = cursor.fetchone()
    return result['max_round'] if result and result['max_round'] is not None else 0

def is_round_complete(cursor, tournament_id, round_number):
    if round_number == 0: # No rounds generated yet
        return False
    # Count total matches in the round
    cursor.execute("SELECT COUNT(*) as total_matches FROM fixtures WHERE tournament_id = %s AND round_number = %s", (tournament_id, round_number))
    total_matches = cursor.fetchone()['total_matches']
    
    # Count completed matches in the round
    cursor.execute("SELECT COUNT(*) as completed_matches FROM fixtures WHERE tournament_id = %s AND round_number = %s AND status = 'Completed'", (tournament_id, round_number))
    completed_matches = cursor.fetchone()['completed_matches']
    
    return total_matches > 0 and total_matches == completed_matches

def get_round_winners(cursor, tournament_id, round_number):
    # Fetches participants who are winners in the specified round
    sql = """
        SELECT p.id, p.name 
        FROM fixtures f
        JOIN participants p ON f.winner_id = p.id
        WHERE f.tournament_id = %s AND f.round_number = %s AND f.winner_id IS NOT NULL
        ORDER BY p.id
    """
    # Also handle byes where team2_id is NULL and status is 'Completed' (team1 is auto-winner)
    # This might require more complex logic if byes aren't automatically marked with winner_id
    # For now, assuming winner_id is populated correctly for byes upon completion.
    # If not, we'd need to adjust the query or logic here.
    # A simpler approach for now: just get winner_id's.
    # The calling function will need to construct participant-like dicts if needed by fixture_logic
    
    sql_winners = """
        SELECT DISTINCT winner_id as id 
        FROM fixtures 
        WHERE tournament_id = %s AND round_number = %s AND winner_id IS NOT NULL
    """
    cursor.execute(sql_winners, (tournament_id, round_number))
    winners_data = cursor.fetchall() # List of dicts like [{'id': winner_id1}, {'id': winner_id2}]
    
    # To pass to generate_knockout_fixtures, we might need their names too,
    # or ensure generate_knockout_fixtures can work just with IDs if we pass participant-like objects.
    # For simplicity, let's assume generate_knockout_fixtures can take {'id': value}
    # and the calling function (advance_knockout_round) will fetch names if needed for messages.
    
    # Re-fetch with names for convenience, though it's a bit redundant if generate_knockout_fixtures only needs IDs
    # This makes the list of winners more directly usable by generate_knockout_fixtures if it expects {'id': X, 'name': Y}
    detailed_winners = []
    if winners_data:
        winner_ids = [w['id'] for w in winners_data]
        if winner_ids: # Ensure winner_ids is not empty before using in IN clause
            # Create a placeholder string for IN clause: %s, %s, %s
            placeholders = ', '.join(['%s'] * len(winner_ids))
            sql_winner_details = f"SELECT id, name FROM participants WHERE id IN ({placeholders})"
            cursor.execute(sql_winner_details, tuple(winner_ids))
            detailed_winners = cursor.fetchall()
            
    return detailed_winners


@app.route('/')
@app.route('/index')
def index():
    tournaments = []
    connection = get_db_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                # Fetch raw created_at, format in Python
                sql = "SELECT id, name, sport, format, created_at FROM tournaments ORDER BY created_at DESC"
                cursor.execute(sql)
                fetched_tournaments = cursor.fetchall()
                processed_tournaments = []
                for t_data in fetched_tournaments:
                    created_at_formatted = t_data['created_at'].strftime('%Y-%m-%d %H:%M') if isinstance(t_data['created_at'], datetime) else str(t_data['created_at'])
                    processed_tournaments.append({
                        'id': t_data['id'],
                        'name': t_data['name'],
                        'sport': t_data['sport'],
                        'format': t_data['format'],
                        'created_at_formatted': created_at_formatted
                    })
                tournaments = processed_tournaments
        except pymysql.MySQLError as e:
            flash(f"Error fetching tournaments: {e}", "danger")
            # Log error e
        finally:
            if connection.open:
                connection.close()
    
    tournament_count = len(tournaments)
    return render_template('index.html', tournaments=tournaments, tournament_count=tournament_count)

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
        print(f"Attempting to create tournament: {name}, {sport}, {tournament_format}")
        connection = get_db_connection()
        if connection:
            try:
                with connection.cursor() as cursor:
                    sql = "INSERT INTO `tournaments` (`name`, `sport`, `format`) VALUES (%s, %s, %s)"
                    cursor.execute(sql, (name, sport, tournament_format))
                connection.commit()
                flash(f"Tournament '{name}' created successfully!", 'success')
                return redirect(url_for('index')) # Or a page showing all tournaments
            except pymysql.MySQLError as e:
                flash(f"Error creating tournament: {e}", 'danger')
                # Log error e
            finally:
                if connection.open:
                    connection.close()
        else:
            # Flash message about DB connection error is handled by get_db_connection
            pass # Stay on the same page or redirect to an error page

        # --- Fallback for when DB connection is not working ---
        flash(f"Tournament '{name}' ({sport}, {tournament_format}) would be created (DB connection pending).", 'info')
        return redirect(url_for('index'))
        # --- End Fallback ---

    return render_template('create_tournament.html')

@app.route('/tournament/<int:tournament_id>')
def view_tournament(tournament_id):
    tournament_name = f"Tournament ID {tournament_id}" # Default/placeholder name
    tournament_details = None 
    teams = [] 
    fixtures = []
    fixtures_generated_yet = False

    connection = get_db_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                # Fetch tournament details
                sql_select_tournament = "SELECT id, name, sport, format, created_at FROM tournaments WHERE id = %s"
                cursor.execute(sql_select_tournament, (tournament_id,))
                tournament_data = cursor.fetchone() 
                
                if tournament_data:
                    if isinstance(tournament_data['created_at'], datetime):
                        created_at_formatted = tournament_data['created_at'].strftime('%Y-%m-%d %H:%M')
                    else:
                        created_at_formatted = str(tournament_data['created_at'])
                    tournament_details = {
                        'id': tournament_data['id'],
                        'name': tournament_data['name'],
                        'sport': tournament_data['sport'],
                        'format': tournament_data['format'],
                        'created_at_formatted': created_at_formatted
                    }
                    tournament_name = tournament_details['name']

                    # Fetch teams for this tournament
                    sql_select_teams = "SELECT id, name FROM participants WHERE tournament_id = %s ORDER BY name ASC"
                    cursor.execute(sql_select_teams, (tournament_id,))
                    teams = cursor.fetchall()

                    # Fetch fixtures for this tournament & check if generated
                    # We need team names for display, so a JOIN is useful here
                    sql_select_fixtures = """
                        SELECT 
                            f.id, f.round_number, f.match_number_in_round, f.status,
                            f.score1, f.score2,
                            p1.name as team1_name, 
                            p2.name as team2_name,
                            winner.name as winner_name
                        FROM fixtures f
                        JOIN participants p1 ON f.team1_id = p1.id
                        LEFT JOIN participants p2 ON f.team2_id = p2.id  -- LEFT JOIN for byes
                        LEFT JOIN participants winner ON f.winner_id = winner.id -- LEFT JOIN for no winner yet
                        WHERE f.tournament_id = %s
                        ORDER BY f.round_number, f.match_number_in_round;
                    """
                    cursor.execute(sql_select_fixtures, (tournament_id,))
                    fixtures = cursor.fetchall()
                    if fixtures: # or check count before fetching all if performance is a concern
                        fixtures_generated_yet = True
                else:
                    flash(f"Tournament with ID {tournament_id} not found.", "warning")
        except pymysql.MySQLError as e:
            flash(f"Error fetching tournament data: {e}", "danger")
        finally:
            if connection.open:
                connection.close()
    
    return render_template('view_tournament.html', 
                           tournament_name=tournament_name, 
                           tournament_id=tournament_id,
                           tournament=tournament_details,
                           teams=teams,
                           fixtures=fixtures, # Pass fixtures to template
                           fixtures_generated_yet=fixtures_generated_yet) # Pass flag to template

@app.route('/tournament/<int:tournament_id>/add_team', methods=['POST'])
def add_team(tournament_id):
    team_name = request.form.get('team_name')
    if not team_name:
        flash('Team name cannot be empty!', 'danger')
        return redirect(url_for('view_tournament', tournament_id=tournament_id))

    connection = get_db_connection()
    if connection:
        try:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `participants` (`tournament_id`, `name`) VALUES (%s, %s)"
                cursor.execute(sql, (tournament_id, team_name))
            connection.commit()
            flash(f"Team '{team_name}' added successfully.", 'success')
        except pymysql.MySQLError as e:
            flash(f"Error adding team: {e}", 'danger')
        finally:
            if connection.open:
                connection.close()
    # If get_db_connection() returned None, it would have already flashed an error.
    # We still need to redirect. This redirect is correctly placed outside the 'if connection' block.
    return redirect(url_for('view_tournament', tournament_id=tournament_id))
    
from app import league_utils # Import the new league utilities


# Placeholder for standings calculation logic (to be moved to a new file later)
# def calculate_standings(teams, completed_fixtures, points_win=3, points_draw=1, points_loss=0):
# # This is a complex function, will be implemented in the next step.
# # For now, return an empty list or basic structure.
# standings_data = {team['id']: {'name': team['name'], 'mp': 0, 'w': 0, 'd': 0, 'l': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0} for team in teams}
# # Actual calculation logic will go here.
#    
# # Sort by points, GD, GF etc. (Placeholder sorting)
# sorted_standings = sorted(standings_data.values(), key=lambda x: x['pts'], reverse=True)
# return sorted_standings

@app.route('/tournament/<int:tournament_id>/standings')
def league_standings(tournament_id):
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('index'))

    tournament_details = None
    teams = []
    standings = []

    try:
        with connection.cursor() as cursor:
            # Fetch tournament details
            cursor.execute("SELECT id, name, format FROM tournaments WHERE id = %s", (tournament_id,))
            tournament_details = cursor.fetchone()

            if not tournament_details:
                flash('Tournament not found.', 'danger')
                return redirect(url_for('index'))
            
            if tournament_details['format'] != 'league':
                flash('Standings are only available for league tournaments.', 'warning')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            # Fetch teams (participants)
            cursor.execute("SELECT id, name FROM participants WHERE tournament_id = %s", (tournament_id,))
            teams = cursor.fetchall()

            # Fetch completed fixtures
            sql_fixtures = """
                SELECT f.*, p1.name as team1_name, p2.name as team2_name 
                FROM fixtures f
                JOIN participants p1 ON f.team1_id = p1.id
                LEFT JOIN participants p2 ON f.team2_id = p2.id 
                WHERE f.tournament_id = %s AND f.status = 'Completed'
            """
            cursor.execute(sql_fixtures, (tournament_id,))
            completed_fixtures = cursor.fetchall()
            
            # Call calculation logic from league_utils
            if teams: # Only calculate if there are teams
                standings = league_utils.calculate_standings_data(teams, completed_fixtures) 
            else: # No teams, so standings will be empty by default
                standings = []


    except pymysql.MySQLError as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for('view_tournament', tournament_id=tournament_id))
    finally:
        if connection.open:
            connection.close()

    return render_template('league_standings.html', 
                           tournament=tournament_details, 
                           standings=standings)

@app.route('/tournament/<int:tournament_id>/bracket')
def knockout_bracket(tournament_id):
    connection = get_db_connection()
    if not connection:
        flash("Database connection failed.", "danger") # Flash here if get_db_connection itself fails
        return redirect(url_for('index'))

    tournament_details = None
    rounds_data = {}
    current_max_round = 0
    max_round_is_complete = False
    can_advance_round = False

    try:
        with connection.cursor() as cursor: # Single cursor context for all DB ops in this route
            # Fetch tournament details
            cursor.execute("SELECT id, name, format FROM tournaments WHERE id = %s", (tournament_id,))
            tournament_details = cursor.fetchone()

            if not tournament_details:
                flash('Tournament not found.', 'danger')
                # No 'finally' here yet, connection will be closed by outer finally
                return redirect(url_for('index')) 
            
            if tournament_details['format'] != 'knockout':
                flash('Bracket view is only available for knockout tournaments.', 'warning')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            # Fetch all fixtures for this tournament, including team names
            sql_fixtures = """
                SELECT 
                    f.id, f.round_number, f.match_number_in_round, f.status,
                    f.score1, f.score2,
                    p1.name as team1_name, 
                    p2.name as team2_name,
                    winner.name as winner_name
                FROM fixtures f
                JOIN participants p1 ON f.team1_id = p1.id
                LEFT JOIN participants p2 ON f.team2_id = p2.id
                LEFT JOIN participants winner ON f.winner_id = winner.id
                WHERE f.tournament_id = %s
                ORDER BY f.round_number, f.match_number_in_round;
            """
            cursor.execute(sql_fixtures, (tournament_id,))
            all_fixtures = cursor.fetchall()

            for fixture in all_fixtures:
                round_num = fixture['round_number']
                if round_num not in rounds_data:
                    rounds_data[round_num] = []
                rounds_data[round_num].append(fixture)
            
            # Logic for "Advance Round" button display, using the SAME cursor
            if rounds_data: 
                print("DEBUG: About to call get_max_round")
                current_max_round = get_max_round(cursor, tournament_id)
                print(f"DEBUG: get_max_round returned: {current_max_round}")
                if current_max_round > 0:
                    print("DEBUG: About to call is_round_complete")
                    max_round_is_complete = is_round_complete(cursor, tournament_id, current_max_round)
                    print(f"DEBUG: is_round_complete returned: {max_round_is_complete}")
                    if max_round_is_complete:
                        print("DEBUG: About to call get_round_winners")
                        winners_of_max_round = get_round_winners(cursor, tournament_id, current_max_round)
                        print(f"DEBUG: get_round_winners returned: {winners_of_max_round}")
                        if len(winners_of_max_round) > 1:
                            can_advance_round = True
                        elif len(winners_of_max_round) == 1 and current_max_round > 0:
                            flash(f"Tournament finished! Winner: {winners_of_max_round[0]['name']}", "success")

    except pymysql.MySQLError as e:
        flash(f"Database error in knockout_bracket: {e}", "danger")
        # It's safer to redirect to index if a major DB error occurs during data fetching
        return redirect(url_for('index')) 
    finally:
        if connection and connection.open: # Check if connection was successfully made before trying to close
            connection.close()
            
    return render_template('knockout_bracket.html', 
                           tournament=tournament_details, 
                           rounds_data=rounds_data,
                           can_advance_round=can_advance_round,
                           current_max_round=current_max_round)


@app.route('/tournament/<int:tournament_id>/advance_round', methods=['POST'])
def advance_knockout_round(tournament_id):
    connection = get_db_connection()
    if not connection:
        return redirect(url_for('knockout_bracket', tournament_id=tournament_id))

    try:
        with connection.cursor() as cursor:
            # Verify tournament is knockout
            cursor.execute("SELECT format, name FROM tournaments WHERE id = %s", (tournament_id,))
            tournament = cursor.fetchone()
            if not tournament or tournament['format'] != 'knockout':
                flash("This action is only for knockout tournaments.", "warning")
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            current_max_round = get_max_round(cursor, tournament_id)
            if not is_round_complete(cursor, tournament_id, current_max_round):
                flash(f"Round {current_max_round} is not yet complete.", "warning")
                return redirect(url_for('knockout_bracket', tournament_id=tournament_id))

            winners_list = get_round_winners(cursor, tournament_id, current_max_round)

            if not winners_list:
                 flash(f"No winners found for round {current_max_round} to advance. Ensure matches are completed and winners determined.", "warning")
                 return redirect(url_for('knockout_bracket', tournament_id=tournament_id))
            
            if len(winners_list) == 1 and current_max_round > 0: # Tournament ended in previous round check
                flash(f"Tournament already finished! Winner: {winners_list[0]['name']}", "info")
                return redirect(url_for('knockout_bracket', tournament_id=tournament_id))
            
            if len(winners_list) < 2 : # Not enough winners to make new pairings (e.g. only 1 winner and it's not final)
                flash(f"Not enough winners ({len(winners_list)}) from round {current_max_round} to generate the next round.", "warning")
                return redirect(url_for('knockout_bracket', tournament_id=tournament_id))


            next_round_number = current_max_round + 1
            
            # Check if next round already has fixtures (e.g., if button was clicked twice quickly)
            cursor.execute("SELECT COUNT(*) as count FROM fixtures WHERE tournament_id = %s AND round_number = %s", (tournament_id, next_round_number))
            if cursor.fetchone()['count'] > 0:
                flash(f"Round {next_round_number} fixtures already exist.", "info")
                return redirect(url_for('knockout_bracket', tournament_id=tournament_id))

            # Generate fixtures for the next round using the winners
            # generate_knockout_fixtures expects a list of dicts with 'id' (and optionally 'name')
            next_round_matches = fixture_logic.generate_knockout_fixtures(winners_list)

            if not next_round_matches:
                flash("Could not generate matches for the next round (e.g. only one winner).", "info")
                # This might happen if generate_knockout_fixtures returns [] for a single winner, which is correct.
                # The len(winners_list) == 1 check above should ideally catch the tournament end.
                return redirect(url_for('knockout_bracket', tournament_id=tournament_id))

            match_in_round_counter = 1
            for match_pair in next_round_matches:
                team1_id = match_pair[0]
                team2_id = match_pair[1] # None for a bye

                sql_insert_fixture = """
                INSERT INTO fixtures 
                (tournament_id, round_number, match_number_in_round, team1_id, team2_id, status) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert_fixture, 
                               (tournament_id, next_round_number, match_in_round_counter, team1_id, team2_id, 'Scheduled'))
                match_in_round_counter += 1
            
            connection.commit()
            flash(f"Round {next_round_number} fixtures generated successfully!", 'success')

    except pymysql.MySQLError as e:
        flash(f"Database error during next round generation: {e}", "danger")
    finally:
        if connection.open:
            connection.close()
            
    return redirect(url_for('knockout_bracket', tournament_id=tournament_id))


@app.route('/match/<int:match_id>', methods=['GET', 'POST']) # Add POST method
def match_details(match_id):
    
    connection = get_db_connection()
    if not connection:
        # This case should ideally redirect to an error page or index
        # For now, let's assume if GET fails, it's handled below. If POST fails connection, it's an issue.
        flash("Database connection failed.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            score1_str = request.form.get('score1')
            score2_str = request.form.get('score2')

            # Validate scores - must be integers if provided
            score1 = int(score1_str) if score1_str and score1_str.strip() != '' else None
            score2 = int(score2_str) if score2_str and score2_str.strip() != '' else None
            
            if (score1 is not None and score1 < 0) or \
               (score2 is not None and score2 < 0):
                flash("Scores cannot be negative.", "danger")
                return redirect(url_for('match_details', match_id=match_id))

            winner_id = None
            # Fetch current team IDs for winner determination
            with connection.cursor() as cursor_fetch_teams:
                cursor_fetch_teams.execute("SELECT team1_id, team2_id FROM fixtures WHERE id = %s", (match_id,))
                current_match_teams = cursor_fetch_teams.fetchone()
            
            if current_match_teams and current_match_teams['team2_id'] is None: # Bye match
                winner_id = current_match_teams['team1_id']
                # Scores might be conventionally set for a bye, e.g., 1-0 or remain None
                # For simplicity, we'll just mark winner if it's a bye. Scores remain as entered or None.
            elif score1 is not None and score2 is not None:
                if score1 > score2:
                    winner_id = current_match_teams['team1_id']
                elif score2 > score1:
                    winner_id = current_match_teams['team2_id']
                # If score1 == score2, winner_id remains None (draw)
            
            status = 'Completed' if (score1 is not None or score2 is not None) else 'Scheduled' # If any score entered, mark completed

            with connection.cursor() as cursor_update:
                sql_update = """
                    UPDATE fixtures 
                    SET score1 = %s, score2 = %s, winner_id = %s, status = %s 
                    WHERE id = %s
                """
                cursor_update.execute(sql_update, (score1, score2, winner_id, status, match_id))
            connection.commit()
            flash("Match scores updated successfully!", "success")

        except ValueError:
            flash("Invalid score format. Scores must be numbers.", "danger")
        except pymysql.MySQLError as e:
            flash(f"Database error updating scores: {e}", "danger")
        finally:
            if connection.open: # Connection might have been closed if get_db_connection failed initially
                connection.close()
        return redirect(url_for('match_details', match_id=match_id))

    # --- GET Request Logic ---
    match_data = None
    tournament_name = "Unknown Tournament" # Default
    # Re-establish connection if it was closed by POST, or if it's the first GET
    # Note: get_db_connection() is called again here. This is acceptable for simplicity.
    # In a larger app, you might manage connection per request context.
    if not connection or not connection.open: # Ensure connection is (re)opened for GET
        connection = get_db_connection()
        if not connection:
            return redirect(url_for('index'))

    connection = get_db_connection()
    if not connection:
        return redirect(url_for('index')) # Or a more specific error page

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT 
                    f.*, 
                    t.name as tournament_name,
                    p1.name as team1_name,
                    p2.name as team2_name,
                    winner.name as winner_name
                FROM fixtures f
                JOIN tournaments t ON f.tournament_id = t.id
                JOIN participants p1 ON f.team1_id = p1.id
                LEFT JOIN participants p2 ON f.team2_id = p2.id
                LEFT JOIN participants winner ON f.winner_id = winner.id
                WHERE f.id = %s
            """
            cursor.execute(sql, (match_id,))
            match_data = cursor.fetchone()

            if not match_data:
                flash(f"Match with ID {match_id} not found.", 'warning')
                # Try to redirect to a sensible place, e.g., index or a tournament list
                # For now, redirect to index if match not found.
                return redirect(url_for('index')) 
            
            tournament_name = match_data['tournament_name']

    except pymysql.MySQLError as e:
        flash(f"Error fetching match details: {e}", 'danger')
        return redirect(url_for('index')) # Redirect on error
    finally:
        if connection.open:
            connection.close()
            
    return render_template('match_details.html', 
                           match=match_data, 
                           tournament_name=tournament_name)

@app.route('/tournament/<int:tournament_id>/remove', methods=['POST'])
def remove_tournament(tournament_id):
    connection = get_db_connection()
    if not connection:
        # Error already flashed by get_db_connection
        return redirect(url_for('index'))

    try:
        with connection.cursor() as cursor:
            # Due to ON DELETE CASCADE in participants and fixtures tables,
            # deleting from tournaments will also delete related records.
            # First, ensure the tournament exists to give a more specific error if not.
            cursor.execute("SELECT id FROM tournaments WHERE id = %s", (tournament_id,))
            tournament = cursor.fetchone()
            if not tournament:
                flash(f"Tournament with ID {tournament_id} not found for removal.", 'warning')
                return redirect(url_for('index'))

            cursor.execute("DELETE FROM tournaments WHERE id = %s", (tournament_id,))
        connection.commit()
        flash(f"Tournament (ID: {tournament_id}) and all its data removed successfully.", 'success')
    except pymysql.MySQLError as e:
        flash(f"Error removing tournament: {e}", 'danger')
    finally:
        if connection.open:
            connection.close()
            
    return redirect(url_for('index'))

@app.route('/tournament/<int:tournament_id>/generate_fixtures', methods=['POST'])
def generate_fixtures_route(tournament_id): # Renamed to avoid conflict with url_for if we name it 'generate_fixtures'
    connection = get_db_connection()
    if not connection:
        # Error already flashed by get_db_connection
        return redirect(url_for('view_tournament', tournament_id=tournament_id))

    tournament_format = None
    teams = []

    try:
        with connection.cursor() as cursor:
            # Check if fixtures already exist
            cursor.execute("SELECT COUNT(*) as count FROM fixtures WHERE tournament_id = %s", (tournament_id,))
            if cursor.fetchone()['count'] > 0:
                flash('Fixtures have already been generated for this tournament.', 'info')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            # Fetch tournament format
            cursor.execute("SELECT format FROM tournaments WHERE id = %s", (tournament_id,))
            tournament_data = cursor.fetchone()
            if not tournament_data:
                flash('Tournament not found.', 'danger')
                return redirect(url_for('index'))
            tournament_format = tournament_data['format']

            # Fetch teams (participants)
            cursor.execute("SELECT id, name FROM participants WHERE tournament_id = %s", (tournament_id,))
            teams = cursor.fetchall()

            if not teams or len(teams) < 2:
                flash('Not enough teams to generate fixtures (minimum 2 required).', 'warning')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            generated_matches = []
            if tournament_format == 'league':
                generated_matches = fixture_logic.generate_league_fixtures(teams)
            elif tournament_format == 'knockout':
                generated_matches = fixture_logic.generate_knockout_fixtures(teams)
            else:
                flash(f"Unsupported tournament format: {tournament_format}", 'danger')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            if not generated_matches:
                flash('No matches were generated. This might be due to an issue with the number of teams or format.', 'warning')
                return redirect(url_for('view_tournament', tournament_id=tournament_id))

            # Insert generated matches into the fixtures table
            # For league, all matches are typically round 1 unless a more complex round system is implemented
            # For knockout, these are round 1 matches.
            round_number = 1 
            match_in_round_counter = 1
            for match_pair in generated_matches:
                team1_id = match_pair[0]
                team2_id = match_pair[1] # This could be None for a bye in knockout

                sql_insert_fixture = """
                INSERT INTO fixtures 
                (tournament_id, round_number, match_number_in_round, team1_id, team2_id, status) 
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert_fixture, 
                               (tournament_id, round_number, match_in_round_counter, team1_id, team2_id, 'Scheduled'))
                match_in_round_counter +=1
            
            connection.commit()
            flash('Fixtures generated successfully!', 'success')

    except pymysql.MySQLError as e:
        flash(f"Database error during fixture generation: {e}", 'danger')
    finally:
        if connection.open:
            connection.close()
            
    return redirect(url_for('view_tournament', tournament_id=tournament_id))
