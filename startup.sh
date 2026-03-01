#!/bin/bash

# Azure App Service startup script for Streamlit
# Azure injects the PORT environment variable (default 8000)
python -m streamlit run app.py \
    --server.port=${PORT:-8000} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false
