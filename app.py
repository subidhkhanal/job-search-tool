import hmac
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from groq import Groq

from tracker import (
    init_db, add_application, update_status, get_all_applications,
    get_follow_ups_due, get_stats, get_scraped_jobs, mark_scraped_job,
    delete_application
)
from scraper import (
    run_all_scrapers, scrape_wellfound_search_hint,
    scrape_linkedin_search_urls
)
from message_generator import (
    generate_cold_dm, generate_follow_up, generate_cover_letter,
    generate_thank_you
)
from jd_analyzer import full_analyze, quick_analyze
from resume_tailor import (
    suggest_project_order, suggest_skill_order,
    analyze_gaps, generate_summary_lines
)
from tracker import (
    get_weekly_trend, get_platform_effectiveness,
    get_status_funnel, get_role_analysis,
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_new_watchlist_jobs, mark_watchlist_job_seen,
)
from watchlist import check_all_watchlist, load_starter_list, STARTER_COMPANIES
from nightly import score_job, llm_rerank_jobs
from url_store import load_seen, save_seen, is_new, mark_seen

# --- Page Config ---
st.set_page_config(
    page_title="Subidh's Job Search HQ",
    page_icon="🎯",
    layout="wide"
)


# --- Authentication ---
def check_password():
    """Show login form and return True if credentials are correct."""
    def password_entered():
        if (
            hmac.compare_digest(st.session_state["username"], st.secrets.credentials.username)
            and hmac.compare_digest(st.session_state["password"], st.secrets.credentials.password)
        ):
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 Login")
    st.text_input("Username", key="username")
    st.text_input("Password", type="password", key="password")
    st.button("Log in", on_click=password_entered)

    if "authenticated" in st.session_state and not st.session_state["authenticated"]:
        st.error("Wrong username or password.")
    return False


if not check_password():
    st.stop()

# --- Init ---
init_db()

# --- Sidebar ---
st.sidebar.title("🎯 Job Search HQ")
page = st.sidebar.radio("Navigate", [
    "📊 Dashboard",
    "🎯 Tonight's Plan",
    "🔎 JD Analyzer",
    "🔍 Job Scraper",
    "🏢 Watchlist",
    "✍️ Message Generator",
    "📄 Resume Tailor",
    "📋 Application Tracker",
    "🔗 Quick Links"
])

# API Key in sidebar
api_key = st.sidebar.text_input("Groq API Key", type="password",
                                 help="Needed for message generation only")

# --- Immigration Filter Reminder ---
st.sidebar.markdown("---")
st.sidebar.markdown("### 🇨🇦 Immigration Filter")
st.sidebar.markdown("""
Before applying, verify:
- ✅ Paid, 30+ hrs/week
- ✅ NOC-compatible title
- ✅ Experience letter possible
- ✅ Conversion potential (internships)
""")

