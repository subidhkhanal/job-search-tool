from groq import Groq

SUBIDH_PROFILE = """
- AI Engineer Intern at PathToPR.ca (Dec 2025 – Present): Built automated data ingestion pipeline, integrated OpenAI and Gemini APIs for content generation and summarization, automated multi-platform publishing (Facebook, Instagram, Telegram, X, Threads) — reduced manual content creation from hours to minutes
- M.Tech in Artificial Intelligence from Amity University Noida (graduating March 2026)
- Built Agentic RAG Knowledge Base: document Q&A system with hybrid retrieval (dense + BM25 via reciprocal rank fusion), query routing, RAGAS evaluation framework. Tech: Python, FastAPI, LangChain, ChromaDB, OpenAI, Cohere, Next.js
- Built BCT Engineering Notes: Nepal's most popular CS blog — 2.2M+ organic views, 87K monthly visitors, 904% YOY growth, $0 ad spend
- Tech stack: LangChain, RAG Pipelines, Agentic AI, Hybrid Search, RAGAS, Python, FastAPI, REST APIs, Web Scraping, Automation Pipelines, Next.js, Tailwind CSS, ChromaDB, SQL, Git
- Currently building Gen AI projects and actively looking for AI/ML roles (internship or full-time) in India
"""

def generate_cold_dm(client, company_name, role_title, company_description, 
                     platform="LinkedIn", tone="professional", project_link=""):
    """Generate a personalized cold DM for a specific company."""
    
    prompt = f"""You are helping a job seeker write a cold outreach message. 
    
ABOUT THE SENDER:
{SUBIDH_PROFILE}

TARGET:
- Company: {company_name}
- Role: {role_title}
- What the company does: {company_description}
- Platform: {platform}
- Project link to include: {project_link if project_link else "[will add project link]"}

RULES:
1. Keep it under 100 words for LinkedIn DMs, under 150 for email
2. Lead with something specific about THEIR company/product — show you've done research
3. Connect your experience to their specific needs
4. Include the project link naturally
5. End with a clear, low-commitment ask (quick chat, 15-min call)
6. Do NOT sound like ChatGPT — no "I hope this message finds you well", no "I'm reaching out because"
7. Tone: {tone}
8. Do NOT mention Canada, immigration, or PR goals
9. Lead with the PathToPR automation pipeline or the Agentic RAG project — these are more impressive for practical roles.
10. Be genuine and specific — generic messages get ignored
11. If the company uses LangChain, RAG, or vector databases, emphasize the Agentic RAG Knowledge Base project specifically — it directly demonstrates the skills they need.

Generate 2 variants:
VARIANT 1: Direct and confident
VARIANT 2: Curiosity-driven (lead with a question or observation about their product)

Format each as ready-to-copy text.
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=600
    )
    
    return response.choices[0].message.content

def generate_follow_up(client, company_name, role_title, days_since_applied, 
                       original_platform="LinkedIn"):
    """Generate a follow-up message after no response."""
    
    prompt = f"""Write a follow-up message for a job application.

CONTEXT:
- Applied to {company_name} for {role_title} role {days_since_applied} days ago
- No response yet
- Platform: {original_platform}

SENDER PROFILE:
{SUBIDH_PROFILE}

RULES:
1. Keep it under 60 words
2. Don't be apologetic or desperate
3. Add ONE new piece of value (a relevant insight, a new project update, or a specific idea for their product)
   The "new piece of value" should be one of these based on what's relevant to the company:
   - A specific feature of my Agentic RAG project that solves their problem
   - A metric from PathToPR (hours to minutes automation) or BCT Notes (2.2M views, 904% growth)
   - A brief insight about their product showing I've used it
   Do NOT repeat the same value-add from the original application.
4. Make it easy to respond to (yes/no question or simple ask)
5. No "just following up" or "circling back" — those are instant deletes

Generate 1 follow-up message, ready to copy.
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    
    return response.choices[0].message.content

def generate_cover_letter(client, company_name, role_title, job_description, 
                          company_info=""):
    """Generate a concise, non-generic cover letter."""
    
    prompt = f"""Write a cover letter for a job/internship application.

SENDER PROFILE:
{SUBIDH_PROFILE}

APPLICATION:
- Company: {company_name}
- Role: {role_title}
- Job Description: {job_description}
- Additional company info: {company_info}

RULES:
1. MAX 200 words — recruiters don't read long cover letters
2. Paragraph 1: Why THIS company specifically (not generic flattery)
3. Paragraph 2: Your most relevant qualification mapped to their needs
4. Paragraph 3: One sentence close with enthusiasm
5. Do NOT sound like AI generated it — no corporate buzzwords
6. Do NOT list all skills — pick the 2-3 most relevant ones from this priority order based on what the job needs:
   - If they need LLM/RAG: lead with Agentic RAG project
   - If they need automation/APIs: lead with PathToPR pipeline
   - If they need content/growth: lead with BCT Engineering Notes
7. Do NOT mention immigration plans

Generate the cover letter, ready to copy.
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=400
    )
    
    return response.choices[0].message.content

def generate_thank_you(client, company_name, interviewer_name, 
                       key_discussion_point=""):
    """Generate a post-interview thank you message."""
    
    prompt = f"""Write a thank-you email after a job interview.

CONTEXT:
- Company: {company_name}
- Interviewer: {interviewer_name}
- Key point discussed: {key_discussion_point}

RULES:
1. Under 80 words
2. Reference something specific from the conversation
3. Reaffirm interest without being needy
4. Professional but warm

Generate the thank-you message.
"""
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=200
    )

    return response.choices[0].message.content


def generate_referral_request(client, contact_name, contact_role, company,
                              role_applying_for, relationship):
    """Generate a referral request message tailored to the relationship type."""

    if relationship in ("College alumni", "Friend", "Friend of friend"):
        tone_instruction = "Warm, casual tone — you know this person. Use first name."
    else:
        tone_instruction = "Professional but not stiff. Respectful of their time."

    prompt = f"""Write a referral request message.

ABOUT YOU:
{SUBIDH_PROFILE}

TARGET CONTACT:
- Name: {contact_name}
- Their role: {contact_role} at {company}
- Your relationship: {relationship}

ROLE YOU WANT:
- Position: {role_applying_for} at {company}

RULES:
1. Under 80 words
2. {tone_instruction}
3. Mention something specific about WHY you want to work at {company}
4. Include a relevant project link (Agentic RAG or PathToPR)
5. End with a direct ask: "Would you be open to referring me for the {role_applying_for} position?"
6. Do NOT say "I know this is a big ask"
7. Do NOT mention immigration or PR goals

Generate 1 message, ready to copy.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=200,
    )

    return response.choices[0].message.content


def generate_demo_outreach(client, company, role, demo_url, demo_description,
                           company_desc):
    """Generate an outreach message that leads with a demo you built."""

    prompt = f"""Write an outreach message leading with a mini demo/prototype.

ABOUT YOU:
{SUBIDH_PROFILE}

CONTEXT:
- Company: {company}
- Role: {role}
- What company does: {company_desc}
- Demo you built: {demo_description}
- Demo URL: {demo_url}

RULES:
1. Open with 1 line about their company/product showing you've researched them
2. Next: "I built [specific thing] that [solves specific problem for them]"
3. Include the demo URL prominently
4. End with: "Happy to walk through the approach — would 15 minutes work?"
5. Under 120 words total
6. This is NOT a job application — it's a value-first introduction
7. Generate 2 variants: one for LinkedIn DM, one for email
8. Do NOT mention immigration or PR goals

Generate both variants.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=500,
    )

    return response.choices[0].message.content
