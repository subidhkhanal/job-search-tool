"""
Hourly Job Search Automation
Runs all scrapers, scores/ranks jobs, sends email, and saves to Supabase.
Designed to run both locally and in GitHub Actions.
"""

import os
from datetime import datetime
from tracker import (
    init_db, save_scraped_job, save_email_log, get_existing_job_urls,
    save_notification, init_notifications_table,
    send_push_notifications,
)
from scraper import run_all_scrapers, _llm_filter_jobs, matches_keywords
from send_email import build_email_content, send_email, get_alert_number

# Default fallback blocked list
_DEFAULT_BLOCKED = {"turing"}


def _get_blocked_companies():
    """Try to load blocked companies from DB, fall back to hardcoded default."""
    try:
        from profile import get_blocked_companies
        blocked = get_blocked_companies()
        if blocked is not None:
            return blocked
    except Exception:
        pass
    return _DEFAULT_BLOCKED


# Backward-compatible reference
BLOCKED_COMPANIES = _DEFAULT_BLOCKED



def main():
    print("=== Hourly Job Search Automation ===")
    print(f"Running at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Initialize database
    init_db()
    init_notifications_table()

    # Run all automated scrapers
    print("Running scrapers...")
    jobs, sources_status, sources_errors = run_all_scrapers()
    print(f"\nTotal jobs found: {len(jobs)}")
    for source, count in sources_status.items():
        print(f"  {source}: {count}")
    if sources_errors:
        print(f"\nFailed scrapers: {', '.join(sources_errors.keys())}")

    # Filter out already-seen jobs (deduplication across hourly runs)
    print("\nChecking for duplicates...")
    existing_urls = get_existing_job_urls()
    new_jobs = [j for j in jobs if j.get("url", "") not in existing_urls]
    print(f"New jobs: {len(new_jobs)} (filtered out {len(jobs) - len(new_jobs)} duplicates)")

    # Filter blocked companies
    new_jobs = [j for j in new_jobs if j.get("company", "").strip().lower() not in _get_blocked_companies()]

    # Keep unfiltered jobs for email (so user can spot false negatives)
    all_new_jobs = list(new_jobs)

    # Apply LLM relevance filter (with keyword fallback) — only filtered jobs go to DB/site
    if new_jobs:
        print(f"\nRunning LLM relevance filter on {len(new_jobs)} jobs...")
        llm_result = _llm_filter_jobs(new_jobs)
        if llm_result is not None:
            new_jobs = llm_result
            print(f"  LLM filter: {len(new_jobs)} relevant jobs")
        else:
            new_jobs = [j for j in new_jobs if matches_keywords(j["title"] + " " + j.get("description", ""))]
            print(f"  Keyword fallback filter: {len(new_jobs)} relevant jobs")
        print(f"  Filtered out: {len(all_new_jobs) - len(new_jobs)} jobs (will still appear in email)")

    # Health check: if LinkedIn scraper returned 0 results, flag it
    linkedin_count = sources_status.get("LinkedIn AI/ML", 0)
    if linkedin_count == 0 and "LinkedIn AI/ML" not in sources_errors:
        print("\n[HEALTH CHECK FAILED] LinkedIn scraper returned 0 results — possible scraper failure.")
        try:
            save_notification(
                title="Scraper Health Check Failed",
                body="LinkedIn AI/ML scraper returned 0 results. Possible scraper failure — check logs.",
                notification_type="health_check",
                metadata={"source": "LinkedIn AI/ML", "timestamp": datetime.now().isoformat()},
            )
        except Exception:
            pass

    # Auto-analyze top jobs for verdict/ATS
    if new_jobs:
        print("\nRunning auto-analysis on top jobs...")
        try:
            from jd_analyzer import full_analyze, quick_ats
            for job in new_jobs[:15]:
                try:
                    result = full_analyze(job.get("title", ""), job.get("description", ""))
                    job["verdict"] = result.get("verdict_label", "")
                    job["ats_score"] = quick_ats(job.get("description", ""))
                    job["skill_match"] = result.get("skills", {}).get("match_percentage", 0)
                    job["noc_verdict"] = result.get("noc", {}).get("confidence", "")
                except Exception:
                    pass
            print(f"Auto-analysis complete for top {min(15, len(new_jobs))} jobs.")
        except ImportError:
            print("jd_analyzer not available — skipping auto-analysis.")

    # Save new jobs to database
    print("\nSaving new jobs to database...")
    for job in new_jobs:
        try:
            save_scraped_job(
                title=job.get("title", ""),
                company=job.get("company", ""),
                location=job.get("location", ""),
                source=job.get("source", ""),
                url=job.get("url", ""),
                description=job.get("description", ""),
                score=job.get("score", 0),
                verdict=job.get("verdict", ""),
                ats_score=job.get("ats_score", 0),
            )
        except Exception:
            pass

    # Only send email if there are any new jobs (filtered or unfiltered)
    if not all_new_jobs:
        print("\nNo new jobs found this run. Skipping email.")
        print("Done!")
        return

    # Build email with ALL new jobs (unfiltered) so user can spot false negatives
    print("\nBuilding email content...")
    alert_number = get_alert_number()

    # Mark which jobs passed the relevance filter
    filtered_urls = {j.get("url", "") for j in new_jobs}
    for job in all_new_jobs:
        job["filtered"] = job.get("url", "") in filtered_urls

    md_content = build_email_content(all_new_jobs, sources_status, sources_errors)

    # Send email
    print(f"Sending Job Alert #{alert_number}...")
    email_sent = send_email(md_content, alert_number=alert_number)

    # Save to Supabase so frontend can display it
    print("Saving email log to database...")
    try:
        save_email_log(
            subject=f"Job Alert #{alert_number}",
            markdown_content=md_content,
            html_content="",
            jobs_count=len(all_new_jobs),
            sources_summary=sources_status,
            email_sent=email_sent,
        )
    except Exception as e:
        print(f"  WARNING: Could not save email log to database: {e}")

    # Save in-app notification
    print("Saving in-app notification...")
    try:
        save_notification(
            title=f"Job Alert #{alert_number}",
            body=f"{len(new_jobs)} new relevant jobs ({len(all_new_jobs)} total)",
            notification_type="job_alert",
            metadata={
                "jobs_count": len(new_jobs),
                "total_count": len(all_new_jobs),
                "alert_number": alert_number,
                "sources": sources_status,
            },
        )
    except Exception as e:
        print(f"  WARNING: Could not save notification: {e}")

    # Send push notification to subscribed devices
    print("Sending push notification...")
    try:
        send_push_notifications(
            title=f"Job Alert #{alert_number}",
            body=f"{len(new_jobs)} new relevant jobs ({len(all_new_jobs)} total)",
            url="/tonight",
        )
    except Exception as e:
        print(f"  WARNING: Could not send push notification: {e}")

    print(f"\nDone! Job Alert #{alert_number} sent: {email_sent}. {len(new_jobs)} relevant jobs saved, {len(all_new_jobs)} total in email.")


if __name__ == "__main__":
    main()