# ===================== DASHBOARD =====================
if page == "📊 Dashboard":
    st.title("📊 Application Dashboard")
    
    stats = get_stats()
    
    # Top metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Applied", stats['total'])
    col2.metric("Awaiting Response", stats['applied'])
    col3.metric("Interviews", stats['interviews'])
    col4.metric("Offers", stats['offers'])
    col5.metric("Rejected", stats['rejected'])
    
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Job vs Internship Split")
        st.write(f"🏢 Jobs: {stats['jobs']}  |  🎓 Internships: {stats['internships']}")
        
        if stats['by_platform']:
            st.subheader("Applications by Platform")
            platform_df = pd.DataFrame(stats['by_platform'], columns=['Platform', 'Count'])
            st.bar_chart(platform_df.set_index('Platform'))
    
    with col_b:
        st.subheader("Response Rates by Platform")
        if stats['response_rates']:
            for platform, total, responses in stats['response_rates']:
                rate = (responses / total * 100) if total > 0 else 0
                st.write(f"**{platform}**: {responses}/{total} ({rate:.0f}%)")
        else:
            st.info("Start applying to see response rates!")
    
    # Follow-ups due
    st.markdown("---")
    st.subheader("⏰ Follow-ups Due Today")
    follow_ups = get_follow_ups_due()
    if len(follow_ups) > 0:
        for _, row in follow_ups.iterrows():
            st.warning(f"📩 Follow up with **{row['company']}** for {row['role']} ({row['platform']})")
    else:
        st.success("No follow-ups due today!")
    
    # Weekly targets
    st.markdown("---")
    st.subheader("📅 This Week's Progress")
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    all_apps = get_all_applications()
    if len(all_apps) > 0:
        this_week = all_apps[all_apps['date_applied'] >= week_ago]
        weekly_count = len(this_week)
        st.progress(min(weekly_count / 50, 1.0))
        st.write(f"**{weekly_count}/50** applications this week")
    else:
        st.progress(0.0)
        st.write("**0/50** applications this week — time to start!")

    # ============ ANALYTICS SECTION ============
    st.markdown("---")
    st.header("📈 Analytics")

    # Chart 1: Weekly Application Trend
    weekly = get_weekly_trend()
    if not weekly.empty:
        st.subheader("Weekly Application Trend")
        chart_data = weekly.pivot_table(
            index="label", columns="type", values="count", aggfunc="sum"
        ).fillna(0)
        st.line_chart(chart_data)

    # Chart 2: Platform Effectiveness
    plat_eff = get_platform_effectiveness()
    if not plat_eff.empty:
        st.subheader("Platform Effectiveness")
        for _, row in plat_eff.iterrows():
            col_l, col_r = st.columns([3, 1])
            with col_l:
                st.write(f"**{row['platform']}**")
                st.progress(min(row['rate'] / 100, 1.0) if row['rate'] > 0 else 0.0)
            with col_r:
                st.write(f"{int(row['responses'])}/{int(row['total'])} ({row['rate']}%)")

    # Chart 3: Status Funnel
    funnel = get_status_funnel()
    if sum(funnel.values()) > 0:
        st.subheader("Application Funnel")
        funnel_df = pd.DataFrame([
            {"Stage": stage, "Count": count}
            for stage, count in funnel.items()
        ])
        st.bar_chart(funnel_df.set_index("Stage"))

        # Conversion rates
        stages_list = list(funnel.keys())
        conversions = []
        for i in range(len(stages_list) - 1):
            curr = funnel[stages_list[i]]
            nxt = funnel[stages_list[i + 1]]
            rate = f"{nxt/curr*100:.1f}%" if curr > 0 else "—"
            conversions.append(f"{stages_list[i]}: {curr} → {stages_list[i+1]}: {nxt} ({rate})")
        for c in conversions:
            st.caption(c)

    # Chart 4: Role Type Analysis
    role_df = get_role_analysis()
    if not role_df.empty:
        st.subheader("Role Type Analysis")
        st.dataframe(role_df, use_container_width=True, hide_index=True)

    # Insight Box
    if not plat_eff.empty or not role_df.empty:
        st.subheader("💡 Insights")
        insights = []

        if not plat_eff.empty:
            best = plat_eff.loc[plat_eff["rate"].idxmax()]
            if best["rate"] > 0:
                insights.append(
                    f"Your best platform: **{best['platform']}** "
                    f"({int(best['responses'])} responses from {int(best['total'])} applications)"
                )

        try:
            overdue = get_follow_ups_due()
            if len(overdue) > 0:
                insights.append(
                    f"You haven't followed up on **{len(overdue)} applications** that are overdue"
                )
        except Exception:
            pass

        if not role_df.empty and len(role_df) >= 2:
            best_role = role_df.sort_values("Responses", ascending=False).iloc[0]
            if best_role["Responses"] > 0:
                insights.append(
                    f"**{best_role['Role Keyword']}** roles are converting best — consider increasing applications for this type"
                )

        if insights:
            for ins in insights:
                st.info(ins)
        else:
            st.info("Keep applying — insights will appear after you have more data!")

