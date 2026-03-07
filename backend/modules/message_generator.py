from groq import Groq

# Default fallback — used when profile DB is unavailable
_DEFAULT_PROFILE = """
- AI Engineer Intern at PathToPR.ca (Dec 2025 – Present): Built automated data ingestion pipeline, integrated OpenAI and Gemini APIs for content generation and summarization, automated multi-platform publishing (Facebook, Instagram, Telegram, X, Threads) — reduced manual content creation from hours to minutes
- M.Tech in Artificial Intelligence from Amity University Noida (graduating March 2026)
- Built Agentic RAG Knowledge Base: document Q&A system with hybrid retrieval (dense + BM25 via reciprocal rank fusion), query routing, RAGAS evaluation framework. Tech: Python, FastAPI, LangChain, ChromaDB, OpenAI, Cohere, Next.js
- Built BCT Engineering Notes: Nepal's most popular CS blog — 2.2M+ organic views, 87K monthly visitors, 904% YOY growth, $0 ad spend
- Tech stack: LangChain, RAG Pipelines, Agentic AI, Hybrid Search, RAGAS, Python, FastAPI, REST APIs, Web Scraping, Automation Pipelines, Next.js, Tailwind CSS, ChromaDB, SQL, Git
- Currently building Gen AI projects and actively looking for AI/ML roles (internship or full-time) in India
"""


def _get_profile_text():
    """Try to load profile from DB, fall back to hardcoded default."""
    try:
        from profile import get_profile_text
        text = get_profile_text()
        if text:
            return text
    except Exception:
        pass
    return _DEFAULT_PROFILE


# Backward-compatible reference for other modules that import SUBIDH_PROFILE
SUBIDH_PROFILE = _DEFAULT_PROFILE

def generate_cold_dm(client, company_name, role_title, company_description,
                     platform="LinkedIn", tone="professional", project_link="",
                     profile_text=""):
    """Generate a personalized cold DM for a specific company."""
    sender_profile = profile_text or _get_profile_text()

    prompt = f"""You are helping a job seeker write a cold outreach message.

ABOUT THE SENDER:
{sender_profile}

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
                       original_platform="LinkedIn", profile_text="",
                       follow_up_number=1, previous_messages=None):
    """Generate a follow-up message after no response."""
    sender_profile = profile_text or _get_profile_text()

    # --- Escalating tone (softened #3 for entry-level) ---
    if follow_up_number >= 3:
        tone_directive = "Tone: respectful and final. This is the last follow-up. Keep it brief — acknowledge they may have gone another direction, and check one last time. No ultimatums or 'moving on' language. Just a clean, professional close."
    elif follow_up_number == 2:
        tone_directive = "Tone: confident with a brief value-add. Mention one specific skill or project that's relevant to the role as a secondary hook, but keep the follow-up framing dominant."
    else:
        tone_directive = "Tone: polite and professional check-in. Keep it simple — reference the application and ask about status. No value-add needed."

    # --- Platform-specific formatting ---
    if original_platform == "LinkedIn":
        platform_instructions = "FORMAT: One tight block of text, no greeting, no sign-off. Max 300 characters."
        char_limit = 300
        max_tok = 150
    elif original_platform == "Email":
        platform_instructions = "FORMAT: Include a short subject line on the first line prefixed with 'Subject: '. Can be 2-3 short paragraphs. Max 500 characters."
        char_limit = 500
        max_tok = 400
    elif original_platform == "Twitter":
        platform_instructions = "FORMAT: Ultra-short, one sentence. Max 280 characters."
        char_limit = 280
        max_tok = 150
    else:
        platform_instructions = "FORMAT: One tight block of text. Max 300 characters."
        char_limit = 300
        max_tok = 150

    system_msg = f"""You write ultra-short follow-up messages for job applications.
