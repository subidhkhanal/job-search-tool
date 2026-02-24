import hmac
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from groq import Groq
from streamlit_option_menu import option_menu

from tracker import (
    init_db, add_application, update_status, get_all_applications,
    get_follow_ups_due, get_stats,
    delete_application,
    get_weekly_trend, get_platform_effectiveness,
    get_status_funnel, get_role_analysis,
    add_referral, update_referral_status, get_referral_follow_ups_due,
    get_referral_stats, get_referrals_by_company,
    add_mini_demo, update_mini_demo, get_active_demos, get_demo_results,
    get_cached_research, save_research_cache,
)
from scraper import (
    run_all_scrapers, scrape_wellfound_search_hint,
    scrape_linkedin_search_urls, generate_career_url
)
from message_generator import (
    generate_cold_dm, generate_follow_up, generate_cover_letter,
    generate_thank_you, generate_referral_request, generate_demo_outreach
)
from resume_tailor import (
    suggest_project_order, suggest_skill_order,
    analyze_gaps, generate_summary_lines
)
from jd_analyzer import full_analyze, ats_check, quick_ats, _get_default_resume_text
from nightly import score_job, llm_rerank_jobs

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

# --- Top Navbar ---
page = option_menu(
    menu_title=None,
    options=[
        "Dashboard", "Tonight's Plan", "JD Analyzer",
        "Messages", "Resume Tailor", "Tracker", "Referral Network", "Quick Links",
    ],
    icons=[
        "bar-chart-fill", "bullseye", "search",
        "pencil-square", "file-earmark-text", "clipboard-check", "people-fill", "link-45deg",
    ],
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {"padding": "0!important", "background-color": "#0E1117"},
        "icon": {"font-size": "14px"},
        "nav-link": {
            "font-size": "13px",
            "text-align": "center",
            "margin": "0px",
            "padding": "8px 10px",
            "--hover-color": "#262730",
        },
        "nav-link-selected": {"background-color": "#4A90D9"},
    },
)

# Load Groq API key from secrets / environment
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    import os
    api_key = os.environ.get("GROQ_API_KEY", "")

st.caption("**Immigration Filter** — Before applying, verify: "
           "Paid 30+ hrs/week | NOC-compatible title | Experience letter possible | Conversion potential")

