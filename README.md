# 🎯 AI-Powered Job Search Assistant

A Streamlit-based tool that automates and streamlines the job search process for AI/ML roles in India. Built with Python, OpenAI API, and SQLite.

## Features

### 🔍 Job Scraper
- Auto-scrapes AI/ML job listings from **Remotive**, **HackerNews Who's Hiring**, and **Arbeitnow**
- Pre-built search URLs for **Wellfound**, **LinkedIn**, **YC Startups** (manual apply — automation gets accounts banned)
- Filters jobs by AI/ML keywords automatically

### ✍️ AI Message Generator (OpenAI-powered)
- **Cold DMs** — Personalized outreach to founders/hiring managers (2 variants per company)
- **Follow-ups** — Smart follow-up messages that add value, not just "checking in"
- **Cover Letters** — Concise, non-generic, under 200 words
- **Thank You Notes** — Post-interview messages referencing specific discussion points

### 📋 Application Tracker
- Log every application with immigration-relevant metadata (NOC compatibility, conversion potential)
- Auto-sets 7-day follow-up reminders
- Filter by status, type (job/internship), platform
- Response rate analytics by platform

### 📊 Dashboard
- Weekly progress tracking (target: 50 applications/week)
- Follow-up reminders
- Platform response rate comparison
- Job vs internship split analysis

## Setup

```bash
# Clone or download the project
cd job_search_tool

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

## Configuration

- **OpenAI API Key**: Enter in the sidebar. Only needed for the Message Generator.
- **No other API keys needed** — all scrapers use free public APIs.

## Tech Stack

- **Frontend**: Streamlit
- **AI**: OpenAI GPT-4o-mini (for message generation)
- **Database**: SQLite (local, no server needed)
- **Scraping**: requests + BeautifulSoup
- **Data**: pandas

## Project Structure

```
job_search_tool/
├── app.py                 # Main Streamlit app
├── scraper.py             # Job scraping from multiple sources
├── message_generator.py   # AI-powered message generation
├── tracker.py             # SQLite application tracker
├── requirements.txt       # Dependencies
└── README.md              # This file
```

## Immigration Filter

Every job opportunity is evaluated through a Canadian PR immigration lens:
- ✅ Paid, 30+ hours/week
- ✅ NOC-compatible role title
- ✅ Detailed experience letter possible
- ✅ Conversion potential (for internships)

## Portfolio Note

This project demonstrates: Python, API integration (OpenAI), web scraping, database management (SQLite), full-stack development (Streamlit), and practical problem-solving — all skills relevant for Gen AI developer roles.
