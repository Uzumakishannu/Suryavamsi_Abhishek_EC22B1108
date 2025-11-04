Quant Analytics Lab (Streamlit) - Advanced
------------------------------------------
Run the full app (backend streamer + Streamlit UI) with a single command:

    python run.py

Features added in this build:
- Price comparison chart between two symbols (overlay)
- Spread & Z-score time series plotted and downloadable
- Rolling correlation chart (configurable window)
- Analysis summary box that interprets z-score, correlation, volatility
- Improved NDJSON upload safety and parsing
- Backend import path fix so frontend works when launched from frontend/

Setup:
    python -m venv venv
    source venv/bin/activate      # or venv\Scripts\activate on Windows
    pip install -r requirements.txt
    python run.py

Notes:
- If WebSocket connections fail (firewall), use NDJSON upload for offline demo.
- The backend starts automatically as a background thread.