# ===================== DASHBOARD =====================
if page == "Dashboard":
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
        st.dataframe(role_df, width='stretch', hide_index=True)

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
elif page == "Tonight's Plan":
    st.title("🎯 Tonight's Battle Plan")
    st.caption("Run all scrapers, score jobs, and get your nightly action plan — right here.")

    if st.button("🚀 Generate Tonight's Plan", type="primary"):
        # --- Run scrapers ---
        with st.spinner("Scraping all sources..."):
            jobs, sources_status, sources_errors = run_all_scrapers()

        # --- Scrape Summary ---
        summary_rows = []
        for source, count in sources_status.items():
            if source in sources_errors:
                status = "❌ FAILED"
            elif count == 0:
                status = "⚠️ EMPTY"
            else:
                status = "✅ OK"
            summary_rows.append({"Source": source, "Jobs Found": count, "Status": status})

        # --- Score jobs ---
        for job in jobs:
            job["score"] = score_job(job)
        jobs = [j for j in jobs if j["score"] > -100]
        jobs.sort(key=lambda j: j["score"], reverse=True)

        # --- LLM re-ranking ---
        with st.spinner("Running LLM re-ranking on top candidates..."):
            jobs = llm_rerank_jobs(jobs, top_n=20)

        # --- Filter low-relevance jobs ---
        jobs = [j for j in jobs if j.get("score", 0) >= 20]

        # --- Build jobs table rows ---
        table_rows = []
        for j in jobs[:20]:
            score = j.get("score", 0)
            llm_reason = j.get("llm_reason", "") or "—"
            text = (j.get("location", "") + " " + j.get("description", "") + " " + j.get("title", "")).lower()
            if any(kw in text for kw in ["onsite", "on-site", "on site", "in-office", "in office", "work from office", "wfo"]):
                work_mode = "🏢 Onsite"
            elif "hybrid" in text:
                work_mode = "🔀 Hybrid"
            elif "remote" in text:
                work_mode = "🏠 Remote"
            else:
                work_mode = "—"
            table_rows.append({
                "Mode": work_mode,
                "Company": j.get("company", "Unknown"),
                "Title": j.get("title", "Untitled")[:60],
                "Score": score,
                "LLM Take": llm_reason[:40],
                "URL": j.get("url", ""),
                "Career Page": generate_career_url(j.get("company", ""), j.get("title", "")),
                "Source": j.get("source", "Other"),
            })

        # --- Build cold DM targets ---
        cold_dm_targets = [
            {"company": j["company"], "title": j["title"], "score": j.get("score", 0)}
            for j in jobs[:5] if j.get("score", 0) >= 30
        ][:3]

        # --- Follow-ups ---
        try:
            follow_ups = get_follow_ups_due()
            follow_up_list = [
                {"company": fu["company"], "role": fu["role"], "platform": fu.get("platform", "")}
                for _, fu in follow_ups.iterrows()
            ] if not follow_ups.empty else []
        except Exception:
            follow_up_list = []

        # --- Manual links ---
        wf_urls = scrape_wellfound_search_hint()
        li_urls = scrape_linkedin_search_urls()

        # --- Store everything in session state ---
        st.session_state["plan"] = {
            "summary_rows": summary_rows,
            "sources_errors": dict(sources_errors) if sources_errors else {},
            "jobs_count": len(jobs),
            "high_rel": sum(1 for j in jobs if j.get("score", 0) >= 40),
            "table_rows": table_rows,
            "follow_ups": follow_up_list,
            "cold_dm_targets": cold_dm_targets,
            "wf_urls": wf_urls,
            "li_urls": li_urls,
            "generated_at": datetime.now().strftime('%I:%M %p on %A, %B %d, %Y'),
        }

    # --- Render from session state ---
    if "plan" in st.session_state:
        plan = st.session_state["plan"]

        st.subheader("📡 Scrape Summary")
        st.dataframe(pd.DataFrame(plan["summary_rows"]), width='stretch', hide_index=True)

        if plan["sources_errors"]:
            for src, err in plan["sources_errors"].items():
                st.error(f"{src}: {err[:100]}")

        st.markdown(f"**Total: {plan['jobs_count']}** | **High relevance: {plan['high_rel']}**")
        st.markdown("---")

        # Phase 1: Follow-ups
        st.subheader("⏰ Phase 1: Follow-ups")
        if plan["follow_ups"]:
            for fu in plan["follow_ups"]:
                st.warning(f"📩 Follow up: **{fu['company']}** — {fu['role']} ({fu['platform']})")
        else:
            st.success("No follow-ups due tonight. ✅")

        # Phase 2: Top Jobs
        st.markdown("---")
        st.subheader(f"🔍 Phase 2: Top Jobs ({plan['jobs_count']} found)")
        if plan["table_rows"]:
            # Track which jobs have been logged this session
            if "logged_jobs" not in st.session_state:
                st.session_state["logged_jobs"] = set()

            for idx, row in enumerate(plan["table_rows"]):
                col_info, col_score, col_links, col_log = st.columns([4, 1, 2, 1])
                with col_info:
                    st.markdown(f"**{row['Company']}** — {row['Title']}  {row['Mode']}")
                    if row["LLM Take"] != "—":
                        st.caption(row["LLM Take"])
                with col_score:
                    st.metric("Score", row["Score"], label_visibility="collapsed")
                with col_links:
                    link_parts = []
                    if row["URL"]:
                        link_parts.append(f"[Apply →]({row['URL']})")
                    if row["Career Page"]:
                        link_parts.append(f"[Career →]({row['Career Page']})")
                    st.markdown(" | ".join(link_parts) if link_parts else "—")
                with col_log:
                    job_key = f"{row['Company']}_{row['Title']}"
                    if job_key in st.session_state["logged_jobs"]:
                        st.success("✅", icon="✅")
                    elif st.button("📋 Log", key=f"log_job_{idx}"):
                        # Map scraper source to platform name
                        source_map = {
                            "hn": "YC Startups", "wellfound": "Wellfound",
                            "linkedin": "LinkedIn", "internshala": "Internshala",
                            "devsindia": "Reddit",
                        }
                        platform = source_map.get(row.get("Source", "").lower(), "Other")
                        add_application(
                            company=row["Company"],
                            role=row["Title"],
                            job_type="Internship",
                            platform=platform,
                            url=row.get("URL", ""),
                        )
                        st.session_state["logged_jobs"].add(job_key)
                        st.rerun()
                st.divider()
        else:
            st.info("No relevant jobs found tonight. Try the manual links below.")

        # Phase 3: Manual Links
        st.markdown("---")
        st.subheader("💼 Phase 3: Manual Platform Applications")
        col_wf, col_li = st.columns(2)
        with col_wf:
            st.markdown("**Wellfound (5-8 apps)**")
            for url in plan["wf_urls"]:
                st.markdown(f"- [{url[:60]}...]({url})")
        with col_li:
            st.markdown("**LinkedIn Easy Apply (10-15 apps)**")
            for item in plan["li_urls"]:
                st.markdown(f"- [{item['query']}]({item['url']})")

        # Phase 4: Cold DMs
        if plan["cold_dm_targets"]:
            st.markdown("---")
            st.subheader("🎯 Phase 4: Cold DM Targets")
            for j in plan["cold_dm_targets"]:
                st.markdown(f"- **{j['company']}** — {j['title']} (Score: {j['score']})")

        st.markdown("---")
        st.caption(f"Generated at {plan['generated_at']}")

