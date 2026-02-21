import sqlite3
import pandas as pd
from datetime import datetime, timedelta

DB_PATH = "job_applications.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        role TEXT NOT NULL,
        type TEXT CHECK(type IN ('Job', 'Internship')) NOT NULL,
        platform TEXT NOT NULL,
        url TEXT,
        date_applied TEXT NOT NULL,
        status TEXT DEFAULT 'Applied',
        follow_up_date TEXT,
        noc_compatible TEXT DEFAULT 'Unknown',
        conversion_potential TEXT DEFAULT 'N/A',
        salary_range TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS scraped_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        source TEXT NOT NULL,
        url TEXT UNIQUE,
        description TEXT,
        scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
        applied INTEGER DEFAULT 0,
        dismissed INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()

def add_application(company, role, job_type, platform, url="", 
                    noc_compatible="Unknown", conversion="N/A", 
                    salary="", notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    follow_up = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
    
    c.execute('''INSERT INTO applications 
        (company, role, type, platform, url, date_applied, follow_up_date, 
         noc_compatible, conversion_potential, salary_range, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (company, role, job_type, platform, url, today, follow_up,
         noc_compatible, conversion, salary, notes))
    
    conn.commit()
    conn.close()

def update_status(app_id, new_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE applications SET status = ? WHERE id = ?", (new_status, app_id))
    conn.commit()
    conn.close()

def get_all_applications():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM applications ORDER BY date_applied DESC", conn)
    conn.close()
    return df

def get_follow_ups_due():
    conn = sqlite3.connect(DB_PATH)
    today = datetime.now().strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        "SELECT * FROM applications WHERE follow_up_date <= ? AND status = 'Applied'",
        conn, params=(today,))
    conn.close()
    return df

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    stats = {}
    c.execute("SELECT COUNT(*) FROM applications")
    stats['total'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Applied'")
    stats['applied'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Interview Scheduled'")
    stats['interviews'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Offer'")
    stats['offers'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE status = 'Rejected'")
    stats['rejected'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE type = 'Job'")
    stats['jobs'] = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM applications WHERE type = 'Internship'")
    stats['internships'] = c.fetchone()[0]
    
    c.execute("SELECT platform, COUNT(*) as count FROM applications GROUP BY platform ORDER BY count DESC")
    stats['by_platform'] = c.fetchall()
    
    c.execute("""SELECT platform, COUNT(*) as total,
        SUM(CASE WHEN status IN ('Interview Scheduled', 'Interviewed', 'Offer') THEN 1 ELSE 0 END) as responses
        FROM applications GROUP BY platform""")
    stats['response_rates'] = c.fetchall()
    
    conn.close()
    return stats

def save_scraped_job(title, company, location, source, url, description=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''INSERT OR IGNORE INTO scraped_jobs 
            (title, company, location, source, url, description)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (title, company, location, source, url, description))
        conn.commit()
    except:
        pass
    conn.close()

def get_scraped_jobs(source=None):
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM scraped_jobs WHERE dismissed = 0 AND applied = 0"
    if source:
        query += f" AND source = '{source}'"
    query += " ORDER BY scraped_at DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def mark_scraped_job(job_id, action):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if action == 'applied':
        c.execute("UPDATE scraped_jobs SET applied = 1 WHERE id = ?", (job_id,))
    elif action == 'dismissed':
        c.execute("UPDATE scraped_jobs SET dismissed = 1 WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()

def delete_application(app_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM applications WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def get_weekly_trend():
    """Get application counts grouped by week, split by type."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date_applied, type FROM applications ORDER BY date_applied",
        conn,
    )
    conn.close()
    if df.empty:
        return pd.DataFrame()

    df["date_applied"] = pd.to_datetime(df["date_applied"])
    df["week"] = df["date_applied"].dt.isocalendar().week.astype(int)
    df["year"] = df["date_applied"].dt.year

    pivot = df.groupby(["year", "week", "type"]).size().reset_index(name="count")
    pivot["label"] = "W" + pivot["week"].astype(str)
    return pivot


def get_platform_effectiveness():
    """Get total applications and positive responses per platform."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """SELECT platform,
                  COUNT(*) as total,
                  SUM(CASE WHEN status IN ('Interview Scheduled','Interviewed','Offer')
                      THEN 1 ELSE 0 END) as responses
           FROM applications
           GROUP BY platform
           ORDER BY total DESC""",
        conn,
    )
    conn.close()
    if not df.empty:
        df["rate"] = (df["responses"] / df["total"] * 100).round(1)
    return df


def get_status_funnel():
    """Get counts at each status stage for a funnel view."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    stages = [
        "Applied", "Follow-up Sent", "Interview Scheduled",
        "Interviewed", "Offer",
    ]
    counts = {}
    for stage in stages:
        c.execute(
            "SELECT COUNT(*) FROM applications WHERE status = ?", (stage,)
        )
        counts[stage] = c.fetchone()[0]
    conn.close()
    return counts


def get_role_analysis():
    """Group applications by role keywords and show conversion rates."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT role, status FROM applications", conn
    )
    conn.close()
    if df.empty:
        return pd.DataFrame()

    role_keywords = [
        "AI Developer", "AI Engineer", "ML Engineer", "AI Intern",
        "ML Intern", "Python Developer", "Backend Developer",
        "Data Scientist", "NLP", "Automation", "Full Stack",
    ]

    rows = []
    for kw in role_keywords:
        mask = df["role"].str.contains(kw, case=False, na=False)
        subset = df[mask]
        if len(subset) == 0:
            continue
        total = len(subset)
        responses = len(
            subset[subset["status"].isin(
                ["Interview Scheduled", "Interviewed", "Offer"]
            )]
        )
        rate = round(responses / total * 100, 1) if total > 0 else 0
        rows.append({
            "Role Keyword": kw,
            "Applied": total,
            "Responses": responses,
            "Response Rate": f"{rate}%",
        })

    return pd.DataFrame(rows)
