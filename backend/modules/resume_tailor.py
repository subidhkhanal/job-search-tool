"""
Resume Tailor — suggests project ordering, skill reordering,
tailored summary lines, and gap analysis based on a job description.
Uses Groq LLM for summary generation only; everything else is local.
"""

PROJECTS = {
    "Agentic RAG Knowledge Base": {
        "keywords": [
            "rag", "langchain", "vector", "chromadb", "llm", "ai",
            "chatbot", "document", "search", "retrieval", "openai",
            "cohere", "fastapi", "agentic", "knowledge base", "nlp",
            "hybrid search", "embeddings",
        ],
        "one_liner": "Document Q&A with hybrid retrieval + query routing + RAGAS evaluation",
    },
    "PathToPR.ca": {
        "keywords": [
            "automation", "api", "pipeline", "scraping", "openai",
            "gemini", "social media", "content", "data ingestion",
            "publishing", "integration", "rest api", "etl",
        ],
        "one_liner": "Automated data pipeline with OpenAI/Gemini APIs + multi-platform publishing",
    },
    "BCT Engineering Notes": {
        "keywords": [
            "seo", "content", "growth", "analytics", "marketing",
            "blog", "traffic", "organic", "audience", "writing",
        ],
        "one_liner": "2.2M+ views blog with 904% YOY growth, $0 ad spend",
    },
}

RESUME_SKILLS = [
    "LangChain", "RAG Pipelines", "Agentic AI", "Hybrid Search",
    "RAGAS", "Python", "FastAPI", "REST APIs", "Web Scraping",
    "Automation Pipelines", "Next.js", "Tailwind CSS", "ChromaDB",
    "SQL", "Git", "OpenAI", "Cohere",
]

# Skills categorized by learnability for gap analysis
SKILL_DIFFICULTY = {
    "easy": [
        "docker", "tailwind", "css", "html", "pandas", "numpy",
        "streamlit", "gradio", "git", "github", "selenium",
    ],
    "medium": [
        "react", "typescript", "angular", "vue", "django", "flask",
        "postgresql", "mongodb", "redis", "graphql", "ci/cd",
        "tensorflow", "pytorch", "airflow",
    ],
    "hard": [
        "kubernetes", "aws", "gcp", "azure", "terraform", "kafka",
        "java", "go", "rust", "c++", "scala", "spark",
        "distributed systems", "microservices",
    ],
}


def suggest_project_order(jd_text):
    """Rank projects by keyword match count against the JD."""
    jd_lower = jd_text.lower()
    results = []

    for name, info in PROJECTS.items():
        matches = [kw for kw in info["keywords"] if kw in jd_lower]
        results.append({
            "project": name,
            "matches": len(matches),
            "matched_keywords": matches,
            "one_liner": info["one_liner"],
        })

    results.sort(key=lambda x: x["matches"], reverse=True)
    return results


def suggest_skill_order(jd_text):
    """Reorder resume skills so the most JD-relevant appear first."""
    jd_lower = jd_text.lower()

    relevant = []
    other = []

    for skill in RESUME_SKILLS:
        if skill.lower() in jd_lower:
            relevant.append(skill)
        else:
            other.append(skill)

    return relevant + other


def analyze_gaps(jd_text):
    """Find skills the JD wants that aren't on the resume."""
    from jd_analyzer import _extract_tech_keywords, ALL_MY_SKILLS

    jd_keywords = _extract_tech_keywords(jd_text)
    resume_lower = [s.lower() for s in RESUME_SKILLS]

    gaps = []
    for kw in jd_keywords:
        if kw not in resume_lower and kw not in ALL_MY_SKILLS:
            # Determine difficulty
            difficulty = "medium"
            for level, skills in SKILL_DIFFICULTY.items():
                if kw in skills:
                    difficulty = level
                    break

            if difficulty == "easy":
                emoji = "\U0001f7e1"
                note = "not on resume, but learnable quickly. Consider adding if you've used it"
            elif difficulty == "medium":
                emoji = "\U0001f7e1"
                note = "moderate learning curve. Worth picking up if multiple JDs ask for it"
            else:
                emoji = "\U0001f534"
                note = "significant gap, don't fake it. Acknowledge in interview as area of growth"

            gaps.append({
                "skill": kw,
                "difficulty": difficulty,
                "emoji": emoji,
                "note": note,
            })

    return gaps


def generate_summary_lines(client, job_title, jd_text):
    """Use LLM to generate 3 tailored one-line resume summaries."""
    prompt = f"""Generate exactly 3 one-line resume summary options (each under 20 words)
tailored for this specific role.

JOB TITLE: {job_title}

JOB DESCRIPTION (key parts):
{jd_text[:1500]}

CANDIDATE BACKGROUND:
- AI Engineer Intern at PathToPR.ca — built automated data pipelines with OpenAI/Gemini APIs
- M.Tech AI from Amity University (graduating March 2026)
- Built Agentic RAG Knowledge Base with hybrid retrieval, LangChain, ChromaDB, FastAPI
- Built BCT Engineering Notes blog — 2.2M+ views, 904% YOY growth

RULES:
1. Each summary must be under 20 words
2. Tailor each to the specific role — use their language
3. Lead with the most relevant achievement
4. Do NOT start with "Aspiring" or "Passionate" — start with a concrete descriptor
5. Vary the angle: one technical, one results-focused, one role-specific

Format:
1. [summary]
2. [summary]
3. [summary]
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=200,
    )

    return response.choices[0].message.content