# ===================== JD ANALYZER =====================
elif page == "JD Analyzer":
    st.title("🔍 JD Analyzer")
    st.caption("Paste a job description to get NOC compatibility, skill match, red flags, ATS score, and verdict.")

    tab_full, tab_ats = st.tabs(["Full Analysis", "Quick ATS Check"])

    with tab_full:
        jd_title = st.text_input("Job Title", placeholder="e.g. AI Engineer", key="jd_title")
        jd_text = st.text_area("Paste the Full Job Description", height=300, key="jd_text")
        jd_company = st.text_input("Company Name (optional — for research)", key="jd_company")

        with st.expander("Custom Resume Text (optional — defaults to your profile)"):
            custom_resume = st.text_area(
                "Paste your resume text here, or leave blank to use the default",
                height=200, key="custom_resume",
            )

        if st.button("Analyze", type="primary", key="btn_full"):
            if jd_title and jd_text:
                result = full_analyze(jd_title, jd_text)
                resume = custom_resume.strip() if custom_resume.strip() else _get_default_resume_text()
                ats = ats_check(resume, jd_text)

                # Company research (if company name provided)
                company_intel = None
                if jd_company.strip():
                    try:
                        cached = get_cached_research(jd_company.strip())
                        if cached:
                            company_intel = cached
                        else:
                            from company_research import research_company
                            with st.spinner(f"Researching {jd_company}..."):
                                company_intel = research_company(jd_company.strip())
                            if company_intel:
                                save_research_cache(jd_company.strip(), company_intel)
                    except Exception as e:
                        st.caption(f"Company research unavailable: {e}")

                # Verdict banner
                st.markdown(f"### {result['verdict_label']}")
                st.caption(result["verdict_reason"])

                # Three metric columns
                col_ats, col_noc, col_skill = st.columns(3)
                with col_ats:
                    st.metric("ATS Score", f"{ats['ats_score']}%")
                with col_noc:
                    noc = result["noc"]
                    st.metric("NOC Code", noc["code"] if noc["code"] else "No match")
                with col_skill:
                    skills = result["skills"]
                    st.metric("Skill Match", f"{skills['match_percentage']}%",
                              delta=f"{len(skills['matched'])}/{skills['total_required']} skills")

                # Company intel (if available)
                if company_intel:
                    st.markdown("---")
                    st.subheader("Company Intel")
                    import json as _json
                    tech = company_intel.get("tech_signals", "")
                    if isinstance(tech, str):
                        try:
                            tech = _json.loads(tech)
                        except Exception:
                            tech = []
                    st.write(f"**Description:** {company_intel.get('description', 'N/A')}")
                    st.write(f"**Recent News:** {company_intel.get('recent_news', 'N/A')}")
                    if tech:
                        st.write(f"**Tech Signals:** {', '.join(tech)}")
                    contact_name = company_intel.get("hiring_contact_name", "")
                    contact_li = company_intel.get("hiring_contact_linkedin", "")
                    if contact_name:
                        st.write(f"**Decision Maker:** {contact_name} ({company_intel.get('hiring_contact_title', '')}) — {contact_li}")
                    if company_intel.get("product_url"):
                        st.write(f"**Website:** {company_intel['product_url']}")

                st.markdown("---")

                # NOC + Skill columns
                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("NOC Compatibility")
                    st.markdown(noc["message"])
                    if noc["matched_duties"]:
                        st.write("**Matched duties:**")
                        for d in noc["matched_duties"]:
                            st.write(f"  - {d}")

                with col2:
                    st.subheader("Skill Match")
                    if skills["matched"]:
                        st.write("**Skills you have:**")
                        st.success(", ".join(skills["matched"]))
                    if skills["gaps"]:
                        st.write("**Gaps:**")
                        st.error(", ".join(skills["gaps"]))

                # Red Flags
                st.markdown("---")
                st.subheader("Red Flags")
                if result["red_flags"]:
                    for flag in result["red_flags"]:
                        st.warning(f"**{flag['message']}** (triggered by: *{flag['trigger']}*)")
                else:
                    st.success("No red flags detected!")

                # ATS Compatibility
                st.markdown("---")
                st.subheader("ATS Compatibility")

                if ats["truncation_warning"]:
                    st.warning("JD appears short (< 600 chars). ATS score may be approximate.")

                score = ats["ats_score"]
                if score >= 75:
                    st.success(f"**ATS Score: {score}%** — Strong match. Your resume should pass most ATS filters.")
                elif score >= 50:
                    st.warning(f"**ATS Score: {score}%** — Moderate match. Consider adding missing keywords.")
                else:
                    st.error(f"**ATS Score: {score}%** — Weak match. Significant keyword gaps detected.")

                col_green, col_red = st.columns(2)
                with col_green:
                    st.write(f"**Found in resume ({len(ats['found'])}):**")
                    if ats["found"]:
                        st.success(", ".join(ats["found"]))
                with col_red:
                    st.write(f"**Missing from resume ({len(ats['missing'])}):**")
                    if ats["missing"]:
                        st.error(", ".join(ats["missing"]))

                if ats["suggestions"]:
                    st.markdown("---")
                    st.subheader("Suggestions")
                    for i, suggestion in enumerate(ats["suggestions"], 1):
                        st.write(f"{i}. {suggestion}")
            else:
                st.error("Enter both a job title and the job description.")

    with tab_ats:
        st.subheader("Quick ATS Check")
        st.caption("Just paste a JD to see your ATS compatibility score.")

        ats_jd = st.text_area("Paste Job Description", height=300, key="ats_jd")
        with st.expander("Custom Resume Text (optional)"):
            ats_resume = st.text_area("Paste your resume, or leave blank for default", height=200, key="ats_resume")

        if st.button("Check ATS Score", type="primary", key="btn_ats"):
            if ats_jd:
                resume = ats_resume.strip() if ats_resume.strip() else _get_default_resume_text()
                ats = ats_check(resume, ats_jd)

                st.metric("ATS Score", f"{ats['ats_score']}%")
                if ats["truncation_warning"]:
                    st.warning("JD appears short. Score may be approximate.")

                col_g, col_r = st.columns(2)
                with col_g:
                    if ats["found"]:
                        st.success(f"**Found ({len(ats['found'])}):** {', '.join(ats['found'])}")
                with col_r:
                    if ats["missing"]:
                        st.error(f"**Missing ({len(ats['missing'])}):** {', '.join(ats['missing'])}")

                if ats["suggestions"]:
                    for s in ats["suggestions"]:
                        st.caption(f"\u2014 {s}")
            else:
                st.error("Paste a job description first.")