# ===================== TONIGHT'S PLAN =====================
elif page == "🎯 Tonight's Plan":
    st.title("🎯 Tonight's Battle Plan")
    st.caption("Run all scrapers, score jobs, and get your nightly action plan — right here.")

    if st.button("🚀 Generate Tonight's Plan", type="primary"):
        # --- Run scrapers ---
        with st.spinner("Scraping all sources..."):
            jobs, sources_status, sources_errors = run_all_scrapers()

        # --- Scrape Summary ---
        st.subheader("📡 Scrape Summary")
        summary_rows = []
        for source, count in sources_status.items():
            if source in sources_errors:
                status = "❌ FAILED"
            elif count == 0:
                status = "⚠️ EMPTY"
            else:
                status = "✅ OK"
            summary_rows.append({"Source": source, "Jobs Found": count, "Status": status})
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

        if sources_errors:
            for src, err in sources_errors.items():
                st.error(f"{src}: {err[:100]}")

        # --- Watchlist ---
        watchlist_results = {}
        with st.spinner("Checking watchlist companies..."):
            try:
                watchlist_results = check_all_watchlist()
            except Exception as e:
                st.warning(f"Watchlist check skipped: {e}")

        # --- Freshness tagging ---
        seen = load_seen()
        for job in jobs:
            url = job.get("url", "")
            job["is_new"] = is_new(url, seen)
            mark_seen(url, seen)

        # --- Score jobs ---
        for job in jobs:
            job["score"] = score_job(job)
        jobs = [j for j in jobs if j["score"] > -100]
        jobs.sort(key=lambda j: j["score"], reverse=True)

        # --- LLM re-ranking ---
        with st.spinner("Running LLM re-ranking on top candidates..."):
            jobs = llm_rerank_jobs(jobs, top_n=20)

        # --- Save seen URLs ---
        save_seen(seen)

        # Split new vs seen
        new_jobs = [j for j in jobs if j.get("is_new", True)]
        seen_jobs = [j for j in jobs if not j.get("is_new", True)]

        new_count = len(new_jobs)
        high_rel = sum(1 for j in jobs if j.get("score", 0) >= 40)
        st.markdown(f"**Total: {len(jobs)}** | **New tonight: {new_count}** | **High relevance: {high_rel}**")
        st.markdown("---")

        # --- Follow-ups ---
        st.subheader("⏰ Phase 1: Follow-ups")
        try:
            follow_ups = get_follow_ups_due()
            if not follow_ups.empty:
                for _, fu in follow_ups.iterrows():
                    st.warning(f"📩 Follow up: **{fu['company']}** — {fu['role']} ({fu.get('platform', '')})")
            else:
                st.success("No follow-ups due tonight. ✅")
        except Exception:
            st.success("No follow-ups due tonight. ✅")

        # --- Watchlist Alerts ---
        if watchlist_results:
            st.markdown("---")
            st.subheader("🏢 Watchlist Alerts")
            for company, wl_jobs in watchlist_results.items():
                for wj in wl_jobs:
                    st.info(f"🆕 **{company}** posted: \"{wj['title']}\" — [Apply here]({wj['url']})")

        # --- Phase 2: NEW Jobs Table ---
        st.markdown("---")
        st.subheader(f"🔍 Phase 2: Top NEW Jobs ({len(new_jobs)} found)")

        if new_jobs:
            table_rows = []
            for idx, j in enumerate(new_jobs[:15], 1):
                score = j.get("score", 0)
                if score >= 40:
                    tier = "🔥"
                elif score >= 20:
                    tier = "📌"
                else:
                    tier = "📋"

                # Verdict
                try:
                    verdict = quick_analyze(j.get("title", ""), j.get("description", ""))
                    parts = verdict.split("|")
                    verdict_short = f"{parts[0].strip()} · {parts[2].strip()}" if len(parts) >= 3 else verdict
                except Exception:
                    verdict_short = "—"

                llm_reason = j.get("llm_reason", "") or "—"

                table_rows.append({
                    "#": f"{tier} {idx}",
                    "Company": j.get("company", "Unknown")[:25],
                    "Title": j.get("title", "Untitled")[:50],
                    "Score": score,
                    "Verdict": verdict_short,
                    "LLM Take": llm_reason[:40],
                    "Location": j.get("location", "")[:25],
                    "URL": j.get("url", ""),
                })

            df_new = pd.DataFrame(table_rows)
            st.dataframe(
                df_new,
                column_config={
                    "URL": st.column_config.LinkColumn("Apply", display_text="Apply →"),
                },
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No new jobs found tonight. Check 'Still Open' below or manual links.")

        # --- Still Open ---
        still_open = [j for j in seen_jobs if j.get("score", 0) >= 30]
        if still_open:
            st.markdown("---")
            st.subheader(f"📂 Still Open (Seen Before, Score ≥ 30) — {len(still_open)} jobs")
            so_rows = []
            for idx, j in enumerate(still_open[:10], 1):
                so_rows.append({
                    "#": idx,
                    "Company": j.get("company", "Unknown")[:25],
                    "Title": j.get("title", "Untitled")[:50],
                    "Score": j.get("score", 0),
                    "Location": j.get("location", "")[:25],
                    "URL": j.get("url", ""),
                })
            st.dataframe(
                pd.DataFrame(so_rows),
                column_config={
                    "URL": st.column_config.LinkColumn("Apply", display_text="Apply →"),
                },
                use_container_width=True,
                hide_index=True,
            )

        # --- Phase 3: Manual Links ---
        st.markdown("---")
        st.subheader("💼 Phase 3: Manual Platform Applications")

        col_wf, col_li = st.columns(2)
        with col_wf:
            st.markdown("**Wellfound (5-8 apps)**")
            for url in scrape_wellfound_search_hint():
                st.markdown(f"- [{url[:60]}...]({url})")
        with col_li:
            st.markdown("**LinkedIn Easy Apply (10-15 apps)**")
            for item in scrape_linkedin_search_urls():
                st.markdown(f"- [{item['query']}]({item['url']})")

        # --- Phase 4: Cold DMs ---
        all_scored = new_jobs + seen_jobs
        top3 = [j for j in all_scored[:5] if j.get("score", 0) >= 30][:3]
        if top3:
            st.markdown("---")
            st.subheader("🎯 Phase 4: Cold DM Targets")
            for j in top3:
                st.markdown(f"- **{j['company']}** — {j['title']} (Score: {j.get('score', 0)})")

        st.markdown("---")
        st.caption(f"Generated at {datetime.now().strftime('%I:%M %p on %A, %B %d, %Y')}")

# ===================== JD ANALYZER =====================
elif page == "🔎 JD Analyzer":
    st.title("🔎 JD Analyzer")
    st.caption("Paste a job description to get NOC compatibility, skill match %, red flags, and a verdict — in seconds.")

    jd_title = st.text_input("Job Title", placeholder="e.g. AI Engineer, Software Developer")
    jd_text = st.text_area("Paste the Full Job Description", height=300,
                           placeholder="Paste the entire JD here...")

    if st.button("Analyze", type="primary"):
        if jd_title and jd_text:
            result = full_analyze(jd_title, jd_text)

            # --- Verdict (top) ---
            verdict_colors = {"apply": "green", "caution": "orange", "skip": "red"}
            vcolor = verdict_colors.get(result["verdict"], "gray")
            st.markdown(f"### {result['verdict_label']}")
            st.caption(result["verdict_reason"])
            st.markdown("---")

            col1, col2 = st.columns(2)

            # --- NOC Compatibility ---
            with col1:
                st.subheader("NOC Compatibility")
                noc = result["noc"]
                st.markdown(noc["message"])
                if noc["matched_duties"]:
                    st.write("**Matched duties:**")
                    for d in noc["matched_duties"]:
                        st.write(f"  - {d}")

            # --- Skill Match ---
            with col2:
                st.subheader("Skill Match")
                skills = result["skills"]
                pct = skills["match_percentage"]
                st.metric("Match", f"{pct}%",
                          delta=f"{len(skills['matched'])}/{skills['total_required']} skills")

                if skills["matched"]:
                    st.write("**\u2705 Skills you have:**")
                    st.success(", ".join(skills["matched"]))
                if skills["gaps"]:
                    st.write("**\u274c Gaps:**")
                    st.error(", ".join(skills["gaps"]))

            # --- Red Flags ---
            st.markdown("---")
            st.subheader("Red Flags")
            if result["red_flags"]:
                for flag in result["red_flags"]:
                    st.warning(f"\U0001f6a9 {flag['message']} (triggered by: *{flag['trigger']}*)")
            else:
                st.success("No red flags detected!")

        else:
            st.error("Enter both a job title and the job description.")

# ===================== JOB SCRAPER =====================
elif page == "🔍 Job Scraper":
    st.title("🔍 Job Scraper")
    st.caption("Scrapes AI/ML jobs from free public APIs. LinkedIn and Wellfound links are for manual browsing (automation gets you banned).")
    
    tab1, tab2, tab3 = st.tabs(["🤖 Auto-Scrape", "🔗 Manual Search Links", "📥 Saved Jobs"])
    
    with tab1:
        if st.button("🚀 Scrape All Sources", type="primary"):
            with st.spinner("Scraping Remotive, HN Who's Hiring, Arbeitnow..."):
                jobs, status, _errors = run_all_scrapers()
            
            st.success(f"Found {len(jobs)} relevant jobs!")
            for source, count in status.items():
                st.write(f"  • {source}: {count} jobs")
            
            if jobs:
                for job in jobs[:20]:  # Show top 20
                    with st.expander(f"🏢 {job['company']} — {job['title']}"):
                        st.write(f"**Location:** {job['location']}")
                        st.write(f"**Source:** {job['source']}")
                        if job['url']:
                            st.write(f"**Link:** {job['url']}")
                        if job.get('description'):
                            st.write(f"**Preview:** {job['description'][:300]}...")
                        
                        col1, col2 = st.columns(2)
                        # Use unique keys based on job URL or index
                        job_key = job.get('url', '') or job['title']
                        if col1.button("✅ Mark as Applied", key=f"apply_{hash(job_key)}"):
                            st.info("➡️ Go to Application Tracker to log this application")
    
    with tab2:
        st.subheader("Wellfound (Manual — Don't Automate)")
        st.write("Open these links and apply manually on Wellfound:")
        for url in scrape_wellfound_search_hint():
            st.markdown(f"  🔗 [{url}]({url})")
        
        st.markdown("---")
        
        st.subheader("LinkedIn (Manual — Don't Automate)")
        st.write("Open these links and use Easy Apply:")
        for item in scrape_linkedin_search_urls():
            st.markdown(f"  🔗 **{item['query']}**: [{item['url'][:80]}...]({item['url']})")
        
        st.markdown("---")
        
        st.subheader("Other Manual Sources")
        st.markdown("""
        - 🔗 [YC Work at a Startup](https://www.workatastartup.com/jobs?query=ai+ml&demographic=any&role=eng&sortBy=created_desc)
        - 🔗 [r/developersIndia Hiring Thread](https://www.reddit.com/r/developersIndia/search/?q=who%27s+hiring&sort=new)
        - 🔗 [Internshala AI/ML](https://internshala.com/internships/artificial-intelligence-internship/)
        - 🔗 [Instahyre](https://www.instahyre.com/search-jobs/?designation=ai-ml-engineer)
        - 🔗 [Cutshort](https://cutshort.io/jobs?q=ai+ml)
        """)
    
    with tab3:
        st.subheader("📥 Saved Scraped Jobs")
        saved = get_scraped_jobs()
        if len(saved) > 0:
            for _, job in saved.iterrows():
                with st.expander(f"{job['company']} — {job['title']} ({job['source']})"):
                    st.write(f"**Location:** {job['location']}")
                    if job['url']:
                        st.write(f"**Link:** {job['url']}")
                    if job.get('description'):
                        st.write(job['description'][:300])
                    
                    col1, col2 = st.columns(2)
                    if col1.button("❌ Dismiss", key=f"dismiss_{job['id']}"):
                        mark_scraped_job(job['id'], 'dismissed')
                        st.rerun()
                    if col2.button("✅ Applied", key=f"applied_{job['id']}"):
                        mark_scraped_job(job['id'], 'applied')
                        st.rerun()
        else:
            st.info("No saved jobs yet. Run the scraper first!")

# ===================== WATCHLIST =====================
elif page == "🏢 Watchlist":
    st.title("🏢 Company Watchlist")
    st.caption("Monitor target company career pages for new AI/ML listings via Lever, Greenhouse, Ashby, and Workable APIs.")

    tab1, tab2 = st.tabs(["Manage Watchlist", "New Listings"])

    with tab1:
        col_add, col_actions = st.columns([2, 1])

        with col_add:
            st.subheader("Add Company")
            wl_name = st.text_input("Company Name", key="wl_name")
            wl_platform = st.selectbox("Platform", ["lever", "greenhouse", "ashby", "workable", "custom"])
            wl_slug = st.text_input("Company Slug (from their careers URL)", key="wl_slug",
                                    placeholder="e.g. razorpay, freshworks")
            wl_url = st.text_input("Career Page URL (for custom)", key="wl_url",
                                   placeholder="https://company.com/careers")

            if st.button("Add to Watchlist"):
                if wl_name and (wl_slug or wl_url):
                    url = wl_url or f"https://api.lever.co/v0/postings/{wl_slug}"
                    add_to_watchlist(wl_name, url, wl_platform, wl_slug)
                    st.success(f"Added {wl_name} to watchlist!")
                    st.rerun()
                else:
                    st.error("Enter company name and either a slug or URL.")

        with col_actions:
            st.subheader("Quick Actions")
            if st.button("Load Starter List (10 companies)", type="primary"):
                load_starter_list()
                st.success(f"Loaded {len(STARTER_COMPANIES)} starter companies!")
                st.rerun()

            if st.button("Check All Now"):
                with st.spinner("Checking all watchlist companies..."):
                    results = check_all_watchlist()
                total_new = sum(len(v) for v in results.values())
                st.success(f"Found {total_new} new listings from {len(results)} companies!")
                st.rerun()

        st.markdown("---")
        st.subheader("Current Watchlist")
        watchlist = get_watchlist()
        if not watchlist.empty:
            for _, company in watchlist.iterrows():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{company['company_name']}**")
                with col2:
                    st.caption(f"{company['platform_type']} | Last checked: {company['last_checked'] or 'Never'}")
                with col3:
                    if st.button("Remove", key=f"rm_wl_{company['id']}"):
                        remove_from_watchlist(company['id'])
                        st.rerun()
        else:
            st.info("Watchlist is empty. Add companies or load the starter list.")

    with tab2:
        st.subheader("New Listings")
        new_jobs = get_new_watchlist_jobs()
        if not new_jobs.empty:
            for _, job in new_jobs.iterrows():
                with st.expander(f"\U0001f195 {job['company_name']} \u2014 {job['job_title']}"):
                    st.write(f"[Apply here]({job['job_url']})")
                    col1, col2 = st.columns(2)
                    if col1.button("Mark Seen", key=f"seen_wl_{job['id']}"):
                        mark_watchlist_job_seen(job['id'])
                        st.rerun()
                    if col2.button("Go to Tracker", key=f"track_wl_{job['id']}"):
                        st.info("Go to Application Tracker to log this application")
        else:
            st.info("No new listings found. Click 'Check All Now' above to refresh.")

# ===================== MESSAGE GENERATOR =====================
elif page == "✍️ Message Generator":
    st.title("✍️ AI Message Generator")
    
    if not api_key:
        st.warning("⚠️ Enter your Groq API key in the sidebar to use this feature.")
        st.stop()
    
    client = Groq(api_key=api_key)
    
    msg_type = st.selectbox("What do you need?", [
        "Cold DM to Founder/Hiring Manager",
        "Follow-up Message",
        "Cover Letter",
        "Thank You (Post-Interview)"
    ])
    
    if msg_type == "Cold DM to Founder/Hiring Manager":
        st.subheader("🎯 Cold DM Generator")
        
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company Name")
            role = st.text_input("Role Title")
            platform = st.selectbox("Platform", ["LinkedIn", "Twitter/X", "Email", "Wellfound"])
        with col2:
            company_desc = st.text_area("What does the company do? (Be specific)", 
                                        placeholder="e.g., They build AI-powered customer support chatbots for e-commerce...")
            project_link = st.text_input("Your Project Link (optional)", 
                                         placeholder="https://your-project-demo.streamlit.app")
        
        if st.button("Generate Messages", type="primary"):
            if company and role and company_desc:
                with st.spinner("Crafting personalized messages..."):
                    result = generate_cold_dm(client, company, role, company_desc, 
                                             platform, "professional", project_link)
                st.markdown(result)
                st.markdown("---")
                st.caption("💡 Edit these before sending. Make them sound like YOU, not AI.")
            else:
                st.error("Fill in company name, role, and company description.")
    
    elif msg_type == "Follow-up Message":
        st.subheader("📩 Follow-up Generator")
        
        company = st.text_input("Company Name")
        role = st.text_input("Role Title")
        days = st.number_input("Days since you applied", min_value=1, value=7)
        platform = st.selectbox("Platform", ["LinkedIn", "Email", "Wellfound"])
        
        if st.button("Generate Follow-up", type="primary"):
            if company and role:
                with st.spinner("Generating..."):
                    result = generate_follow_up(client, company, role, days, platform)
                st.markdown(result)
            else:
                st.error("Fill in company and role.")
    
    elif msg_type == "Cover Letter":
        st.subheader("📝 Cover Letter Generator")
        
        company = st.text_input("Company Name")
        role = st.text_input("Role Title")
        jd = st.text_area("Paste the Job Description", height=200)
        company_info = st.text_input("Any additional info about the company (optional)")
        
        if st.button("Generate Cover Letter", type="primary"):
            if company and role and jd:
                with st.spinner("Writing cover letter..."):
                    result = generate_cover_letter(client, company, role, jd, company_info)
                st.markdown(result)
                st.markdown("---")
                st.caption("⚠️ IMPORTANT: Edit this before submitting. Generic AI-written cover letters are an instant rejection.")
            else:
                st.error("Fill in company, role, and job description.")
    
    elif msg_type == "Thank You (Post-Interview)":
        st.subheader("🙏 Thank You Message")
        
        company = st.text_input("Company Name")
        interviewer = st.text_input("Interviewer's Name")
        discussion = st.text_input("Key point you discussed in the interview", 
                                   placeholder="e.g., Their plans to integrate RAG into their product")
        
        if st.button("Generate Thank You", type="primary"):
            if company and interviewer:
                with st.spinner("Generating..."):
                    result = generate_thank_you(client, company, interviewer, discussion)
                st.markdown(result)

# ===================== RESUME TAILOR =====================
elif page == "📄 Resume Tailor":
    st.title("📄 Resume Tailor")
    st.caption("Paste a JD to get project ordering, skill reordering, tailored summaries, and gap analysis.")

    rt_title = st.text_input("Job Title", placeholder="e.g. AI Engineer", key="rt_title")
    rt_jd = st.text_area("Paste the Job Description", height=250, key="rt_jd")

    if st.button("Tailor My Resume", type="primary"):
        if rt_title and rt_jd:
            # --- Project Order ---
            st.subheader("1. Project Order")
            projects = suggest_project_order(rt_jd)
            for i, p in enumerate(projects, 1):
                match_str = f"({p['matches']} keyword matches)"
                if i == 1:
                    st.markdown(f"**Lead with \u2192 {p['project']}** {match_str}")
                else:
                    st.write(f"{i}. {p['project']} {match_str}")
                if p["matched_keywords"]:
                    st.caption(f"   Matched: {', '.join(p['matched_keywords'])}")

            st.markdown("---")

            # --- Skills Reorder ---
            st.subheader("2. Suggested Skills Line")
            reordered = suggest_skill_order(rt_jd)
            st.code(", ".join(reordered), language=None)
            st.caption("Copy this into your resume's skills section — JD-relevant skills are first.")

            st.markdown("---")

            # --- Gap Analysis ---
            st.subheader("3. Gap Analysis")
            gaps = analyze_gaps(rt_jd)
            if gaps:
                for g in gaps:
                    st.write(f"{g['emoji']} **{g['skill']}** — {g['note']}")
            else:
                st.success("No significant skill gaps found!")

            st.markdown("---")

            # --- Tailored Summary Lines (needs API) ---
            st.subheader("4. Tailored Summary Lines")
            if api_key:
                client = Groq(api_key=api_key)
                with st.spinner("Generating tailored summaries..."):
                    summaries = generate_summary_lines(client, rt_title, rt_jd)
                st.markdown(summaries)
                st.caption("Pick one and replace your current resume headline.")
            else:
                st.info("Enter your Groq API key in the sidebar to generate AI-powered summary lines.")
        else:
            st.error("Enter both a job title and the job description.")

# ===================== APPLICATION TRACKER =====================
elif page == "📋 Application Tracker":
    st.title("📋 Application Tracker")
    
    tab1, tab2 = st.tabs(["➕ Add Application", "📊 View All"])
    
    with tab1:
        st.subheader("Log New Application")
        
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company")
            role = st.text_input("Role Title")
            job_type = st.selectbox("Type", ["Internship", "Job"])
            platform = st.selectbox("Applied via", [
                "Wellfound", "LinkedIn", "YC Startups", "Instahyre", 
                "Cutshort", "Internshala", "Direct/Career Page", 
                "Cold DM", "Referral", "Reddit", "Other"
            ])
        with col2:
            url = st.text_input("Job URL (optional)")
            noc = st.selectbox("NOC Compatible?", ["✅ Yes", "⚠️ Maybe", "❌ No", "Unknown"])
            conversion = st.selectbox("Conversion Potential", [
                "N/A (Full-time job)", "PPO mentioned", "Likely", 
                "Possible", "Unlikely", "Unknown"
            ])
            salary = st.text_input("Salary/Stipend (optional)")
        
        notes = st.text_area("Notes (optional)", placeholder="e.g., Founder replied on Twitter, interview next week")
        
        if st.button("Log Application", type="primary"):
            if company and role:
                add_application(company, role, job_type, platform, url,
                              noc, conversion, salary, notes)
                st.success(f"✅ Logged: {company} — {role} ({job_type})")
                st.balloons()
            else:
                st.error("Company and Role are required.")
    
    with tab2:
        st.subheader("All Applications")
        
        apps = get_all_applications()
        
        if len(apps) > 0:
            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_status = st.selectbox("Filter by Status", 
                    ["All", "Applied", "Follow-up Sent", "Interview Scheduled", 
                     "Interviewed", "Offer", "Rejected"])
            with col2:
                filter_type = st.selectbox("Filter by Type", ["All", "Job", "Internship"])
            with col3:
                filter_platform = st.selectbox("Filter by Platform", 
                    ["All"] + list(apps['platform'].unique()))
            
            filtered = apps.copy()
            if filter_status != "All":
                filtered = filtered[filtered['status'] == filter_status]
            if filter_type != "All":
                filtered = filtered[filtered['type'] == filter_type]
            if filter_platform != "All":
                filtered = filtered[filtered['platform'] == filter_platform]
            
            st.write(f"Showing {len(filtered)} applications")
            
            for _, row in filtered.iterrows():
                status_emoji = {
                    "Applied": "📨", "Follow-up Sent": "📩", 
                    "Interview Scheduled": "📅", "Interviewed": "🤝",
                    "Offer": "🎉", "Rejected": "❌"
                }.get(row['status'], "📨")
                
                type_emoji = "🏢" if row['type'] == "Job" else "🎓"
                
                with st.expander(f"{status_emoji} {type_emoji} {row['company']} — {row['role']} | {row['status']}"):
                    col1, col2, col3 = st.columns(3)
                    col1.write(f"**Platform:** {row['platform']}")
                    col2.write(f"**Applied:** {row['date_applied']}")
                    col3.write(f"**Follow-up:** {row['follow_up_date']}")
                    
                    if row['url']:
                        st.write(f"**URL:** {row['url']}")
                    st.write(f"**NOC:** {row['noc_compatible']} | **Conversion:** {row['conversion_potential']}")
                    if row['notes']:
                        st.write(f"**Notes:** {row['notes']}")
                    
                    # Update status
                    new_status = st.selectbox(
                        "Update Status", 
                        ["Applied", "Follow-up Sent", "Interview Scheduled", 
                         "Interviewed", "Offer", "Rejected"],
                        key=f"status_{row['id']}",
                        index=["Applied", "Follow-up Sent", "Interview Scheduled", 
                               "Interviewed", "Offer", "Rejected"].index(row['status'])
                        if row['status'] in ["Applied", "Follow-up Sent", "Interview Scheduled", 
                                             "Interviewed", "Offer", "Rejected"] else 0
                    )
                    
                    col_a, col_b = st.columns(2)
                    if col_a.button("Update", key=f"update_{row['id']}"):
                        update_status(row['id'], new_status)
                        st.success("Updated!")
                        st.rerun()
                    if col_b.button("🗑️ Delete", key=f"del_{row['id']}"):
                        delete_application(row['id'])
                        st.rerun()
        else:
            st.info("No applications logged yet. Start applying!")

# ===================== QUICK LINKS =====================
elif page == "🔗 Quick Links":
    st.title("🔗 Quick Links Hub")
    st.caption("All your job search bookmarks in one place. Open these during your 10 PM - 12 AM window.")
    
    st.subheader("Tier 1 — Apply Here First")
    st.markdown("""
    - 🚀 [Wellfound — AI/ML Jobs India](https://wellfound.com/jobs?q=ai&location=India)
    - 🚀 [YC Work at a Startup](https://www.workatastartup.com/jobs?query=ai+ml&demographic=any&role=eng)
    - 🚀 [r/developersIndia Hiring](https://www.reddit.com/r/developersIndia/search/?q=who%27s+hiring&sort=new)
    """)
    
    st.subheader("Tier 2 — Volume Play")
    st.markdown("""
    - 💼 [LinkedIn — Gen AI Developer India](https://www.linkedin.com/jobs/search/?keywords=gen%20ai%20developer&location=India&f_AL=true)
    - 💼 [LinkedIn — AI ML Intern India](https://www.linkedin.com/jobs/search/?keywords=ai%20ml%20intern&location=India&f_AL=true)
    - 💼 [Internshala — AI Internships](https://internshala.com/internships/artificial-intelligence-internship/)
    - 💼 [Instahyre](https://www.instahyre.com/search-jobs/?designation=ai-ml-engineer)
    - 💼 [Cutshort](https://cutshort.io/jobs?q=ai+ml)
    """)
    
    st.subheader("Tier 3 — Passive")
    st.markdown("""
    - 📡 [Naukri](https://www.naukri.com/ai-ml-jobs)
    - 📡 [Indeed India](https://in.indeed.com/jobs?q=gen+ai+developer)
    """)
    
    st.subheader("Startup Research")
    st.markdown("""
    - 🔬 [Inc42 — Funded Startups](https://inc42.com/tag/funding/)
    - 🔬 [YourStory — Startup News](https://yourstory.com/category/funding)
    - 🔬 [Tracxn — AI Startups India](https://tracxn.com/)
    """)
    
    st.markdown("---")
    st.subheader("Your Assets (Keep Updated)")
    st.markdown("""
    - 📄 Resume (ATS-friendly, one page)
    - 🌐 Portfolio website
    - 💻 GitHub (pinned projects, green graph)
    - 🔗 LinkedIn (headline: M.Tech AI | Gen AI Developer | Published Researcher)
    """)
