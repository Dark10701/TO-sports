def calculate_standings_data(teams, completed_fixtures, points_win=3, points_draw=1, points_loss=0):
    if not teams:
        return []

    standings = {
        team['id']: {
            'id': team['id'], 
            'name': team['name'],
            'mp': 0, 'w': 0, 'd': 0, 'l': 0,
            'gf': 0, 'ga': 0, 'gd': 0, 'pts': 0
        } for team in teams
    }
    print(f"--- Initial Standings Dict: {standings}") # DEBUG
    print(f"--- Processing {len(completed_fixtures)} Completed Fixtures: {completed_fixtures}") # DEBUG

    for fixture in completed_fixtures:
        print(f"--- Processing Fixture: {fixture}") # DEBUG
        team1_id = fixture['team1_id']
        team2_id = fixture['team2_id']
        score1 = fixture['score1']
        score2 = fixture['score2']
        winner_id = fixture['winner_id']

        s1 = int(score1) if score1 is not None else 0
        s2 = int(score2) if score2 is not None else 0
        
        print(f"Fixture details: T1_ID={team1_id}, T2_ID={team2_id}, S1={s1}, S2={s2}, Winner_ID={winner_id}") # DEBUG

        # --- Update stats for Team 1 ---
        if team1_id in standings:
            print(f"Updating Team 1 ({standings[team1_id]['name']})") # DEBUG
            standings[team1_id]['mp'] += 1
            standings[team1_id]['gf'] += s1
            standings[team1_id]['ga'] += s2
            
            if team2_id is None: 
                standings[team1_id]['w'] += 1
                standings[team1_id]['pts'] += points_win
                print(f"  Team 1 Bye Win. New Pts: {standings[team1_id]['pts']}") # DEBUG
            elif winner_id == team1_id:
                standings[team1_id]['w'] += 1
                standings[team1_id]['pts'] += points_win
                print(f"  Team 1 Win. New Pts: {standings[team1_id]['pts']}") # DEBUG
            elif winner_id == team2_id: 
                standings[team1_id]['l'] += 1
                standings[team1_id]['pts'] += points_loss
                print(f"  Team 1 Loss. New Pts: {standings[team1_id]['pts']}") # DEBUG
            elif winner_id is None and score1 is not None and score2 is not None and s1 == s2 : # Explicitly check s1 == s2 for draw
                standings[team1_id]['d'] += 1
                standings[team1_id]['pts'] += points_draw
                print(f"  Team 1 Draw. New Pts: {standings[team1_id]['pts']}") # DEBUG
            else:
                print(f"  Team 1: No points condition met (Winner ID: {winner_id}, S1: {score1}, S2: {score2})") # DEBUG

        # --- Update stats for Team 2 (if it's not a bye) ---
        if team2_id and team2_id in standings:
            print(f"Updating Team 2 ({standings[team2_id]['name']})") # DEBUG
            standings[team2_id]['mp'] += 1
            standings[team2_id]['gf'] += s2
            standings[team2_id]['ga'] += s1

            if winner_id == team2_id:
                standings[team2_id]['w'] += 1
                standings[team2_id]['pts'] += points_win
                print(f"  Team 2 Win. New Pts: {standings[team2_id]['pts']}") # DEBUG
            elif winner_id == team1_id: 
                standings[team2_id]['l'] += 1
                standings[team2_id]['pts'] += points_loss
                print(f"  Team 2 Loss. New Pts: {standings[team2_id]['pts']}") # DEBUG
            elif winner_id is None and score1 is not None and score2 is not None and s1 == s2: # Explicitly check s1 == s2 for draw
                standings[team2_id]['d'] += 1
                standings[team2_id]['pts'] += points_draw
                print(f"  Team 2 Draw. New Pts: {standings[team2_id]['pts']}") # DEBUG
            else:
                print(f"  Team 2: No points condition met (Winner ID: {winner_id}, S1: {score1}, S2: {score2})") # DEBUG
        
        # print(f"--- Standings after fixture {fixture['id']}: {standings}") # DEBUG (optional, can be very verbose)


    standings_list = []
    for team_id in standings:
        standings[team_id]['gd'] = standings[team_id]['gf'] - standings[team_id]['ga']
        standings_list.append(standings[team_id])

    sorted_standings = sorted(
        standings_list,
        key=lambda x: (-x['pts'], -x['gd'], -x['gf'], x['name'])
    )
    print(f"--- Final Sorted Standings: {sorted_standings}") # DEBUG
    return sorted_standings