# ===================== MESSAGE GENERATOR =====================
elif page == "Messages":
    st.title("✍️ AI Message Generator")

    if not api_key:
        st.warning("⚠️ Set GROQ_API_KEY in .streamlit/secrets.toml or environment to use this feature.")
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
elif page == "Resume Tailor":
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
                st.info("Set GROQ_API_KEY in .streamlit/secrets.toml or environment to generate AI-powered summary lines.")
        else:
            st.error("Enter both a job title and the job description.")

# ===================== APPLICATION TRACKER =====================
elif page == "Tracker":
    st.title("📋 Application Tracker")

    with st.expander("➕ Add New Application", expanded=False):
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

    st.markdown("---")
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

    # --- Mini Demos Section ---
    st.markdown("---")
    st.subheader("🛠️ Mini Demos")

    demo_tab1, demo_tab2, demo_tab3 = st.tabs(["Active Demos", "Add New Demo", "Results"])

    with demo_tab1:
        demos = get_active_demos()
        if len(demos) > 0:
            for _, demo in demos.iterrows():
                with st.expander(f"{demo['company']} — {demo['demo_idea'][:50]} | Status: {demo['status']}"):
                    new_status = st.selectbox(
                        "Status", ["Idea", "Building", "Deployed", "Sent to Company", "Got Response", "Got Interview"],
                        index=["Idea", "Building", "Deployed", "Sent to Company", "Got Response", "Got Interview"].index(demo["status"])
                        if demo["status"] in ["Idea", "Building", "Deployed", "Sent to Company", "Got Response", "Got Interview"] else 0,
                        key=f"demo_status_{demo['id']}",
                    )
                    gh_url = st.text_input("GitHub URL", value=demo.get("github_url", "") or "", key=f"demo_gh_{demo['id']}")
                    demo_url = st.text_input("Demo URL", value=demo.get("demo_url", "") or "", key=f"demo_url_{demo['id']}")
                    hours = st.number_input("Hours Spent", value=float(demo.get("hours_spent", 0) or 0), min_value=0.0, step=0.5, key=f"demo_hrs_{demo['id']}")
                    result_text = st.text_input("Result", value=demo.get("result", "") or "", key=f"demo_res_{demo['id']}")
                    if st.button("Update Demo", key=f"demo_upd_{demo['id']}"):
                        update_mini_demo(demo["id"], status=new_status, github_url=gh_url, demo_url=demo_url, hours_spent=hours, result=result_text)
                        st.success("Updated!")
                        st.rerun()
        else:
            st.info("No active demos. Add one below!")

    with demo_tab2:
        d_company = st.text_input("Company", key="demo_company")
        d_role = st.text_input("Role", key="demo_role")
        d_idea = st.text_area("Demo Idea", placeholder="e.g. RAG chatbot over their product docs", key="demo_idea")
        if st.button("Add Demo", type="primary", key="btn_add_demo"):
            if d_company and d_idea:
                add_mini_demo(d_company, d_role, d_idea)
                st.success(f"Added demo idea for {d_company}!")
            else:
                st.error("Company and demo idea are required.")

    with demo_tab3:
        all_demos = get_demo_results()
        if len(all_demos) > 0:
            display_cols = ["company", "demo_idea", "status", "hours_spent", "result"]
            available = [c for c in display_cols if c in all_demos.columns]
            st.dataframe(all_demos[available], width="stretch", hide_index=True)
        else:
            st.info("No demo data yet.")

