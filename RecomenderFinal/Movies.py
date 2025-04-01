import requests
import random

# Your API Key and Token
API_KEY = "fdd33b28e26c84e63392d59b9de8dbd8"
BASE_URL = "https://api.themoviedb.org/3"

def fetch_movie_details(movie_id):
    """Fetches and filters movie details from TMDb."""
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&append_to_response=keywords,credits"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error fetching movie {movie_id}: {response.json()}")
        return None

    data = response.json()

    # Extract relevant movie details
    movie_info = {
        "id": data["id"],
        "title": data["title"],
        "overview": data.get("overview", ""),
        "tagline": data.get("tagline", ""),
        "genres": [genre["name"] for genre in data.get("genres", [])],
        "keywords": [kw["name"] for kw in data.get("keywords", {}).get("keywords", [])],
        "director": next((crew["name"] for crew in data.get("credits", {}).get("crew", []) if crew["job"] == "Director"), ""),
        "vote_average": data.get("vote_average", 0),
        "vote_count": data.get("vote_count", 0),
        "popularity": data.get("popularity", 0),
    }

    return movie_info


def fetch_movies(total_movies=500):
    """Fetches a list of popular movies and their detailed info."""
    movies = []
    page = 1

    while len(movies) < total_movies:
        url = f"{BASE_URL}/discover/movie?api_key={API_KEY}&language=en-US&sort_by=popularity.desc&vote_count.gte=500&page={page}"
        response = requests.get(url)

        if response.status_code != 200:
            print("Error fetching movies:", response.json())
            break

        data = response.json()
        movie_ids = [movie["id"] for movie in data["results"]]

        for movie_id in movie_ids:
            if len(movies) >= total_movies:
                break  # Stop once we reach the desired count
            movie_details = fetch_movie_details(movie_id)
            if movie_details:
                movies.append(movie_details)

        if page >= data["total_pages"]:  # Stop if there are no more pages
            break

        page += 1  # Move to next page

    return movies

# Run this file directly to test fetching movies
if __name__ == "__main__":
    movies = fetch_movies(50)  # Fetch only 10 for testing
    for idx, movie in enumerate(movies, start=1):
        print(f"{idx}. {movie['title']} - {movie['genres']} - {movie['director']}")
