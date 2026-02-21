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

# --- Page Config ---
st.set_page_config(
    page_title="Subidh's Job Search HQ",
    page_icon="🎯",
    layout="wide"
)

# --- Init ---
init_db()

# --- Sidebar ---
st.sidebar.title("🎯 Job Search HQ")
page = st.sidebar.radio("Navigate", [
    "📊 Dashboard",
    "🔍 Job Scraper",
    "✍️ Message Generator",
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

# ===================== JOB SCRAPER =====================
elif page == "🔍 Job Scraper":
    st.title("🔍 Job Scraper")
    st.caption("Scrapes AI/ML jobs from free public APIs. LinkedIn and Wellfound links are for manual browsing (automation gets you banned).")
    
    tab1, tab2, tab3 = st.tabs(["🤖 Auto-Scrape", "🔗 Manual Search Links", "📥 Saved Jobs"])
    
    with tab1:
        if st.button("🚀 Scrape All Sources", type="primary"):
            with st.spinner("Scraping Remotive, HN Who's Hiring, Arbeitnow..."):
                jobs, status = run_all_scrapers()
            
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
