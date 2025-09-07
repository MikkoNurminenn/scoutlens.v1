# csv_importer.py

import pandas as pd
from app.data_utils import (
    BASE_DIR,
    save_players,
    save_seasonal_stats,
    load_players,
    MASTER_FIELDS,
)
from pathlib import Path

def import_master_csv(uploaded_csv_path: str, team_name: str) -> None:
    """
    Import a MASTER-format CSV file and load only valid fields for ScoutLens.
    """
    df = pd.read_csv(uploaded_csv_path)

    filtered = {}
    for col in MASTER_FIELDS:
        if col in df.columns:
            filtered[col] = df[col]
        else:
            filtered[col] = [None] * len(df)

    clean_df = pd.DataFrame(filtered)
    save_players(clean_df, team_name)
    print(f"✅ Imported {len(clean_df)} players to {team_name} successfully!")

def import_seasonal_stats_csv(uploaded_csv_path: str, team_name: str) -> None:
    """
    Import seasonal stats CSV and save into seasonal_stats.csv
    """
    df = pd.read_csv(uploaded_csv_path)

    if 'PlayerID' not in df.columns or 'Season' not in df.columns:
        raise ValueError("CSV must contain at least 'PlayerID' and 'Season' columns.")

    duplicates = df.duplicated(subset=['PlayerID', 'Season'])
    if duplicates.any():
        duplicate_rows = df.loc[duplicates, ['PlayerID', 'Season']]
        print(f"🚨 Duplicate PlayerID+Season found:\n{duplicate_rows}")
        raise ValueError("Resolve duplicate PlayerID + Season combinations before importing.")

    save_seasonal_stats(df, team_name)
    print(f"✅ Imported {len(df)} seasonal stats entries to {team_name} successfully!")

def import_player_update_csv(uploaded_csv_path: str, team_name: str) -> None:
    """
    Update existing player records based on PlayerID.
    CSV must contain 'PlayerID' column for updates.
    """
    update_df = pd.read_csv(uploaded_csv_path)

    if 'PlayerID' not in update_df.columns:
        raise ValueError("CSV must contain 'PlayerID' column to update players. Make sure your CSV has a 'PlayerID' header.")

    master_df = load_players(team_name)

    # Merge updates based on PlayerID
    master_df.set_index('PlayerID', inplace=True)
    update_df.set_index('PlayerID', inplace=True)

    for col in update_df.columns:
        if col not in master_df.columns:
            print(f"⚠️ Skipping unknown field: {col}")
            continue
        master_df.update(update_df[[col]])

    master_df.reset_index(inplace=True)
    save_players(master_df, team_name)
    print(f"✅ Updated {len(update_df)} players for {team_name} successfully!")

# Helper if you want to call directly from command-line or dev console
if __name__ == "__main__":
    # EXAMPLE USAGE
    # import_master_csv("/path/to/master_upload.csv", "Real Madrid")
    # import_seasonal_stats_csv("/path/to/seasonal_upload.csv", "Real Madrid")
    # import_player_update_csv("/path/to/player_update_upload.csv", "Real Madrid")
    pass