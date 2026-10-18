"""Holt alle Aktivitäten des eingeloggten Strava-Athleten und speichert sie als JSON."""

import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://www.strava.com/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
OUTPUT_FILE = Path("data/activities.json")
PER_PAGE = 200  # Maximum laut Strava-API


def get_access_token() -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def fetch_all_activities(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    activities = []
    page = 1
    while True:
        response = requests.get(
            ACTIVITIES_URL,
            headers=headers,
            params={"page": page, "per_page": PER_PAGE},
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        activities.extend(batch)
        print(f"Seite {page}: {len(batch)} Aktivitäten")
        page += 1
    return activities


def main() -> None:
    access_token = get_access_token()
    activities = fetch_all_activities(access_token)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(activities, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(activities)} Aktivitäten gespeichert in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
