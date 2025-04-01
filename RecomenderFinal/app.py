import os
import torch
from flask import jsonify
from sentence_transformers import SentenceTransformer, util
from Movies import fetch_movies
from History import load_history, preprocess_history, get_filtered_history
import time

# Load pre-trained SBERT model
model = SentenceTransformer("all-MiniLM-L6-v2")  # Small, fast, and accurate

# Function to get SBERT embeddings
def get_embedding(text, model):
    """Generates SBERT embedding for a given text."""
    return model.encode(text, convert_to_tensor=True)

# Function to recommend movies based on browsing history
def recommend_movies(history, movies, model):
    """Computes the recommendation of movies based on browsing history."""
    start_time = time.time()
    
    recommended_movies = []

    # Aggregate all URLs' titles from browsing history
    history_texts = [str(title) for title, score in history if title]

    # Compute embeddings for all history texts (batch processing for efficiency)
    with torch.no_grad():
        history_embeddings = {text: get_embedding(text, model) for text in history_texts}

    print(f"Total history embedding time: {time.time() - start_time:.4f} seconds")

    # For each movie, calculate similarity to browsing history
    for movie in movies:
        movie_text = f"{movie['title']} {movie['tagline']} {movie['overview']} {' '.join(movie['genres'])} {' '.join(movie['keywords'])}"
        movie_embedding = get_embedding(movie_text, model)

        similarities = []
        for history_text, history_embedding in history_embeddings.items():
            similarity = util.pytorch_cos_sim(movie_embedding, history_embedding).item()
            similarities.append((history_text, similarity))

        # Best similarity (highest single match)
        Best_similarity = max(similarities, key=lambda x: x[1])[1]

        # Average of the top 5 similarities
        sorted5_similarities = sorted(similarities, key=lambda x: x[1], reverse=True)[:5]
        avg5_similarity = sum(sim for _, sim in sorted5_similarities) / len(sorted5_similarities)

        # Combined similarity / reduce best similarity effect
        combined_similarity = (Best_similarity + avg5_similarity) / 2

        recommended_movies.append({
            'title': movie['title'],
            'combined_similarity': combined_similarity,
            'overview': movie['overview'],
            'history_contributions': sorted5_similarities  
        })

    print(f"Total recommendation calculation time: {time.time() - start_time:.4f} seconds")
    
    # Return the top 5 movies sorted by combined similarity
    recommended_movies.sort(key=lambda x: x['combined_similarity'], reverse=True)
    return recommended_movies[:5]  # Return only top 5 recommendations

# Iterative decay function:
def iterative_decay_recommendations(recommended_movies):
    """
    Iteratively select the movie with the highest avg_similarity.
    Reduce by 20% the similarity values (history contributions)
    in all remaining movies if they share the same history items.
    """
    final_recommendations = []
    movies = recommended_movies[:]  # Work on a copy

    while movies:
        # Sort movies by highest similarity
        movies.sort(key=lambda m: m['combined_similarity'], reverse=True)
        best_movie = movies.pop(0)  # Select highest-ranked movie
        final_recommendations.append(best_movie)

        # Identify shared history items
        best_history_items = {history_text for history_text, _ in best_movie['history_contributions']}

        # Reduce similarity values in remaining movies
        for movie in movies:
            new_contributions = [
                (history_text, sim * 0.8 if history_text in best_history_items else sim)
                for history_text, sim in movie['history_contributions']
            ]
            movie['history_contributions'] = new_contributions
            movie['combined_similarity'] = sum(sim for _, sim in new_contributions) / len(new_contributions)

    return final_recommendations

def get_recommendations(file):
    """Handles file upload or direct file path and returns movie recommendations."""
    try:
        # Check if 'file' is an uploaded file or a file path
        if hasattr(file, "filename"):  # It's an uploaded file
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)

            file_path = os.path.join(uploads_dir, file.filename)
            file.save(file_path)  # Save the uploaded file
        else:  
            file_path = file  # Direct file path (e.g., Firefox history)

        print(f"Processing history from {file_path}")

        # Process history
        history = get_filtered_history("chrome", limit=1000)
        print(f"History processed: {history}")

        # Fetch movies and make recommendations
        movies = fetch_movies(500)
        print(f"Fetched {len(movies)} movies")

        # Compute initial recommendations
        initial_recommendations = recommend_movies(history, movies, model)

        # Apply iterative decay to refine the recommendations
        final_recommendations = iterative_decay_recommendations(initial_recommendations)

        # Return the top 5 final recommendations
        return final_recommendations[:5]  # Return top 5 recommendations
    except Exception as e:
        print(f"Error in get_recommendations: {str(e)}")
        raise e