The sender has ALREADY applied — this is NOT a cold outreach or pitch.
{tone_directive}
{platform_instructions}"""

    # --- Conditional profile (only for #2) ---
    if follow_up_number == 2:
        profile_section = f"\nMY PROFILE (pick ONE relevant detail for a brief value-add):\n{sender_profile}\n"
    else:
        profile_section = ""

    # --- Previous follow-up history context ---
    history_section = ""
    if previous_messages and follow_up_number > 1:
        history_lines = []
        for i, msg in enumerate(previous_messages, 1):
            history_lines.append(f"- Follow-up #{i}: \"{msg}\"")
        history_section = "\nPREVIOUS FOLLOW-UPS I SENT (do NOT repeat these — build on them, reference them naturally):\n" + "\n".join(history_lines) + "\n"

    # --- One-shot example per follow-up number ---
    if follow_up_number >= 3:
        example = 'EXAMPLE (follow-up #3, 198 chars):\n"Reaching out one last time about the ML Engineer Intern role I applied for 3 weeks ago. Completely understand if the team went another direction — just wanted to check before closing the loop."'
    elif follow_up_number == 2:
        example = 'EXAMPLE (follow-up #2, 283 chars):\n"Applied for the ML Engineer Intern role 2 weeks ago. Since then I shipped a RAG pipeline with hybrid retrieval that might be relevant to your search stack. Would love to know if the role is still open — happy to share details."'
    else:
        example = 'EXAMPLE (follow-up #1, 247 chars):\n"Applied for the ML Engineer Intern role 8 days ago — wanted to check if the team has started reviewing applications. Happy to share anything else that would help. Thanks for your time."'

    prompt = f"""Write follow-up #{follow_up_number} for my existing job application.

CONTEXT:
- I applied to {company_name} for the {role_title} role {days_since_applied} days ago
- No response yet
- This is follow-up attempt #{follow_up_number} of 3
- Platform: {original_platform}
{profile_section}{history_section}
MESSAGE STRUCTURE (follow this order):
1. Reference the original application — mention the role and timeframe briefly
2. (Follow-up #2 only) One short clause of new value if it fits within the limit
3. Close with a simple ask about application status or next steps

RULES:
- This is a FOLLOW-UP, not a cold DM. Do NOT pitch yourself from scratch.
- Do NOT open with project descriptions or technical capabilities
- No cliches: "just following up", "circling back", "I hope this finds you well", "I wanted to reach out", "I'm reaching out", "I hope you're doing well", "I trust this message finds you", "I'd love to connect", "at your earliest convenience", "please don't hesitate", "I look forward to hearing from you", "touching base"
- No greetings like "Hi [Name]" — keep every character for content
- Do NOT mention Canada, immigration, or PR goals

{example}

Generate 1 follow-up message, ready to copy. Output ONLY the message text, nothing else.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
        max_tokens=max_tok
    )

    result = response.choices[0].message.content.strip()

    # --- Post-generation character enforcement ---
    if len(result) > char_limit:
        sentences = result.replace("? ", "?|").replace(". ", ".|").replace("! ", "!|").split("|")
        truncated = ""
        for s in sentences:
            if len(truncated + s) <= char_limit:
                truncated += s + " "
            else:
                break
        result = truncated.strip() or result[:char_limit]

    return result

def generate_cover_letter(client, company_name, role_title, job_description,
                          company_info="", profile_text=""):
    """Generate a concise, non-generic cover letter."""
    sender_profile = profile_text or _get_profile_text()

    prompt = f"""Write a cover letter for a job/internship application.

SENDER PROFILE:
{sender_profile}

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
                              role_applying_for, relationship, profile_text=""):
    """Generate a referral request message tailored to the relationship type."""
    sender_profile = profile_text or _get_profile_text()

    if relationship in ("College alumni", "Friend", "Friend of friend"):
        tone_instruction = "Warm, casual tone — you know this person. Use first name."
    else:
        tone_instruction = "Professional but not stiff. Respectful of their time."

    prompt = f"""Write a referral request message.

ABOUT YOU:
{sender_profile}

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
                           company_desc, profile_text=""):
    """Generate an outreach message that leads with a demo you built."""
    sender_profile = profile_text or _get_profile_text()

    prompt = f"""Write an outreach message leading with a mini demo/prototype.

ABOUT YOU:
{sender_profile}

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
