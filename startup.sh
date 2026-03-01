#!/bin/bash

# Download Chrome for Kaleido (required for Plotly chart-to-image export in PowerPoint)
echo "Downloading Chrome for Kaleido..."
if python -c "import kaleido; kaleido.get_chrome_sync()" 2>&1; then
    echo "Chrome downloaded via kaleido.get_chrome_sync()."
elif plotly_get_chrome 2>&1; then
    echo "Chrome downloaded via plotly_get_chrome."
else
    echo "WARNING: Chrome download failed — PowerPoint chart export will not work."
fi

# Start the Streamlit app
python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
