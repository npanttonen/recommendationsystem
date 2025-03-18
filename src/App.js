import React, { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  // Fetch browsing history from Firefox (automatic detection)
  const handleFetchHistory = async () => {
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:5001/recommend/firefox");
      const data = await response.json();

      if (data.error) {
        alert("Error: " + data.error);
      } else {
        setRecommendations(data);
      }
    } catch (error) {
      console.error("Error fetching history:", error);
    } finally {
      setLoading(false);
    }
  };

  // Upload browsing history file manually
  const handleSubmit = async () => {
    if (!file) {
      alert("Please upload your browsing history file!");
      return;
    }

    setLoading(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:5001/recommend", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      setRecommendations(data);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <h1>Movie Recommender</h1>

      {/* Upload file manually */}
      <input type="file" onChange={handleFileChange} />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Loading..." : "Upload File & Get Recommendations"}
      </button>

      {/* Fetch Firefox browsing history automatically */}
      <button onClick={handleFetchHistory} disabled={loading}>
        {loading ? "Fetching..." : "Fetch Firefox History"}
      </button>

      {/* Display recommendations */}
      {recommendations.length > 0 && (
        <div className="recommendations">
          <h2>Recommended Movies</h2>
          <ul>
            {recommendations.map((movie, index) => (
              <li key={index}>
                <h3>{movie.title}</h3>
                <p>{movie.overview}</p>
                <strong>Score: {movie.combined_similarity.toFixed(4)}</strong>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
