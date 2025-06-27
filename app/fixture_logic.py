import random

def generate_league_fixtures(teams):
    """
    Generates fixtures for a league (round-robin) tournament.
    Each team plays every other team once.
    Assumes 'teams' is a list of participant objects/dictionaries, each with an 'id'.
    Returns a list of match tuples: (team1_id, team2_id)
    """
    if not teams or len(teams) < 2:
        return []

    matches = []
    # Create a list of team IDs
    team_ids = [team['id'] for team in teams]

    # Simple round-robin: iterate through all unique pairs
    for i in range(len(team_ids)):
        for j in range(i + 1, len(team_ids)):
            # Ensure order doesn't matter for now, or decide on home/away later
            # For simplicity, let team with lower index be team1, or randomize
            match = tuple(sorted((team_ids[i], team_ids[j])))
            matches.append(match)
    
    # Shuffle the matches to make the order less predictable if desired
    random.shuffle(matches)
    
    # For a more structured round-robin (e.g., Circle method), a more complex algorithm is needed,
    # especially for assigning rounds. This version just creates all pairs.
    # We will assign round numbers and match numbers in the route that calls this.
    return matches


def generate_knockout_fixtures(teams):
    """
    Generates fixtures for the first round of a knockout tournament.
    Assumes 'teams' is a list of participant objects/dictionaries, each with an 'id'.
    Handles byes if there's an odd number of teams.
    Returns a list of match tuples: (team1_id, team2_id_or_None_for_bye)
    """
    if not teams:
        return []

    team_ids = [team['id'] for team in teams]
    random.shuffle(team_ids) # Shuffle for random pairings

    matches = []
    
    # Determine number of byes needed to get to a power of 2 for next round
    # Or simply pair them up, one might get a bye directly to next round
    
    # Simple pairing, handling odd numbers with a bye
    i = 0
    while i < len(team_ids):
        if i + 1 < len(team_ids):
            matches.append((team_ids[i], team_ids[i+1]))
            i += 2
        else:
            # Last team gets a bye
            matches.append((team_ids[i], None)) # None indicates a bye for team2
            i += 1
            
    return matches

if __name__ == '__main__':
    # Example Usage (for testing this file directly)
    print("--- Testing League Fixture Generation ---")
    sample_teams_league = [{'id': 1, 'name': 'Team A'}, {'id': 2, 'name': 'Team B'}, {'id': 3, 'name': 'Team C'}, {'id': 4, 'name': 'Team D'}]
    league_matches = generate_league_fixtures(sample_teams_league)
    print(f"Teams: {sample_teams_league}")
    print(f"Generated League Matches ({len(league_matches)}): {league_matches}")
    # Expected for 4 teams: (4*3)/2 = 6 matches

    sample_teams_league_odd = [{'id': 1, 'name': 'Team A'}, {'id': 2, 'name': 'Team B'}, {'id': 3, 'name': 'Team C'}]
    league_matches_odd = generate_league_fixtures(sample_teams_league_odd)
    print(f"Teams (odd): {sample_teams_league_odd}")
    print(f"Generated League Matches ({len(league_matches_odd)}): {league_matches_odd}")
     # Expected for 3 teams: (3*2)/2 = 3 matches


    print("\n--- Testing Knockout Fixture Generation ---")
    sample_teams_knockout_even = [{'id': 1, 'name': 'Team A'}, {'id': 2, 'name': 'Team B'}, {'id': 3, 'name': 'Team C'}, {'id': 4, 'name': 'Team D'}]
    knockout_matches_even = generate_knockout_fixtures(sample_teams_knockout_even)
    print(f"Teams (even): {sample_teams_knockout_even}")
    print(f"Generated Knockout Matches ({len(knockout_matches_even)}): {knockout_matches_even}")

    sample_teams_knockout_odd = [{'id': 5, 'name': 'Team E'}, {'id': 6, 'name': 'Team F'}, {'id': 7, 'name': 'Team G'}]
    knockout_matches_odd = generate_knockout_fixtures(sample_teams_knockout_odd)
    print(f"Teams (odd): {sample_teams_knockout_odd}")
    print(f"Generated Knockout Matches ({len(knockout_matches_odd)}): {knockout_matches_odd}")

    sample_teams_knockout_single = [{'id': 8, 'name': 'Team H'}]
    knockout_matches_single = generate_knockout_fixtures(sample_teams_knockout_single)
    print(f"Teams (single): {sample_teams_knockout_single}")
    print(f"Generated Knockout Matches ({len(knockout_matches_single)}): {knockout_matches_single}")

    sample_teams_knockout_none = []
    knockout_matches_none = generate_knockout_fixtures(sample_teams_knockout_none)
    print(f"Teams (none): {sample_teams_knockout_none}")
    print(f"Generated Knockout Matches ({len(knockout_matches_none)}): {knockout_matches_none}")

