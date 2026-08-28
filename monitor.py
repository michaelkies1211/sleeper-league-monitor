import json
import urllib.request
from datetime import datetime, timezone

LEAGUE_ID = "1314660185330954240"
BASE = "https://api.sleeper.app/v1"


def get_json(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def main():
    # League information
    league = get_json(f"{BASE}/league/{LEAGUE_ID}")
    rosters = get_json(f"{BASE}/league/{LEAGUE_ID}/rosters")
    users = get_json(f"{BASE}/league/{LEAGUE_ID}/users")
    traded_picks = get_json(f"{BASE}/league/{LEAGUE_ID}/traded_picks")

    # Sleeper player database — this translates IDs into names
    players = get_json(f"{BASE}/players/nfl")

    # Current NFL state
    nfl_state = get_json(f"{BASE}/state/nfl")
    current_week = nfl_state.get("week", 1)

    users_by_id = {
        user["user_id"]: {
            "display_name": user.get("display_name"),
            "team_name": (user.get("metadata") or {}).get("team_name"),
        }
        for user in users
    }

    rosters_by_id = {}

    for roster in rosters:
        owner_id = roster.get("owner_id")
        owner = users_by_id.get(owner_id, {})

        rosters_by_id[str(roster.get("roster_id"))] = {
            "team_name": owner.get("team_name"),
            "display_name": owner.get("display_name"),
        }

    def player_info(player_id):
        player = players.get(str(player_id), {})

        return {
            "player_id": str(player_id),
            "name": player.get("full_name"),
            "position": player.get("position"),
            "nfl_team": player.get("team"),
        }

    transactions = []

    # Capture current week plus previous two weeks
    for week in range(max(1, current_week - 2), current_week + 1):
        try:
            week_transactions = get_json(
                f"{BASE}/league/{LEAGUE_ID}/transactions/{week}"
            )

            for tx in week_transactions:

                clean_tx = {
                    "transaction_id": tx.get("transaction_id"),
                    "transaction_week": week,
                    "type": tx.get("type"),
                    "status": tx.get("status"),
                    "created": tx.get("created"),
                    "adds": [],
                    "drops": [],
                    "draft_picks": tx.get("draft_picks") or [],
                }

                # Translate added players
                for player_id, roster_id in (tx.get("adds") or {}).items():
                    info = player_info(player_id)
                    team = rosters_by_id.get(str(roster_id), {})

                    clean_tx["adds"].append({
                        **info,
                        "roster_id": roster_id,
                        "team_name": team.get("team_name"),
                        "display_name": team.get("display_name"),
                    })

                # Translate dropped players
                for player_id, roster_id in (tx.get("drops") or {}).items():
                    info = player_info(player_id)
                    team = rosters_by_id.get(str(roster_id), {})

                    clean_tx["drops"].append({
                        **info,
                        "roster_id": roster_id,
                        "team_name": team.get("team_name"),
                        "display_name": team.get("display_name"),
                    })

                transactions.append(clean_tx)

        except Exception as e:
            print(f"Could not fetch transactions for week {week}: {e}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "league_id": LEAGUE_ID,
        "league_name": league.get("name"),
        "current_week": current_week,
        "rosters": [],
        "transactions": transactions,
        "traded_picks": traded_picks,
    }

    # Current rosters, ALSO translated to names
    for roster in rosters:
        owner_id = roster.get("owner_id")
        owner = users_by_id.get(owner_id, {})

        roster_players = []

        for player_id in roster.get("players") or []:
            roster_players.append(player_info(player_id))

        output["rosters"].append({
            "roster_id": roster.get("roster_id"),
            "owner_id": owner_id,
            "display_name": owner.get("display_name"),
            "team_name": owner.get("team_name"),
            "players": roster_players,
            "starters": roster.get("starters") or [],
            "reserve": roster.get("reserve") or [],
            "taxi": roster.get("taxi") or [],
        })

    with open("league_state.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(
        f"Updated league_state.json with "
        f"{len(transactions)} transactions and player names"
    )


if __name__ == "__main__":
    main()
