import os

TEAM_DIR = "teams"
DEFAULT_TEAM = "default_team.csv"

def get_team_path(team_name):
    safe_name = team_name.replace(" ", "_").upper()
    return os.path.join(TEAM_DIR, f"{safe_name}.csv")