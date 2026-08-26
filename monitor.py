import json
import urllib.request
from datetime import datetime, timezone

LEAGUE_ID = "1314660185330954240"
BASE = "https://api.sleeper.app/v1"


def get_json(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.load(response)


def main():
    league = get_json(f"{BASE}/league/{LEAGUE_ID}")
    rosters = get_json(f"{BASE}/league/{LEAGUE_ID}/rosters")
    users = get_json(f"{BASE}/league/{LEAGUE_ID}/users")
    traded_picks = get_json(f"{BASE}/league/{LEAGUE_ID}/traded_picks")

    nfl_state = get_json(f"{BASE}/state/nfl")
    current_week = nfl_state.get("week", 1)

    transactions = []

    # Grab current week AND prior 2 weeks so recent drops don't disappear
    for week in range(max(1, current_week - 2), current_week + 1):
        try:
            week_transactions = get_json(
                f"{BASE}/league/{LEAGUE_ID}/transactions/{week}"
            )

            for tx in week_transactions:
                tx["transaction_week"] = week

            transactions.extend(week_transactions)

        except Exception as e:
            print(f"Could not fetch transactions for week {week}: {e}")

    users_by_id = {
        user["user_id"]: {
            "display_name": user.get("display_name"),
            "team_name": (user.get("metadata") or {}).get("team_name"),
        }
        for user in users
    }

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": LEAGUE_ID,
        "league_name": league.get("name"),
        "current_week": current_week,
        "rosters": [],
        "transactions": transactions,
        "traded_picks": traded_picks,
    }

    for roster in rosters:
        owner_id = roster.get("owner_id")
        owner = users_by_id.get(owner_id, {})

        output["rosters"].append({
            "roster_id": roster.get("roster_id"),
            "owner_id": owner_id,
            "display_name": owner.get("display_name"),
            "team_name": owner.get("team_name"),
            "players": roster.get("players") or [],
            "starters": roster.get("starters") or [],
            "reserve": roster.get("reserve") or [],
            "taxi": roster.get("taxi") or [],
        })

    with open("league_state.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Updated league_state.json with {len(transactions)} transactions")


if __name__ == "__main__":
    main()