# ===================== REFERRAL NETWORK =====================
elif page == "Referral Network":
    st.title("🤝 Referral Network")
    st.caption("One referral = 20 cold applications. Track your contacts and referral pipeline here.")

    # Top metrics
    ref_stats = get_referral_stats()
    ref_follow = get_referral_follow_ups_due()
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Contacts", ref_stats["total"])
    requested = ref_stats["by_status"].get("Referral Requested", 0)
    col2.metric("Referrals Requested", requested)
    given = ref_stats["by_status"].get("Referral Given", 0) + ref_stats["by_status"].get("Applied via Referral", 0)
    col3.metric("Referrals Received", given)
    col4.metric("Ref→Interview Rate", f"{ref_stats['referral_interview_rate']}%")
    col5.metric("Follow-ups Due", len(ref_follow))

    st.markdown("---")

    tab_add, tab_network, tab_followup = st.tabs(["Add Contact", "My Network", "Follow-ups Due"])

    with tab_add:
        st.subheader("Add New Contact")
        rc1, rc2 = st.columns(2)
        with rc1:
            ref_name = st.text_input("Contact Name", key="ref_name")
            ref_company = st.text_input("Company", key="ref_company")
            ref_role = st.text_input("Their Role", placeholder="e.g. SDE, CTO, HR", key="ref_role")
            ref_relationship = st.selectbox("Relationship", [
                "College alumni", "LinkedIn connection", "TFUG meetup",
                "Cold outreach", "Friend of friend", "Friend", "Conference", "Other"
            ], key="ref_rel")
        with rc2:
            ref_linkedin = st.text_input("LinkedIn URL", key="ref_li")
            ref_email = st.text_input("Email", key="ref_email")
            ref_notes = st.text_area("Notes", key="ref_notes")

        if st.button("Add Contact", type="primary", key="btn_add_ref"):
            if ref_name and ref_company:
                add_referral(ref_name, ref_company, ref_role, ref_relationship, ref_linkedin, ref_email, ref_notes)
                st.success(f"Added {ref_name} at {ref_company}!")
                st.balloons()
            else:
                st.error("Name and Company are required.")

    with tab_network:
        st.subheader("All Contacts")
        try:
            from tracker import _get_client
            db = _get_client()
            resp = db.table("referrals").select("*").order("created_at", desc=True).execute()
            all_refs = pd.DataFrame(resp.data)
        except Exception:
            all_refs = pd.DataFrame()

        if len(all_refs) > 0:
            # Filters
            fc1, fc2 = st.columns(2)
            with fc1:
                filter_ref_status = st.selectbox("Filter by Status", ["All"] + list(all_refs["status"].unique()), key="ref_filter_status")
            with fc2:
                filter_ref_company = st.selectbox("Filter by Company", ["All"] + list(all_refs["company"].unique()), key="ref_filter_company")

            filtered_refs = all_refs.copy()
            if filter_ref_status != "All":
                filtered_refs = filtered_refs[filtered_refs["status"] == filter_ref_status]
            if filter_ref_company != "All":
                filtered_refs = filtered_refs[filtered_refs["company"] == filter_ref_company]

            for _, ref in filtered_refs.iterrows():
                status_map = {
                    "Identified": "🔵", "Contacted": "📨", "Responded": "💬",
                    "Referral Requested": "🙏", "Referral Given": "🎁",
                    "Applied via Referral": "📋", "Interview": "📅", "Offer": "🎉",
                }
                emoji = status_map.get(ref["status"], "🔵")
                with st.expander(f"{emoji} {ref['contact_name']} — {ref['company']} ({ref['contact_role']}) | {ref['status']}"):
                    st.write(f"**Relationship:** {ref.get('relationship', '')}")
                    if ref.get("linkedin_url"):
                        st.write(f"**LinkedIn:** {ref['linkedin_url']}")
                    if ref.get("email"):
                        st.write(f"**Email:** {ref['email']}")
                    if ref.get("notes"):
                        st.write(f"**Notes:** {ref['notes']}")
                    st.write(f"**Last Contacted:** {ref.get('last_contacted', 'N/A')}")

                    new_ref_status = st.selectbox(
                        "Update Status",
                        ["Identified", "Contacted", "Responded", "Referral Requested",
                         "Referral Given", "Applied via Referral", "Interview", "Offer"],
                        index=["Identified", "Contacted", "Responded", "Referral Requested",
                               "Referral Given", "Applied via Referral", "Interview", "Offer"].index(ref["status"])
                        if ref["status"] in ["Identified", "Contacted", "Responded", "Referral Requested",
                                             "Referral Given", "Applied via Referral", "Interview", "Offer"] else 0,
                        key=f"ref_status_{ref['id']}",
                    )
                    if st.button("Update", key=f"ref_upd_{ref['id']}"):
                        update_referral_status(ref["id"], new_ref_status)
                        st.success("Updated!")
                        st.rerun()

                    # Generate referral request message
                    if ref["status"] in ("Responded", "Referral Requested") and api_key:
                        ref_role_input = st.text_input("Role you're applying for", key=f"ref_apply_role_{ref['id']}")
                        if st.button("Generate Referral Request", key=f"ref_gen_{ref['id']}"):
                            if ref_role_input:
                                client = Groq(api_key=api_key)
                                with st.spinner("Generating..."):
                                    msg = generate_referral_request(
                                        client, ref["contact_name"], ref["contact_role"],
                                        ref["company"], ref_role_input, ref.get("relationship", "")
                                    )
                                st.markdown(msg)
        else:
            st.info("No contacts yet. Add your first contact above!")

    with tab_followup:
        st.subheader("Follow-ups Due")
        if len(ref_follow) > 0:
            for _, fu in ref_follow.iterrows():
                st.warning(
                    f"📩 **{fu['contact_name']}** at {fu['company']} — "
                    f"Status: {fu['status']} — Last contacted: {fu.get('last_contacted', 'N/A')}"
                )
        else:
            st.success("No referral follow-ups due today!")

