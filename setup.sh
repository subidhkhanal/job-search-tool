#!/bin/bash
# Job Search Tool — One-time setup script
# Run: bash setup.sh

echo "=== Job Search Tool Setup ==="
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
echo ""

# Initialize database
echo "Initializing database..."
python -c "from tracker import init_db; init_db(); print('Database initialized.')"
echo ""

# Load starter watchlist
echo "Loading starter watchlist companies..."
python -c "from tracker import init_db; init_db(); from watchlist import load_starter_list; load_starter_list(); print('Starter watchlist loaded.')"
echo ""

# Test scrapers (dry run)
echo "Testing scraper imports..."
python -c "from scraper import run_all_scrapers; print('Scraper imports OK')"
echo ""

# Check for API keys
echo "=== API Key Check ==="
if [ -z "$GMAIL_ADDRESS" ]; then
    echo "  GMAIL_ADDRESS:     not set (needed for email delivery)"
else
    echo "  GMAIL_ADDRESS:     set"
fi

if [ -z "$GMAIL_APP_PASSWORD" ]; then
    echo "  GMAIL_APP_PASSWORD: not set (needed for email delivery)"
else
    echo "  GMAIL_APP_PASSWORD: set"
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo "  GROQ_API_KEY:      not set (needed for message generation)"
else
    echo "  GROQ_API_KEY:      set"
fi
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Run the Streamlit app:  streamlit run app.py"
echo "  2. Test nightly pipeline:  python nightly.py"
echo "  3. Push to GitHub and set secrets for GitHub Actions"
echo "  4. Load Chrome extension:  chrome://extensions → Load unpacked → chrome-extension/"
echo ""
