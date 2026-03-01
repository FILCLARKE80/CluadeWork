#!/bin/bash

# Download Chrome for Kaleido (required for Plotly chart-to-image export in PowerPoint)
echo "Downloading Chrome for Kaleido..."
plotly_get_chrome 2>/dev/null || python -c "import kaleido; kaleido.download_chrome()" 2>/dev/null || echo "Chrome download skipped — PowerPoint chart export may not work."

# Start the Streamlit app
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
