#!/bin/bash
# Job Search Tool — One-time setup script
# Run: bash setup.sh

echo "=== Job Search Tool Setup ==="
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r backend/requirements.txt
echo ""

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend && npm install && cd ..
echo ""

# Test module imports
echo "Testing module imports..."
cd backend/modules && python -c "from hourly import score_job; print('Module imports OK')" && cd ../..
echo ""

# Check for API keys
echo "=== API Key Check ==="
if [ -z "$GROQ_API_KEY" ]; then
    echo "  GROQ_API_KEY:      not set (needed for message generation)"
else
    echo "  GROQ_API_KEY:      set"
fi
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Start the backend:    cd backend && uvicorn app.main:app --reload"
echo "  2. Start the frontend:   cd frontend && npm run dev"
echo "  3. Push to GitHub and set secrets for GitHub Actions"
echo "  4. Load Chrome extension: chrome://extensions → Load unpacked → chrome-extension/"
echo ""
