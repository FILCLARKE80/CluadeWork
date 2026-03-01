#!/bin/bash

# Download Chrome for Kaleido (required for Plotly chart-to-image export in PowerPoint)
echo "Downloading Chrome for Kaleido..."
if plotly_get_chrome 2>&1; then
    echo "Chrome downloaded via plotly_get_chrome."
elif python -c "import kaleido; kaleido.download_chrome()" 2>&1; then
    echo "Chrome downloaded via kaleido.download_chrome()."
else
    echo "WARNING: Chrome download failed — PowerPoint chart export will not work."
fi

# Start the Streamlit app
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
