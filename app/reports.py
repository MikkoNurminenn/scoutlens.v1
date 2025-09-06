import os
import pandas as pd
from datetime import datetime
from slack_sdk.webhook import WebhookClient
from data_utils import list_teams
from data_utils_sqlite import get_players_by_team
from apscheduler.schedulers.blocking import BlockingScheduler

# Slack webhook URL must be set as environment variable
def send_to_slack(blocks: list):
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("Missing SLACK_WEBHOOK_URL environment variable.")
    client = WebhookClient(webhook_url)
    response = client.send(blocks=blocks)
    if response.status_code != 200:
        print(f"Failed to send Slack message: {response.status_code}, {response.body}")

# Generate a weekly team summary report
def generate_weekly_report():
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    header_text = f":trophy: *Weekly Team Summary Report* — {report_time}"
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header_text}},
        {"type": "divider"}
    ]

    teams = list_teams()
    for team in teams:
        rows = get_players_by_team(team)
        if not rows:
            continue
        cols = [
            "id", "name", "date_of_birth", "place_of_birth", "nationality", "height", "weight",
            "preferred_foot", "current_club", "club_number", "contract_start_date", "contract_end_date",
            "agent", "wage", "release_clause", "team_name"
        ]
        df = pd.DataFrame(rows, columns=cols)
        # Compute Age
        df["date_of_birth"] = pd.to_datetime(df["date_of_birth"], errors='coerce')
        today = datetime.today()
        df["Age"] = df["date_of_birth"].apply(
            lambda bd: today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            if pd.notnull(bd) else None
        )
        total_players = len(df)
        avg_age = round(df["Age"].dropna().mean(), 1)
        avg_height = round(df["height"].replace(0, pd.NA).dropna().mean(), 1)
        total_wage = int(df["wage"].sum())

        text = (
            f"*{team}*\n"
            f"• Total players: {total_players}\n"
            f"• Average Age: {avg_age}\n"
            f"• Average Height: {avg_height} cm\n"
            f"• Total Wage: €{total_wage}"
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": text}})
        blocks.append({"type": "divider"})

    send_to_slack(blocks)

if __name__ == "__main__":
    # For manual testing
    generate_weekly_report()
    # To schedule weekly reports uncomment below
    # scheduler = BlockingScheduler()
    # scheduler.add_job(generate_weekly_report, 'cron', day_of_week='mon', hour=8, minute=0)
    # print("Scheduler started: weekly reports every Monday at 08:00")
    # scheduler.start()
