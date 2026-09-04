import json
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, timezone

PROFILE_URL = "https://fable.co/fabler/steena-244021637723"


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "steena-fable-sync/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


# Get Steena's public Fable username/slug
slug = urlparse(PROFILE_URL).path.rstrip("/").split("/")[-1]

# Resolve profile -> Fable user ID
profile = get_json(
    f"https://api.fable.co/api/usernames/{slug}"
)
user_id = profile["id"]

# Discover her system book lists
lists_data = get_json(
    f"https://api.fable.co/api/v2/users/{user_id}/book_lists"
)

system_lists = {
    item["system_type"]: item
    for item in lists_data["results"]
    if item.get("type") == "system"
}

# Get all of her ratings
ratings = {}

try:
    ratings_data = get_json(
        f"https://api.fable.co/api/users/{user_id}/compare/ratings?min=0"
    )

    ratings = {
        item["book"]["id"]: item.get("view_user_rating")
        for item in ratings_data
    }
except Exception as error:
    print(f"Could not fetch ratings: {error}")

# Fetch every book from every system list
all_books = []

for system_type, list_info in system_lists.items():
    list_id = list_info["id"]

    url = (
        f"https://api.fable.co/api/v2/users/{user_id}"
        f"/book_lists/{list_id}/books?limit=20"
    )

    while url:
        data = get_json(url)

        for item in data["results"]:
            book = item["book"]

            all_books.append({
                "status": system_type,
                "title": book.get("title"),
                "author": ", ".join(
                    author["name"]
                    for author in book.get("authors", [])
                ),
                "fableBookId": book.get("id"),
                "isbn": (
                    book.get("display_isbn")
                    or book.get("isbn")
                ),
                "genres": [
                    genre["name"]
                    for genre in book.get("genres", [])
                ],
                "rating": ratings.get(book.get("id")),
                "favorite": item.get("favorite", False),
                "hasReview": book.get("has_review", False),
                "reviewLink": book.get("review_link"),
                "startedReading": book.get("started_reading_at"),
                "finishedReading": book.get("finished_reading_at"),
                "note": item.get("note"),
                "sortValue": item.get("sort_value")
            })

        url = data.get("next")

# Build one clean recommendation dataset
output = {
    "lastUpdated": datetime.now(timezone.utc).isoformat(),
    "profile": {
        "displayName": profile.get("display_name"),
        "profileUrl": profile.get("url"),
        "userId": user_id
    },
    "lists": {
        system_type: {
            "id": info["id"],
            "count": info["count"],
            "privacy": info["privacy"]
        }
        for system_type, info in system_lists.items()
    },
    "books": all_books
}

# GitHub Actions will write this directly into the repository
filename = "steena-reading-history.json"

with open(filename, "w", encoding="utf-8") as file:
    json.dump(output, file, indent=2, ensure_ascii=False)

print(f"Profile: {profile.get('display_name')}")
print(f"Books fetched: {len(all_books)}")
print(f"Ratings found: {len(ratings)}")
print(f"Saved: {filename}")
