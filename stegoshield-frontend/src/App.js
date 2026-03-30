import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // 🔥 PARTICLES BACKGROUND
  useEffect(() => {
    const canvas = document.getElementById("particles");
    const ctx = canvas.getContext("2d");

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let particles = [];

    for (let i = 0; i < 60; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 2,
        dx: Math.random() * 0.5,
        dy: Math.random() * 0.5
      });
    }

    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      particles.forEach(p => {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(34,197,94,0.3)";
        ctx.fill();

        p.x += p.dx;
        p.y += p.dy;

        if (p.x > canvas.width) p.x = 0;
        if (p.y > canvas.height) p.y = 0;
      });

      requestAnimationFrame(animate);
    }

    animate();
  }, []);

  // ---------------- API ----------------

  const scanURL = async () => {
    if (!url) return alert("Enter URL");

    setLoading(true);
    setResult(null);

    const res = await fetch("http://127.0.0.1:5000/scan-url", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ url })
    });

    const data = await res.json();
    setResult(data);
    setLoading(false);
  };

  const scanFile = async () => {
    if (!file) return alert("Upload file");

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch("http://127.0.0.1:5000/scan-file", {
      method: "POST",
      body: formData
    });

    const data = await res.json();
    setResult(data);
    setLoading(false);
  };

  // ---------------- UI ----------------

  return (
    <div className="app">

      {/* BACKGROUND */}
      <canvas id="particles"></canvas>

      <h1 className="title">🛡 StegoShield AI</h1>

      <div className="layout">

        {/* LEFT PANEL */}
        <div className="left">
          <h3>Scan File</h3>

          <input
            type="text"
            placeholder="Paste file URL..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />

          <button onClick={scanURL}>Scan URL</button>

          <div className="divider">OR</div>

          <div className="upload-box">
            <p>Drag & Drop or Click to Upload</p>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
            />
          </div>

          <button onClick={scanFile}>Upload & Scan</button>
        </div>

        {/* RIGHT PANEL */}
        <div className="right">

          {loading && (
            <div className="loading-box">
              <div className="loader"></div>
              <p>Scanning File...</p>
            </div>
          )}

          {!loading && !result && (
            <p className="placeholder">Results will appear here</p>
          )}

          {result && (
            <div className="result-card">

              <h2>{result.message}</h2>

              {result.error ? (
                <p className="error">{result.error}</p>
              ) : (
                <>
                  <p className="score">Risk Score: {result.risk_score}</p>

                  <h1 className={`decision ${result.decision}`}>
                    {result.decision}
                  </h1>

                  <p className={`level ${result.risk_level}`}>
                    {result.risk_level}
                  </p>

                  <p>{result.download_status}</p>

                  {/* 🔥 ADDITIONAL SIGNALS */}
                  <div className="signals">
                    <p>📧 Emails Detected: {result.emails}</p>
                    <p>🔗 URLs Detected: {result.urls}</p>
                  </div>

                  {/* DOWNLOAD FILE */}
                  {result.download_url && (
                    <a href={result.download_url} target="_blank" rel="noreferrer">
                      Download File
                    </a>
                  )}

                  {/* 🔥 DOWNLOAD REPORT */}
                  {result.report_url && (
                    <a href={result.report_url} target="_blank" rel="noreferrer" className="report-btn">
                      Download Security Report
                    </a>
                  )}

                  {/* IMAGE */}
                  {result.heatmap_url && (
                    <div className="image-container">
                      <img src={result.heatmap_url} alt="heatmap" />
                    </div>
                  )}

                  {/* PDF */}
                  {!result.heatmap_url && result.download_url && (
                    <div className="pdf-box">
                      <p>📄 PDF Ready</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

export default App;