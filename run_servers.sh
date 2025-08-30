#!/bin/bash

# Start Streamlit
uv run streamlit run app/webapp.py &
STREAMLIT_PID=$!

# Start FastAPI
uv run uvicorn app.main:app --reload &
UVICORN_PID=$!

# Wait for both
wait $STREAMLIT_PID $UVICORN_PID