# ===================== QUICK LINKS =====================
elif page == "Quick Links":
    st.title("🔗 Quick Links Hub")
    st.caption("All your job search bookmarks in one place. Open these during your 10 PM - 12 AM window.")

    st.subheader("🏆 Tier 0 — Low Competition, High Quality (check FIRST)")
    st.markdown("""
    - 🔥 [HasJob by HasGeek](https://hasjob.co/?q=ai)
    - 🔥 [YC Work at a Startup (India)](https://www.workatastartup.com/jobs?location=India)
    - 🔥 [r/developersIndia Job Board](https://developersindia.in/job-board)
    - 🔥 [Hirect (chat with founders)](https://hirect.in/)
    - 🔥 [Cutshort](https://cutshort.io/jobs?q=ai+ml)
    - 🔥 [AI India Jobs Telegram](https://t.me/AiIndiaJobs)
    """)

    st.subheader("💬 Communities (networking, not just listings)")
    st.markdown("""
    - 🗣️ [DataTalks.Club Slack](https://datatalks.club/slack)
    - 🗣️ [MLOps Community Slack](https://go.mlops.community/slack)
    - 🗣️ [Hasgeek Events](https://hasgeek.com/)
    - 🗣️ TFUG meetups — search [Meetup.com](https://www.meetup.com/) for your city
    """)

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
    - 🔗 LinkedIn (headline: M.Tech AI | Gen AI Developer)
    """)
