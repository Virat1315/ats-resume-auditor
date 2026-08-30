import os
import json
import datetime
import urllib.request
import streamlit as st
from pypdf import PdfReader
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from google.genai.errors import APIError

# Load environment variables from .env if present
load_dotenv()

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Company-Specific ATS Auditor & Outreach Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="auto"
)

# ==========================================
# Custom Responsive Styling
# ==========================================
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        padding-left: 1.2rem;
        padding-right: 1.2rem;
        max-width: 1200px;
    }
    
    /* Header hero styling */
    .hero-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0284C7 100%);
        padding: 1.6rem 1.4rem;
        border-radius: 14px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 20px -4px rgba(2, 132, 199, 0.25);
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        font-size: 0.98rem;
        opacity: 0.92;
        margin-top: 0.4rem;
        margin-bottom: 0;
    }

    /* Score & Metrics Cards */
    .score-card {
        background: var(--background-color, #ffffff);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 14px;
        padding: 1.2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        margin-bottom: 1rem;
    }
    .score-number {
        font-size: 2.8rem;
        font-weight: 900;
        line-height: 1;
        margin: 0.4rem 0;
    }
    .score-high { color: #10B981; }
    .score-medium { color: #F59E0B; }
    .score-low { color: #EF4444; }

    /* Keyword Badges Container */
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.01em;
        line-height: 1.2;
    }
    .badge-matched {
        background-color: rgba(16, 185, 129, 0.15);
        color: #059669;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .badge-missing {
        background-color: rgba(239, 68, 68, 0.15);
        color: #DC2626;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }

    /* Verdict Box */
    .verdict-box {
        background-color: rgba(59, 130, 246, 0.08);
        border-left: 4px solid #0284C7;
        padding: 1rem 1.2rem;
        border-radius: 0 10px 10px 0;
        margin: 1rem 0;
        font-size: 0.95rem;
        line-height: 1.55;
    }

    /* Outreach / Email Box */
    .outreach-box {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }

    /* Suggestion Box */
    .suggestion-item {
        background: rgba(248, 250, 252, 0.8);
        border: 1px solid #e2e8f0;
        border-left: 4px solid #10B981;
        padding: 0.9rem 1.1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.8rem;
        font-size: 0.92rem;
        line-height: 1.5;
    }

    /* Red Flag Box */
    .red-flag-item {
        background: rgba(254, 242, 242, 0.8);
        border: 1px solid #fecaca;
        border-left: 4px solid #ef4444;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.6rem;
        font-size: 0.9rem;
        line-height: 1.45;
        color: #991b1b;
    }

    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .hero-title { font-size: 1.5rem; }
        .hero-subtitle { font-size: 0.9rem; }
        .score-number { font-size: 2.2rem; }
        .main .block-container {
            padding-left: 0.6rem;
            padding-right: 0.6rem;
            padding-top: 0.8rem;
        }
        .badge { font-size: 0.75rem; padding: 3px 7px; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# Default Master Sample Data (Virat Patel)
# ==========================================
DEFAULT_LATEX_RESUME = r"""%-------------------------------------------------------------------------------
% Virat Patel - Product Management Resume
% Built on the Jake Ryan resume template (github.com/jakegut/resume), MIT licence.
% Adapted to A4 and to a Product Management layout.
\documentclass[a4paper,11pt]{article}

\usepackage{latexsym}
\usepackage[empty]{fullpage}
\usepackage{titlesec}
\usepackage{marvosym}
\usepackage[usenames,dvipsnames]{color}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage[english]{babel}
\usepackage{tabularx}
\input{glyphtounicode}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\addtolength{\oddsidemargin}{-0.57in}
\addtolength{\evensidemargin}{-0.57in}
\addtolength{\textwidth}{1.13in}
\addtolength{\topmargin}{-0.60in}
\addtolength{\textheight}{1.21in}

\urlstyle{same}
\raggedbottom
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{2pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-3pt}]
\titlespacing*{\section}{0pt}{10pt}{5pt}

\pdfgentounicode=1

\newcommand{\resumeItem}[1]{\item\small{#1}}

\newcommand{\resumeSubheading}[4]{
  \vspace{-1pt}\item
    \begin{tabular*}{0.97\textwidth}[t]{l@{\extracolsep{\fill}}r}
      \textbf{#1} & #2 \\
      \textit{\small#3} & \textit{\small #4} \\
    \end{tabular*}\vspace{-5pt}
}

\newcommand{\resumeProjectHeading}[2]{
    \item
    \begin{tabular*}{0.97\textwidth}{l@{\extracolsep{\fill}}r}
      \small#1 & #2 \\
    \end{tabular*}\vspace{-2pt}
}

\renewcommand\labelitemii{$\vcenter{\hbox{\tiny$\bullet$}}$}

\newcommand{\resumeSubHeadingListStart}{\begin{itemize}[leftmargin=0.15in, label={}]}
\newcommand{\resumeSubHeadingListEnd}{\end{itemize}}
\newcommand{\resumeItemListStart}{%
  \begin{itemize}[leftmargin=0.17in, topsep=3pt, itemsep=2.5pt,
                  parsep=0pt, partopsep=0pt]}
\newcommand{\resumeItemListEnd}{\end{itemize}\vspace{-2pt}}

\begin{document}

%----------HEADING----------
\begin{center}
    \textbf{\Huge \scshape Virat Patel} \\ \vspace{3pt}
    {\large Product Management} \\ \vspace{4pt}
    \small
    +91 8319402171 $|$
    \href{mailto:devxvirat@gmail.com}{\underline{devxvirat@gmail.com}} $|$
    \href{https://www.linkedin.com/in/virat-patel-28ab48285/}{\underline{linkedin.com/in/virat-patel-28ab48285}} $|$
    \href{https://github.com/Virat1315}{\underline{github.com/Virat1315}}
\end{center}

%-----------EXPERIENCE-----------
\section{Experience}
  \resumeSubHeadingListStart

    \resumeSubheading
      {eComSuite}{Bangalore, Karnataka}
      {Product Intern}{Jun 2026 -- Aug 2026}
      \resumeItemListStart
        \resumeItem{Sellers had no LLM access to Amazon data, so shipped an \textbf{MCP-powered AI product} for it.}
        \resumeItem{Prioritized the \textbf{backlog} by testing \textbf{4 features} on \textbf{40+ customers}, shipping \textbf{5 validated fixes}.}
        \resumeItem{Wrote \textbf{20+ PRDs}, specs and acceptance criteria, cutting sprint rework via roadmap governance.}
      \resumeItemListEnd

    \resumeSubheading
      {Flick}{Raipur, Chhattisgarh}
      {Product Analyst Intern}{Feb 2026 -- Jun 2026}
      \resumeItemListStart
        \resumeItem{Onboarding drop-off capped growth, so fixing it \textbf{grew users 6,000 to 15,000+ (2.5x)}.}
        \resumeItem{Manual ops slowed the team, so AI automation workflows \textbf{cut that load 30\%} for 15,000+ users.}
        \resumeItem{Ran funnel and cohort analysis to prioritize the \textbf{growth roadmap} and weekly KPIs.}
      \resumeItemListEnd

    \resumeSubheading
      {Raipur Municipal Corporation}{Raipur, Chhattisgarh}
      {Product \& Software Development Intern}{Jun 2025 -- Jul 2025}
      \resumeItemListStart
        \resumeItem{Citizens lacked a fast query channel, so an \textbf{AI chatbot} absorbed \textbf{4,200+} of them.}
        \resumeItem{That deflected repeat queries from the front desk, freeing staff for high-value cases.}
        \resumeItem{Integrated REST APIs and automated manual workflows, keeping uptime steady at peak volume.}
      \resumeItemListEnd

  \resumeSubHeadingListEnd

%-----------EDUCATION-----------
\section{Education}
  \resumeSubHeadingListStart
    \resumeSubheading
      {International Institute of Information Technology, Naya Raipur}{Chhattisgarh, India}
      {B.Tech, Electronics and Communication Engineering}{Aug 2023 -- Jul 2027}
  \resumeSubHeadingListEnd

%-----------PROJECTS-----------
\section{Projects}
  \resumeSubHeadingListStart

    \resumeProjectHeading
      {\textbf{ConverseIQ: Enterprise AI Voice Platform} $|$ \emph{Python, FastAPI, LLMs}}
      {\href{https://converseiq.vercel.app/}{\underline{Live Demo}}}
      \resumeItemListStart
        \item[]\small\textit{Business outcome: \textbf{cuts recruiter screening time} so hiring teams reach top candidates faster.}\vspace{-1pt}
        \resumeItem{Automated first-round screening end to end, saving a recruiter's \textbf{20-minute call} per candidate.}
        \resumeItem{Chained \textbf{3 AI services} (speech-to-text, LLM, text-to-speech) into a live voice interview.}
        \resumeItem{Built an LLM scoring engine and analytics dashboard ranking \textbf{100\%} of candidate calls.}
      \resumeItemListEnd

    \resumeProjectHeading
      {\textbf{TechnoGate: Smart Event Ticketing Platform} $|$ \emph{FastAPI, SQL, QR}}
      {\href{https://technogate.vercel.app/}{\underline{Live Demo}}}
      \resumeItemListStart
        \item[]\small\textit{Business outcome: \textbf{replaced paper check-in}, cutting gate wait times at scale.}\vspace{-1pt}
        \resumeItem{Gate entry for \textbf{10,000+ attendees} ran on a QR ticketing platform built end to end.}
        \resumeItem{One-time QR validation eliminated duplicates across \textbf{10,000+} ticket scans at the gates.}
        \resumeItem{Gave \textbf{50+ organizers and volunteers} one dashboard for gates, passes and access control.}
      \resumeItemListEnd

    \resumeProjectHeading
      {\textbf{Apple AirDrop: Product Teardown} $|$ \emph{User Research, Prioritization, Metrics}}
      {\href{https://canva.link/t0usuvg59ckties}{\underline{Case Study}}}
      \resumeItemListStart
       \item[]\small\textit{Business outcome: \textbf{a prioritized fix roadmap} for improving AirDrop’s file transfer experience.}\vspace{-1pt}
        \resumeItem{Synthesized \textbf{100+ community posts} across \textbf{4 personas} into 5 ranked friction themes.}
        \resumeItem{Scored each issue on impact, frequency and whether it blocks the core send-a-file job.}
        \resumeItem{Proposed \textbf{5 fixes (P1 to P3)} with \textbf{6 success metrics}, incl. transfer completion rate.}
      \resumeItemListEnd

  \resumeSubHeadingListEnd

%-----------SKILLS-----------
\section{Skills}
 \begin{itemize}[leftmargin=0.15in, label={}]
    \small{\item{
     \textbf{Product}{: PRDs, Roadmap Governance, User Stories, Feature Prioritization} \\
     \textbf{Research}{: User Research, A/B Testing, Funnel Analysis, Cohort Analysis, Personas} \\
     \textbf{Analytics}{: SQL, Power BI, Mixpanel, Google Analytics, KPI Dashboards} \\
     \textbf{Technical}{: Python, FastAPI, REST APIs, LLM Integration, MCP, React, Node.js, Git, GCP} \\
     \textbf{Delivery}{: Jira, Figma, Notion, Agile \& Scrum, Sprint Planning, Stakeholder Management}
    }}
 \end{itemize}

%-----------ACHIEVEMENTS-----------
\section{Achievements}
  \resumeItemListStart
    \resumeItem{Research paper on HAM-1 and HAM-2 shortlisted for \textbf{TENCON 2026}, Bali (IEEE Region 10 Conference).}
    \resumeItem{\textbf{UG Representative (College President)}, IIIT Naya Raipur, representing the UG body in institute decisions.}
    \resumeItem{Led end-to-end execution of a student-run cultural fest of \textbf{10,000+ participants}, the largest in IIIT-NR's history.}
  \resumeItemListEnd

\end{document}
"""

DEFAULT_COMPANY_NAME = "Stripe"
DEFAULT_COMPANY_WEBSITE = "https://stripe.com"
GOOGLE_SHEET_TRACKER_URL = "https://docs.google.com/spreadsheets/d/1NoKDcOeBIveTgz-mIsE1t3T4_rAcf63uH2CcIImjRJI/edit?usp=sharing"

DEFAULT_PM_JD = """Role: Associate Product Manager (Platform & AI Integrations)
Company: Stripe
Website: https://stripe.com

About Stripe & The Role:
Stripe builds economic infrastructure for the internet. As an Associate Product Manager on our Platform & AI Integrations team, you will design developer-first APIs, build high-reliability payment workflows, and harness generative AI/LLMs to reduce integration friction for millions of global businesses.

What You'll Do:
- Write high-clarity Product Requirement Documents (PRDs) with rigorous technical depth, user journeys, and API contracts.
- Partner closely with engineering, data science, and design to define product roadmap, quarterly OKRs, and backlog priorities.
- Perform quantitative user research, SQL cohort analysis, funnel drop-off analytics, and latency telemetry.
- Evaluate developer experience (DX), API reliability, SDK integrations, and Model Context Protocol (MCP) integrations.
- Drive cross-functional alignment and champion operational excellence across global stakeholders.

Who You Are:
- Rigorous analytical thinker with a strong technical background (Computer Science, Engineering, or equivalent).
- Proven track record of user-centric product discovery, hypothesis testing, and data-driven prioritization.
- Experience with APIs, Python/FastAPI, SQL analytics, LLM workflows, and developer platforms.
- Clear, concise written communication and exceptional attention to detail.
"""

# ==========================================
# Pydantic Schema for Strict ATS Auditor & Outreach
# ==========================================
class CompanyATSReview(BaseModel):
    ats_score: int = Field(
        ..., 
        ge=0, 
        le=100, 
        description="Honest, realistic ATS score from 0 to 100 based strictly on the specific company's hiring bar and ATS parser."
    )
    score_tier: str = Field(
        ..., 
        description="'Top Tier / Ready for Interview' (85-100), 'Competitive with Minor Gaps' (70-84), 'Needs Optimization' (50-69), or 'High Risk / Unlikely to Pass ATS' (0-49)."
    )
    is_perfect_match: bool = Field(
        ..., 
        description="True if the resume is already a 100% comprehensive match requiring no additions; False otherwise."
    )
    summary_verdict: str = Field(
        ..., 
        description="Brutally honest, objective recruiter assessment. If perfect, clearly states 'No changes required' along with justification. Otherwise, gives exact reasons for the score."
    )
    company_culture_and_bar_fit: str = Field(
        ..., 
        description="Analysis of how well this resume aligns with this specific company's cultural values, scale expectations, and screening nuances."
    )
    matched_keywords: list[str] = Field(
        ..., 
        description="Keywords, hard skills, tools, and domain concepts present in the resume that match the JD and company expectations."
    )
    missing_or_gap_keywords: list[str] = Field(
        ..., 
        description="Crucial JD and company-specific keywords, tools, metrics, and frameworks missing or weakly represented in the resume."
    )
    suggested_additions_and_bullets: list[str] = Field(
        ..., 
        description="Exact, ready-to-copy bullet points, phrases, or metric enhancements specifically crafted for this company and JD for the candidate to add to their resume. Empty list if is_perfect_match is True."
    )
    company_specific_red_flags: list[str] = Field(
        ..., 
        description="Specific risks, weak signals, or missing criteria that would cause recruiters at THIS specific company to hesitate or reject."
    )
    final_action_checklist: list[str] = Field(
        ..., 
        description="Prioritized checklist of exact edits the candidate must make before applying to this company."
    )
    outreach_email_subject: str = Field(
        ..., 
        description="Punchy, personalized email subject line to the hiring manager or recruiter at this company."
    )
    outreach_email_body: str = Field(
        ..., 
        description="Concise, 1-minute readable outreach email (under 130 words) pitch highlighting 2 relevant candidate proof-points directly mapped to the company's problem space."
    )
    linkedin_connection_note: str = Field(
        ..., 
        description="Compelling LinkedIn connection invite note (strictly under 300 characters) referencing the company and shared domain interest."
    )
    linkedin_outreach_dm: str = Field(
        ..., 
        description="Short, high-conversion LinkedIn InMail / direct message pitch (under 90 words)."
    )

# ==========================================
# Helper Functions
# ==========================================
def extract_text_from_pdf(pdf_file) -> str:
    """Extract text from uploaded PDF using pypdf."""
    try:
        reader = PdfReader(pdf_file)
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text.strip())
        return "\n\n".join(text_parts).strip()
    except Exception as e:
        st.error(f"Error parsing PDF: {str(e)}")
        return ""

def extract_text_from_txt(txt_file) -> str:
    """Extract text from uploaded TXT or TEX file."""
    try:
        content = txt_file.read()
        if isinstance(content, bytes):
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                return content.decode("latin-1", errors="ignore")
        return str(content)
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return ""

def audit_and_generate_outreach(
    api_key: str,
    model_name: str,
    company_name: str,
    company_website: str,
    resume_text: str,
    jd_text: str,
    temperature: float = 0.1
) -> CompanyATSReview:
    """Perform a strict company ATS audit and generate tailored recruiter outreach copy."""
    client = genai.Client(api_key=api_key)

    prompt = f"""
You are an elite Talent Acquisition Leader and Executive Recruiter conducting a strict resume audit and crafting high-conversion outreach for {company_name} ({company_website}).

YOUR MANDATE:
1. Conduct an honest, rigorous ATS screening and recruiter evaluation of the provided CANDIDATE RESUME against the TARGET JOB DESCRIPTION OR LINKEDIN HIRING POST for {company_name}.
   - NOTE: The provided job text may be either a formal enterprise Job Description OR an informal LinkedIn hiring post / founder tweet / recruiter message. If an informal post or message is provided, intelligently parse and extract the core role expectations, required tech stack, implicit hiring bar, and domain challenges from it.
2. If the resume is genuinely exceptional and already covers 100% of the requirements with flawless metrics, state clearly "No changes required" and set is_perfect_match=true.
3. If there are gaps, provide an honest, uninflated ATS score (0-100), identify all missing keywords, and provide EXACT, ready-to-copy bullet points and phrases tailored specifically for {company_name}.
4. GENERATE HIGH-IMPACT OUTREACH:
   - outreach_email_subject: High open-rate subject line referencing {company_name} and the specific role/post.
   - outreach_email_body: Perfect, short, 1-minute readable email (under 130 words) directly connecting candidate's top metrics/projects to {company_name}'s product domain.
   - linkedin_connection_note: Personalized connection request (strictly under 300 characters).
   - linkedin_outreach_dm: Punchy InMail / DM (under 90 words).

COMPANY DETAILS:
- Target Company: {company_name}
- Company Website: {company_website}

---
### TARGET JOB DESCRIPTION OR LINKEDIN HIRING POST:
\"\"\"
{jd_text}
\"\"\"

---
### CANDIDATE RESUME:
\"\"\"
{resume_text}
\"\"\"
"""

    candidate_models = [model_name]
    fallback_pool = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-3.7-flash"]
    for m in fallback_pool:
        if m not in candidate_models:
            candidate_models.append(m)

    last_error = None
    for attempt_model in candidate_models:
        try:
            response = client.models.generate_content(
                model=attempt_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CompanyATSReview,
                    temperature=temperature,
                ),
            )
            raw_text = response.text
            parsed_json = json.loads(raw_text)
            return CompanyATSReview.model_validate(parsed_json)
        except Exception as e:
            last_error = e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate audit across candidate models.")

# ==========================================
# Sidebar Configuration
# ==========================================
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # API Key Handling (Hidden & Masked)
    env_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Gemini API Key",
        value="",
        type="password",
        placeholder="Enter API Key (or loaded from .env)",
        help="Enter your Google Gemini API Key. If left blank, GEMINI_API_KEY from .env is used automatically."
    )
    
    active_api_key = api_key_input.strip() if api_key_input.strip() else env_api_key.strip()
    
    if active_api_key:
        st.success("🔒 Gemini API Key Active")
    else:
        st.warning("⚠️ No API Key found. Add in sidebar or `.env`.")

    st.markdown("---")
    st.markdown("### 📊 Google Sheets Tracker Settings")
    st.caption("Connected Spreadsheet:")
    st.markdown(f"[🔗 Open Google Sheet Tracker]({GOOGLE_SHEET_TRACKER_URL})")
    
    sheets_webhook_url = st.text_input(
        "Google Apps Script Webhook URL (Optional)",
        value=os.getenv("GOOGLE_SHEETS_WEBHOOK_URL", ""),
        placeholder="https://script.google.com/macros/s/.../exec",
        help="Paste your Google Apps Script Webhook URL for instant 1-click automatic spreadsheet appending."
    )

    st.markdown("---")
    st.markdown("### 🧠 Model Settings")
    selected_model = st.selectbox(
        "Model",
        options=["gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite"],
        index=0
    )
    
    temperature = st.slider(
        "Auditor Strictness (Temp)",
        min_value=0.0,
        max_value=0.5,
        value=0.1,
        step=0.05
    )

# ==========================================
# Main App Header
# ==========================================
st.markdown("""
<div class="hero-header">
    <div class="hero-title">🎯 Company-Specific ATS Auditor & Outreach Engine</div>
    <div class="hero-subtitle">Strict ATS scoring, missing keyword detection, 1-minute recruiter email & LinkedIn pitch, with Google Sheets tracking.</div>
</div>
""", unsafe_allow_html=True)

# Quick reset / sample button
col_header_a, col_header_b = st.columns([3, 1])
with col_header_b:
    if st.button("✨ Load Stripe PM Sample", use_container_width=True, help="Populate with Stripe PM role & sample resume"):
        st.session_state["company_name_input"] = DEFAULT_COMPANY_NAME
        st.session_state["company_website_input"] = DEFAULT_COMPANY_WEBSITE
        st.session_state["resume_text_area"] = DEFAULT_LATEX_RESUME
        st.session_state["jd_text_area"] = DEFAULT_PM_JD
        st.rerun()

# ==========================================
# Target Company Inputs Row
# ==========================================
st.markdown("### 🏢 1. Target Company Profile")
col_comp1, col_comp2 = st.columns(2, gap="medium")

with col_comp1:
    company_name = st.text_input(
        "Target Company Name",
        value=st.session_state.get("company_name_input", DEFAULT_COMPANY_NAME),
        placeholder="e.g. Stripe, Google, Amazon, OpenAI...",
        key="company_name_input"
    )

with col_comp2:
    company_website = st.text_input(
        "Company Website / Careers URL",
        value=st.session_state.get("company_website_input", DEFAULT_COMPANY_WEBSITE),
        placeholder="e.g. https://stripe.com",
        key="company_website_input"
    )

st.markdown("---")

# ==========================================
# Resume & Job Description Inputs
# ==========================================
col_left, col_right = st.columns(2, gap="large")

with col_left:
    st.markdown("### 📄 2. Your Resume (LaTeX, PDF, or Plain Text)")
    uploaded_file = st.file_uploader(
        "Upload Resume File (PDF, TEX, or TXT)",
        type=["pdf", "tex", "txt"],
        help="Upload your resume in PDF, LaTeX, or text format."
    )
    
    extracted_text = ""
    if uploaded_file is not None:
        if uploaded_file.name.lower().endswith(".pdf"):
            with st.spinner("Extracting text from PDF..."):
                extracted_text = extract_text_from_pdf(uploaded_file)
        else:
            extracted_text = extract_text_from_txt(uploaded_file)
        
        if extracted_text:
            st.session_state["resume_text_area"] = extracted_text

    initial_resume = st.session_state.get("resume_text_area", DEFAULT_LATEX_RESUME)
    resume_input = st.text_area(
        "Resume Content",
        value=initial_resume,
        height=320,
        placeholder="Paste your resume content or LaTeX code here...",
        key="resume_text_area"
    )
    
    if resume_input:
        words = len(resume_input.split())
        chars = len(resume_input)
        st.caption(f"📊 Resume Stats: **{words} words** | {chars} characters")

with col_right:
    st.markdown("### 💼 3. Target Job Description or LinkedIn Hiring Post")
    initial_jd = st.session_state.get("jd_text_area", DEFAULT_PM_JD)
    jd_input = st.text_area(
        "Job Description / Post Content",
        value=initial_jd,
        height=390,
        placeholder="Paste a formal Job Description OR an informal LinkedIn 'We are hiring!' post text...",
        key="jd_text_area"
    )
    
    if jd_input:
        words = len(jd_input.split())
        chars = len(jd_input)
        st.caption(f"📊 JD Stats: **{words} words** | {chars} characters")

# ==========================================
# Action Button & Trigger
# ==========================================
st.markdown("---")
audit_btn = st.button(f"🚀 Audit Resume & Generate Outreach for {company_name or 'Target Company'}", type="primary", use_container_width=True)

if audit_btn:
    if not active_api_key:
        st.error("🔑 Please provide a Gemini API Key in the sidebar or set `GEMINI_API_KEY` in your `.env` file.")
    elif not company_name.strip():
        st.error("🏢 Please enter the target Company Name.")
    elif not resume_input.strip():
        st.error("📄 Please provide your resume content or upload a resume file.")
    elif not jd_input.strip():
        st.error("💼 Please paste the target Job Description.")
    else:
        with st.spinner(f"Auditing resume against {company_name}'s hiring bar and drafting outreach with {selected_model}..."):
            try:
                review: CompanyATSReview = audit_and_generate_outreach(
                    api_key=active_api_key,
                    model_name=selected_model,
                    company_name=company_name.strip(),
                    company_website=company_website.strip() if company_website.strip() else f"https://{company_name.lower().replace(' ', '')}.com",
                    resume_text=resume_input.strip(),
                    jd_text=jd_input.strip(),
                    temperature=temperature
                )
                st.session_state["audit_result"] = review
                st.session_state["audited_company"] = company_name.strip()
                st.session_state["audited_website"] = company_website.strip()
                st.toast(f"🎉 Audit & outreach for {company_name} completed!", icon="✅")
            except APIError as e:
                st.error(f"Gemini API Error: {str(e)}")
            except json.JSONDecodeError:
                st.error("Failed to decode structured response from Gemini. Please try again.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")

# ==========================================
# Results Display Section
# ==========================================
if "audit_result" in st.session_state:
    res: CompanyATSReview = st.session_state["audit_result"]
    aud_comp = st.session_state.get("audited_company", company_name)
    aud_web = st.session_state.get("audited_website", company_website)
    
    st.markdown(f"## 📊 ATS Audit & Outreach Suite for **{aud_comp}**")
    
    # 1. Top Metrics Row
    metric_col1, metric_col2, metric_col3 = st.columns([1.2, 1.4, 1.4], gap="medium")
    
    score = res.ats_score
    if score >= 85:
        score_class = "score-high"
    elif score >= 70:
        score_class = "score-medium"
    else:
        score_class = "score-low"
        
    with metric_col1:
        st.markdown(f"""
        <div class="score-card">
            <div style="font-size: 0.88rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.8;">{aud_comp} ATS Match</div>
            <div class="score-number {score_class}">{score}<span style="font-size: 1.4rem; font-weight: 500;">/100</span></div>
            <div style="font-weight: 600; font-size: 0.88rem;">{res.score_tier}</div>
        </div>
        """, unsafe_allow_html=True)
        st.progress(score / 100)

    with metric_col2:
        st.markdown(f"""
        <div class="score-card" style="text-align: left;">
            <div style="font-size: 0.88rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.8;">Matched Keywords</div>
            <div style="font-size: 2.1rem; font-weight: 800; color: #10B981; margin: 0.3rem 0;">{len(res.matched_keywords)} Satisfied</div>
            <div style="font-size: 0.82rem; opacity: 0.85;">Hard skills & competencies verified in resume.</div>
        </div>
        """, unsafe_allow_html=True)

    with metric_col3:
        st.markdown(f"""
        <div class="score-card" style="text-align: left;">
            <div style="font-size: 0.88rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.8;">Missing / Gap Keywords</div>
            <div style="font-size: 2.1rem; font-weight: 800; color: #EF4444; margin: 0.3rem 0;">{len(res.missing_or_gap_keywords)} Deficiencies</div>
            <div style="font-size: 0.82rem; opacity: 0.85;">High-value keywords required by {aud_comp}.</div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Perfect Match Banner or Executive Verdict
    if res.is_perfect_match:
        st.success("🏆 **PERFECT MATCH — No Changes Required!** Your resume satisfies all key requirements, scale metrics, and cultural pillars for this role.")
    
    st.markdown(f"""
    <div class="verdict-box">
        <strong>📋 Executive Recruiter Verdict for {aud_comp}:</strong><br/>
        {res.summary_verdict}
    </div>
    """, unsafe_allow_html=True)

    # 3. Main Result Tabs
    tab_outreach, tab_additions, tab_culture, tab_tracker = st.tabs([
        "📬 1-Min Outreach Email & LinkedIn",
        "✍️ Exact Resume Additions & Gaps",
        "🏢 Company Hiring Bar & Red Flags",
        "📊 Log to Google Sheets Tracker"
    ])

    # Tab 1: Outreach (Email & LinkedIn)
    with tab_outreach:
        st.markdown(f"### 📬 Tailored Recruiter Outreach for **{aud_comp}**")
        st.caption("Personalized, high-conversion copy referencing your verified skills and matching {aud_comp}'s product initiatives.")
        
        col_mail1, col_mail2 = st.columns(2, gap="medium")
        
        with col_mail1:
            st.markdown("#### ✉️ 1-Minute Recruiter Email")
            st.text_input("Subject Line", value=res.outreach_email_subject, key="email_subj")
            st.text_area("Email Body (1-Min Read)", value=res.outreach_email_body, height=220, key="email_body")
            
        with col_mail2:
            st.markdown("#### 💼 LinkedIn Outreach")
            st.text_area("LinkedIn Connection Note (Under 300 Chars)", value=res.linkedin_connection_note, height=90, key="li_note")
            st.caption(f"Length: {len(res.linkedin_connection_note)} / 300 characters")
            
            st.text_area("LinkedIn InMail / DM Pitch", value=res.linkedin_outreach_dm, height=130, key="li_dm")

    # Tab 2: Additions & Keyword Gaps
    with tab_additions:
        # Keywords
        kw_col1, kw_col2 = st.columns(2, gap="medium")
        with kw_col1:
            st.markdown(f"#### ✅ Matched Keywords ({len(res.matched_keywords)})")
            if res.matched_keywords:
                badges_html = "".join([f'<span class="badge badge-matched">✓ {kw}</span>' for kw in res.matched_keywords])
                st.markdown(f'<div class="badge-container">{badges_html}</div>', unsafe_allow_html=True)
            else:
                st.info("No significant keyword matches detected.")
                
        with kw_col2:
            st.markdown(f"#### ⚠️ Missing / Target Gap Keywords ({len(res.missing_or_gap_keywords)})")
            if res.missing_or_gap_keywords:
                badges_html = "".join([f'<span class="badge badge-missing">! {kw}</span>' for kw in res.missing_or_gap_keywords])
                st.markdown(f'<div class="badge-container">{badges_html}</div>', unsafe_allow_html=True)
            else:
                st.success("Zero missing critical keywords detected!")

        st.markdown("---")
        st.markdown(f"#### ✍️ Suggested Additions & Ready-to-Add Bullets for {aud_comp}")
        if res.suggested_additions_and_bullets:
            for idx, sug in enumerate(res.suggested_additions_and_bullets, 1):
                st.markdown(f"""
                <div class="suggestion-item">
                    <strong>Addition #{idx}:</strong><br/>
                    {sug}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No additional bullet points required.")

    # Tab 3: Culture & Red Flags
    with tab_culture:
        st.markdown(f"#### 🏢 How {aud_comp} Evaluates Candidates (Culture & Bar Fit)")
        st.markdown(res.company_culture_and_bar_fit)
        
        st.markdown("---")
        st.markdown(f"#### 🚩 Potential Red Flags & Hesitations for {aud_comp}")
        if res.company_specific_red_flags:
            for flag in res.company_specific_red_flags:
                st.markdown(f"""
                <div class="red-flag-item">
                    ⚠️ {flag}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No critical red flags detected.")

        st.markdown("---")
        st.markdown(f"#### ✅ Pre-Submission Action Checklist")
        for step in res.final_action_checklist:
            st.checkbox(step, value=False, key=f"chk_tab_{hash(step)}")

    # Tab 4: Google Sheets Tracker
    with tab_tracker:
        st.markdown("### 📊 Log Application to Google Sheets Tracker")
        st.markdown(f"Connected Spreadsheet: [**Open Google Sheet**]({GOOGLE_SHEET_TRACKER_URL})")
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Prepare structured log data
        tracker_row = {
            "Date": now_str,
            "Company": aud_comp,
            "Website": aud_web,
            "ATS Score": f"{res.ats_score}/100",
            "Tier": res.score_tier,
            "Matched Count": len(res.matched_keywords),
            "Gaps Count": len(res.missing_or_gap_keywords),
            "Status": "Audited / Ready to Apply",
            "Subject Line": res.outreach_email_subject
        }
        
        st.dataframe([tracker_row], use_container_width=True)
        
        col_track1, col_track2 = st.columns(2, gap="medium")
        
        with col_track1:
            if st.button("🚀 Push Row to Google Sheet via Webhook", use_container_width=True, type="primary"):
                if sheets_webhook_url.strip():
                    try:
                        req_payload = json.dumps(tracker_row).encode("utf-8")
                        req = urllib.request.Request(
                            sheets_webhook_url.strip(),
                            data=req_payload,
                            headers={"Content-Type": "application/json"}
                        )
                        with urllib.request.urlopen(req, timeout=8) as response:
                            st.success("🎉 Successfully appended row to your Google Sheet!")
                    except Exception as e:
                        st.error(f"Webhook error: {str(e)}")
                else:
                    st.warning("⚠️ No Webhook URL configured in the sidebar. See setup instructions below or use the 1-Click Copy Row.")

        with col_track2:
            tsv_row = f"{now_str}\t{aud_comp}\t{aud_web}\t{res.ats_score}/100\t{res.score_tier}\tReady to Apply\t{res.outreach_email_subject}"
            st.code(tsv_row, language="text")
            st.caption("📋 One-click copy: Select & paste directly into a new row in your Google Sheet!")

        with st.expander("🛠️ How to connect your Google Sheet for 1-Click Automatic Logging", expanded=False):
            st.markdown("""
            **Simple 2-Minute Google Apps Script Webhook Setup**:
            1. Open your [Google Spreadsheet](https://docs.google.com/spreadsheets/d/1NoKDcOeBIveTgz-mIsE1t3T4_rAcf63uH2CcIImjRJI/edit).
            2. Go to **Extensions** $\\rightarrow$ **Apps Script**.
            3. Paste the following script:
            ```javascript
            function doPost(e) {
              var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
              var data = JSON.parse(e.postData.contents);
              sheet.appendRow([
                data["Date"],
                data["Company"],
                data["Website"],
                data["ATS Score"],
                data["Tier"],
                data["Status"],
                data["Subject Line"]
              ]);
              return ContentService.createTextOutput("Success").setMimeType(ContentService.MimeType.TEXT);
            }
            ```
            4. Click **Deploy** $\\rightarrow$ **New Deployment** $\\rightarrow$ Select type **Web app**.
            5. Set *Execute as:* **Me**, and *Who has access:* **Anyone**.
            6. Copy the **Web App URL** and paste it into the **Google Apps Script Webhook URL** field in the sidebar!
            """)

    # 4. Download Full Report
    st.markdown("---")
    report_markdown = f"""# ATS Resume Audit & Outreach Report: {aud_comp}
**Date:** {datetime.datetime.now().strftime("%Y-%m-%d")}
**Company Website:** {aud_web}
**ATS Match Score:** {res.ats_score}/100 ({res.score_tier})

## Executive Recruiter Verdict
{res.summary_verdict}

## 1-Minute Recruiter Email
**Subject:** {res.outreach_email_subject}

{res.outreach_email_body}

## LinkedIn Outreach
**Connection Note (<300 chars):**
{res.linkedin_connection_note}

**InMail / DM Pitch:**
{res.linkedin_outreach_dm}

## Company Culture & Bar Alignment
{res.company_culture_and_bar_fit}

## Matched Keywords ({len(res.matched_keywords)})
{', '.join(res.matched_keywords)}

## Missing / Gap Keywords ({len(res.missing_or_gap_keywords)})
{', '.join(res.missing_or_gap_keywords)}

## Exact Suggested Additions for Resume
""" + "\n".join([f"- {sug}" for sug in res.suggested_additions_and_bullets]) + f"""

## Company-Specific Red Flags & Risks
""" + "\n".join([f"- {rf}" for rf in res.company_specific_red_flags]) + f"""

## Pre-Submission Action Checklist
""" + "\n".join([f"[ ] {step}" for step in res.final_action_checklist])

    st.download_button(
        label=f"📥 Download Full {aud_comp} Audit & Outreach Report (.md)",
        data=report_markdown,
        file_name=f"{aud_comp.lower().replace(' ', '_')}_audit_and_outreach.md",
        mime="text/markdown",
        use_container_width=True,
        type="primary"
    )

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; opacity: 0.7; font-size: 0.85rem; padding: 1rem 0;'>"
    "Company-Specific ATS Auditor & Outreach Engine | Mail, LinkedIn & Google Sheets Tracker"
    "</div>",
    unsafe_allow_html=True
)
