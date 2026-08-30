import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

app = FastAPI(title="Company-Specific ATS Resume Auditor & Outreach Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Schema
# ==========================================
class AuditRequest(BaseModel):
    company_name: str
    company_website: str = ""
    resume_text: str
    jd_text: str
    api_key: str = ""

class CompanyATSReview(BaseModel):
    ats_score: int = Field(..., ge=0, le=100)
    score_tier: str
    is_perfect_match: bool
    summary_verdict: str
    company_culture_and_bar_fit: str
    matched_keywords: list[str]
    missing_or_gap_keywords: list[str]
    suggested_additions_and_bullets: list[str]
    company_specific_red_flags: list[str]
    final_action_checklist: list[str]
    outreach_email_subject: str
    outreach_email_body: str
    linkedin_connection_note: str
    linkedin_outreach_dm: str

# ==========================================
# API Endpoint
# ==========================================
@app.post("/api/audit")
async def audit_endpoint(req: AuditRequest):
    api_key = req.api_key.strip() if req.api_key.strip() else os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")
        
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
You are an elite Talent Acquisition Leader and Executive Recruiter conducting a strict resume audit and crafting high-conversion outreach for {req.company_name} ({req.company_website}).

YOUR MANDATE:
1. Conduct an honest, rigorous ATS screening and recruiter evaluation of the provided CANDIDATE RESUME against the TARGET JOB DESCRIPTION OR LINKEDIN HIRING POST for {req.company_name}.
   - NOTE: The provided job text may be either a formal enterprise Job Description OR an informal LinkedIn hiring post / founder tweet / recruiter message. If an informal post or message is provided, intelligently parse and extract the core role expectations, required tech stack, implicit hiring bar, and domain challenges from it.
2. If the resume is genuinely exceptional and already covers 100% of the requirements with flawless metrics, state clearly "No changes required" and set is_perfect_match=true.
3. If there are gaps, provide an honest, uninflated ATS score (0-100), identify all missing keywords, and provide EXACT, ready-to-copy bullet points and phrases tailored specifically for {req.company_name}.
4. GENERATE HIGH-IMPACT OUTREACH:
   - outreach_email_subject: High open-rate subject line referencing {req.company_name} and the specific role/post.
   - outreach_email_body: Perfect, short, 1-minute readable email (under 130 words) directly connecting candidate's top metrics/projects to {req.company_name}'s product domain.
   - linkedin_connection_note: Personalized connection request (strictly under 300 characters).
   - linkedin_outreach_dm: Punchy InMail / DM (under 90 words).

COMPANY DETAILS:
- Target Company: {req.company_name}
- Company Website: {req.company_website}

---
### TARGET JOB DESCRIPTION OR LINKEDIN HIRING POST:
\"\"\"
{req.jd_text}
\"\"\"

---
### CANDIDATE RESUME:
\"\"\"
{req.resume_text}
\"\"\"
"""

    candidate_models = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash-lite", "gemini-3.7-flash"]
    last_error = None
    for m in candidate_models:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=CompanyATSReview,
                    temperature=0.1,
                ),
            )
            parsed_json = json.loads(response.text)
            return parsed_json
        except Exception as e:
            last_error = e
            continue

    raise HTTPException(status_code=500, detail=str(last_error) if last_error else "Failed to generate audit.")

# ==========================================
# Frontend HTML
# ==========================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Company-Specific ATS Resume Auditor & Outreach Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .score-gradient { background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0284C7 100%); }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <div class="max-w-6xl mx-auto px-4 py-8">
    
    <!-- Hero Header -->
    <div class="score-gradient text-white rounded-2xl p-6 md:p-8 shadow-xl mb-8">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 bg-white/10 rounded-full text-xs font-semibold uppercase tracking-wider mb-2">
            <span>🎯 ATS Auditor & Outreach Engine</span>
          </div>
          <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight">Company-Specific ATS Auditor & Outreach Engine</h1>
          <p class="text-slate-200 text-sm md:text-base mt-1">Strict ATS scoring, missing keyword gaps, 1-minute recruiter email & LinkedIn pitch, with Google Sheets tracking.</p>
        </div>
        <div>
          <button onclick="loadSample()" class="px-4 py-2 bg-white/15 hover:bg-white/25 text-white text-xs md:text-sm font-medium rounded-xl border border-white/20 transition-all flex items-center gap-1.5 shadow-sm">
            ✨ Load Stripe PM Sample
          </button>
        </div>
      </div>
    </div>

    <!-- Inputs Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
      <!-- Left Column -->
      <div class="space-y-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-4">
          <h2 class="font-bold text-slate-800 flex items-center gap-2">
            <span>🏢</span> 1. Target Company Profile
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">Company Name</label>
              <input id="companyName" type="text" value="Stripe" placeholder="e.g. Stripe, Google, Amazon" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm">
            </div>
            <div>
              <label class="block text-xs font-semibold text-slate-600 mb-1">Company Website</label>
              <input id="companyWebsite" type="text" value="https://stripe.com" placeholder="https://stripe.com" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm">
            </div>
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-slate-800 flex items-center gap-2">
            <span>📄</span> 2. Candidate Resume (LaTeX or Text)
          </h2>
          <textarea id="resumeText" rows="11" class="w-full font-mono text-xs p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="Paste your resume content or LaTeX code here..."></textarea>
        </div>
      </div>

      <!-- Right Column -->
      <div class="space-y-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-slate-800 flex items-center gap-2">
            <span>💼</span> 3. Target Job Description or LinkedIn Post
          </h2>
          <textarea id="jdText" rows="11" class="w-full text-xs p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="Paste a formal Job Description OR an informal LinkedIn 'We are hiring!' post text..."></textarea>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-slate-800 flex items-center gap-2">
            <span>🔑</span> 4. Gemini API Key
          </h2>
          <input id="apiKey" type="password" placeholder="Enter Gemini API Key (or loaded from environment)" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm">
        </div>
      </div>
    </div>

    <!-- Action Button -->
    <div class="mb-8">
      <button id="auditBtn" onclick="runAudit()" class="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 text-base md:text-lg">
        <span>🚀 Audit Resume & Generate 1-Min Outreach Copy</span>
      </button>
    </div>

    <!-- Loading Spinner -->
    <div id="loading" class="hidden text-center py-12">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent mb-3"></div>
      <p class="text-sm font-semibold text-slate-700">Auditing resume and drafting personalized outreach with Gemini 3.6 Flash...</p>
    </div>

    <!-- Results Section -->
    <div id="results" class="hidden space-y-6">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-extrabold text-slate-900 flex items-center gap-2">
          <span>📊</span> Audit & Outreach Suite for <span id="resCompanyName" class="text-blue-600">Company</span>
        </h2>
      </div>

      <!-- Metrics Row -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-center">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">ATS Match Score</div>
          <div id="resScore" class="text-4xl font-black my-2 text-blue-600">--</div>
          <div id="resTier" class="text-xs font-semibold px-2.5 py-1 rounded-full inline-block bg-slate-100 text-slate-700">--</div>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-left">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">Matched Keywords</div>
          <div id="resMatchedCount" class="text-3xl font-black my-2 text-emerald-600">--</div>
          <p class="text-xs text-slate-500">Hard skills & competencies verified in resume.</p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm text-left">
          <div class="text-xs font-semibold uppercase tracking-wider text-slate-500">Missing Deficiencies</div>
          <div id="resMissingCount" class="text-3xl font-black my-2 text-rose-600">--</div>
          <p class="text-xs text-slate-500">High-value keywords required by company.</p>
        </div>
      </div>

      <!-- Executive Verdict -->
      <div class="bg-blue-50/70 border-l-4 border-blue-600 p-5 rounded-r-2xl">
        <div class="font-bold text-sm text-blue-900 mb-1">📋 Executive Recruiter Verdict:</div>
        <div id="resVerdict" class="text-sm text-slate-800 leading-relaxed"></div>
      </div>

      <!-- Outreach Emails & LinkedIn Section -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 1-Min Email -->
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
              <span>✉️</span> 1-Minute Recruiter Email
            </h3>
            <button onclick="copyElementText('resEmailBody')" class="text-xs px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium">📋 Copy Body</button>
          </div>
          <div>
            <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Subject Line</label>
            <div id="resEmailSubject" class="p-2.5 bg-slate-50 rounded-xl text-xs font-semibold text-slate-800 border border-slate-200"></div>
          </div>
          <div>
            <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Email Body</label>
            <textarea id="resEmailBody" rows="7" class="w-full text-xs p-3 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none leading-relaxed"></textarea>
          </div>
        </div>

        <!-- LinkedIn Outreach -->
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
              <span>💼</span> LinkedIn Outreach
            </h3>
            <button onclick="copyElementText('resLiNote')" class="text-xs px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium">📋 Copy Note</button>
          </div>
          <div>
            <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Connection Note (&lt;300 chars)</label>
            <textarea id="resLiNote" rows="3" class="w-full text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none"></textarea>
          </div>
          <div>
            <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">InMail / DM Pitch</label>
            <textarea id="resLiDm" rows="4" class="w-full text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none"></textarea>
          </div>
        </div>
      </div>

      <!-- Keywords Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <h3 class="font-bold text-sm text-emerald-700 mb-3 flex items-center gap-1.5">
            <span>✅</span> Matched Keywords
          </h3>
          <div id="resMatchedChips" class="flex flex-wrap gap-1.5"></div>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <h3 class="font-bold text-sm text-rose-700 mb-3 flex items-center gap-1.5">
            <span>⚠️</span> Missing / Gap Keywords
          </h3>
          <div id="resMissingChips" class="flex flex-wrap gap-1.5"></div>
        </div>
      </div>

      <!-- Suggested Additions -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h3 class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
          <span>✍️</span> Exact Additions & Bullet Points to Add
        </h3>
        <div id="resAdditions" class="space-y-2"></div>
      </div>

      <!-- Google Sheets Tracker Row Section -->
      <div class="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-5 space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-sm text-emerald-900 flex items-center gap-1.5">
            <span>📊</span> Log Application to Google Sheets Tracker
          </h3>
          <a href="https://docs.google.com/spreadsheets/d/1NoKDcOeBIveTgz-mIsE1t3T4_rAcf63uH2CcIImjRJI/edit" target="_blank" class="text-xs text-emerald-700 font-semibold underline">Open Google Sheet &rarr;</a>
        </div>
        <p class="text-xs text-slate-600">Copy this TSV row and paste it directly into your tracking sheet:</p>
        <div id="resTsvRow" class="p-3 bg-white font-mono text-[11px] rounded-xl border border-emerald-300 text-slate-800 break-all select-all"></div>
      </div>

    </div>

  </div>

  <script>
    const SAMPLE_RESUME = `\\documentclass[a4paper,11pt]{article}
\\begin{document}
\\begin{center}
    \\textbf{\\Huge \\scshape Virat Patel} \\\\ \\vspace{3pt}
    {\\large Product Management} \\\\ \\vspace{4pt}
    +91 8319402171 $|$ devxvirat@gmail.com $|$ linkedin.com/in/virat-patel-28ab48285 $|$ github.com/Virat1315
\\end{center}

\\section{Experience}
  \\resumeSubheading{eComSuite}{Bangalore, Karnataka}{Product Intern}{Jun 2026 -- Aug 2026}
    \\resumeItem{Sellers had no LLM access to Amazon data, so shipped an \\textbf{MCP-powered AI product} for it.}
    \\resumeItem{Prioritized the \\textbf{backlog} by testing \\textbf{4 features} on \\textbf{40+ customers}, shipping \\textbf{5 validated fixes}.}
    \\resumeItem{Wrote \\textbf{20+ PRDs}, specs and acceptance criteria, cutting sprint rework via roadmap governance.}

  \\resumeSubheading{Flick}{Raipur, Chhattisgarh}{Product Analyst Intern}{Feb 2026 -- Jun 2026}
    \\resumeItem{Onboarding drop-off capped growth, so fixing it \\textbf{grew users 6,000 to 15,000+ (2.5x)}.}
    \\resumeItem{Manual ops slowed the team, so AI automation workflows \\textbf{cut that load 30\\%} for 15,000+ users.}
    \\resumeItem{Ran funnel and cohort analysis to prioritize the \\textbf{growth roadmap} and weekly KPIs.}

\\section{Education}
  \\resumeSubheading{IIIT Naya Raipur}{Chhattisgarh, India}{B.Tech, Electronics and Communication}{2023 -- 2027}

\\section{Projects}
  \\resumeProjectHeading{\\textbf{ConverseIQ: Enterprise AI Voice Platform} $|$ \\emph{Python, FastAPI, LLMs}}{Live Demo}
    \\resumeItem{Automated first-round screening end to end, saving a recruiter's \\textbf{20-minute call} per candidate.}
    \\resumeItem{Chained \\textbf{3 AI services} (speech-to-text, LLM, text-to-speech) into a live voice interview.}
    \\resumeItem{Built an LLM scoring engine and analytics dashboard ranking \\textbf{100\\%} of candidate calls.}

\\section{Skills}
  \\textbf{Product}{: PRDs, Roadmap Governance, User Stories, Feature Prioritization} \\\\
  \\textbf{Technical}{: Python, FastAPI, REST APIs, LLM Integration, MCP, React, Node.js, Git, SQL}
\\end{document}`;

    const SAMPLE_JD = `Role: Associate Product Manager (Platform & AI Integrations)
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
- Clear, concise written communication and exceptional attention to detail.`;

    function loadSample() {
      document.getElementById("companyName").value = "Stripe";
      document.getElementById("companyWebsite").value = "https://stripe.com";
      document.getElementById("resumeText").value = SAMPLE_RESUME;
      document.getElementById("jdText").value = SAMPLE_JD;
    }

    window.onload = loadSample;

    function copyElementText(id) {
      const el = document.getElementById(id);
      const val = el.value || el.innerText;
      navigator.clipboard.writeText(val);
      alert("Copied to clipboard!");
    }

    async function runAudit() {
      const company_name = document.getElementById("companyName").value.trim();
      const company_website = document.getElementById("companyWebsite").value.trim();
      const resume_text = document.getElementById("resumeText").value.trim();
      const jd_text = document.getElementById("jdText").value.trim();
      const api_key = document.getElementById("apiKey").value.trim();

      if (!company_name || !resume_text || !jd_text) {
        alert("Please provide Company Name, Resume, and Job Description.");
        return;
      }

      document.getElementById("loading").classList.remove("hidden");
      document.getElementById("results").classList.add("hidden");
      document.getElementById("auditBtn").disabled = true;

      try {
        const response = await fetch("/api/audit", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name,
            company_website,
            resume_text,
            jd_text,
            api_key
          })
        });

        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.detail || "Audit failed");
        }

        renderResults(data, company_name, company_website);
      } catch (err) {
        alert("Error: " + err.message);
      } finally {
        document.getElementById("loading").classList.add("hidden");
        document.getElementById("auditBtn").disabled = false;
      }
    }

    function renderResults(data, companyName, companyWebsite) {
      document.getElementById("resCompanyName").textContent = companyName;
      document.getElementById("resScore").textContent = data.ats_score + "/100";
      document.getElementById("resTier").textContent = data.score_tier;
      document.getElementById("resMatchedCount").textContent = data.matched_keywords.length + " Satisfied";
      document.getElementById("resMissingCount").textContent = data.missing_or_gap_keywords.length + " Gaps";
      document.getElementById("resVerdict").textContent = data.summary_verdict;
      
      // Outreach
      document.getElementById("resEmailSubject").textContent = data.outreach_email_subject;
      document.getElementById("resEmailBody").value = data.outreach_email_body;
      document.getElementById("resLiNote").value = data.linkedin_connection_note;
      document.getElementById("resLiDm").value = data.linkedin_outreach_dm;

      // Matched chips
      const matchedContainer = document.getElementById("resMatchedChips");
      matchedContainer.innerHTML = data.matched_keywords.map(kw => 
        `<span class="px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-semibold">✓ ${kw}</span>`
      ).join("");

      // Missing chips
      const missingContainer = document.getElementById("resMissingChips");
      missingContainer.innerHTML = data.missing_or_gap_keywords.map(kw => 
        `<span class="px-2.5 py-1 bg-rose-50 text-rose-700 border border-rose-200 rounded-full text-xs font-semibold">! ${kw}</span>`
      ).join("");

      // Additions
      const additionsContainer = document.getElementById("resAdditions");
      if (data.suggested_additions_and_bullets && data.suggested_additions_and_bullets.length > 0) {
        additionsContainer.innerHTML = data.suggested_additions_and_bullets.map((add, idx) => 
          `<div class="p-3 bg-slate-50 border-l-4 border-emerald-500 rounded-r-xl text-xs text-slate-800 font-medium">
             <div class="text-[10px] uppercase font-bold text-emerald-700 mb-0.5">Addition #${idx+1}:</div>
             ${add}
           </div>`
        ).join("");
      } else {
        additionsContainer.innerHTML = `<div class="text-xs text-slate-500">No additional bullets required.</div>`;
      }

      // TSV Tracker Row
      const now = new Date().toISOString().split('T')[0];
      const tsv = `${now}\\t${companyName}\\t${companyWebsite}\\t${data.ats_score}/100\\t${data.score_tier}\\tApplied\\t${data.outreach_email_subject}`;
      document.getElementById("resTsvRow").textContent = tsv;

      document.getElementById("results").classList.remove("hidden");
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return HTMLResponse(content=HTML_TEMPLATE)
