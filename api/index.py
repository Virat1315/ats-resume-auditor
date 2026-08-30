import os
import sys
import io
import json
import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response, Depends, Header
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Ensure root directory is on sys.path for exporters module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from exporters import latex_to_docx, latex_to_pdf
except ImportError:
    from ..exporters import latex_to_docx, latex_to_pdf

load_dotenv()

app = FastAPI(title="Virat Patel - ATS Auditor & Outreach Suite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# Authentication Configuration
# ==========================================
AUTH_USERNAME = "Test"
AUTH_PASSWORD = "Test@1234"
SESSION_TOKEN = "virat_ats_auth_session_token_2026"

class LoginRequest(BaseModel):
    username: str
    password: str

class AuditRequest(BaseModel):
    company_name: str
    company_website: str = ""
    resume_text: str
    jd_text: str
    api_key: str = ""
    webhook_url: str = ""
    auth_token: str = ""

class ExportRequest(BaseModel):
    latex_code: str
    auth_token: str = ""

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
# Auth Helper
# ==========================================
def verify_token(token: str):
    if token != SESSION_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized. Please log in.")

# ==========================================
# API Endpoints
# ==========================================
@app.post("/api/login")
async def login_endpoint(req: LoginRequest):
    if req.username.strip() == AUTH_USERNAME and req.password.strip() == AUTH_PASSWORD:
        return {"status": "success", "token": SESSION_TOKEN, "username": AUTH_USERNAME}
    raise HTTPException(status_code=401, detail="Invalid username or password.")

@app.post("/api/audit")
async def audit_endpoint(req: AuditRequest):
    verify_token(req.auth_token)
    
    # Priority: req.api_key -> os.getenv("GEMINI_API_KEY")
    api_key = req.api_key.strip() if req.api_key.strip() else os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="Gemini API Key is not configured. Please add GEMINI_API_KEY to environment variables in Vercel.")
        
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

@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """Parse uploaded PDF, TEX, or TXT file."""
    try:
        content = await file.read()
        filename = file.filename.lower()
        
        if filename.endswith(".pdf"):
            from pypdf import PdfReader
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)
            extracted = []
            for p in reader.pages:
                t = p.extract_text()
                if t:
                    extracted.append(t.strip())
            text = "\n\n".join(extracted)
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="ignore")
                
        return {"filename": file.filename, "text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

@app.post("/api/export-pdf")
async def export_pdf(req: ExportRequest):
    """Generate 1-Page PDF from LaTeX/Resume."""
    verify_token(req.auth_token)
    try:
        pdf_io = latex_to_pdf(req.latex_code)
        return Response(
            content=pdf_io.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="Virat_Patel_Resume.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@app.post("/api/export-docx")
async def export_docx(req: ExportRequest):
    """Generate 1-Page Word DOCX from LaTeX/Resume."""
    verify_token(req.auth_token)
    try:
        docx_io = latex_to_docx(req.latex_code)
        return Response(
            content=docx_io.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="Virat_Patel_Resume.docx"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DOCX generation failed: {str(e)}")

# ==========================================
# Frontend HTML
# ==========================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Virat Patel - Company-Specific ATS Auditor & Outreach Suite</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .hero-grad { background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 50%, #0284C7 100%); }
    .badge-matched { background-color: rgba(16, 185, 129, 0.15); color: #059669; border: 1px solid rgba(16, 185, 129, 0.35); }
    .badge-missing { background-color: rgba(239, 68, 68, 0.15); color: #DC2626; border: 1px solid rgba(239, 68, 68, 0.35); }
  </style>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  
  <!-- Authentication Gate Screen -->
  <div id="authScreen" class="min-h-screen flex items-center justify-center px-4 py-12">
    <div class="max-w-md w-full bg-white rounded-3xl p-8 border border-slate-200 shadow-xl space-y-6 text-center">
      <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto text-3xl shadow-inner">
        🔒
      </div>
      <div>
        <h2 class="text-2xl font-extrabold text-slate-900">ATS Auditor Access</h2>
        <p class="text-xs md:text-sm text-slate-500 mt-1">Please sign in to access your personal screening suite.</p>
      </div>

      <div class="space-y-4 text-left">
        <div>
          <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Username</label>
          <input id="loginUsername" type="text" placeholder="e.g. Test" class="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm">
        </div>
        <div>
          <label class="block text-xs font-bold uppercase text-slate-500 mb-1">Password</label>
          <input id="loginPassword" type="password" placeholder="••••••••" class="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-sm" onkeydown="if(event.key==='Enter')handleLogin()">
        </div>
      </div>

      <div id="loginError" class="hidden p-3 bg-rose-50 text-rose-700 text-xs font-semibold rounded-xl border border-rose-200">
        ❌ Invalid username or password.
      </div>

      <button onclick="handleLogin()" class="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all text-sm">
        🚀 Sign In
      </button>
    </div>
  </div>

  <!-- Main Authenticated App Container -->
  <div id="appContainer" class="hidden max-w-6xl mx-auto px-4 py-6 md:py-8">
    
    <!-- Hero Header -->
    <div class="hero-grad text-white rounded-2xl p-6 md:p-8 shadow-xl mb-6">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 bg-white/10 rounded-full text-xs font-semibold uppercase tracking-wider mb-2">
            <span>🎯 Personal AI Recruiter & ATS Screener</span>
          </div>
          <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight">Virat Patel &bull; ATS Auditor & Outreach Suite</h1>
          <p class="text-slate-200 text-xs md:text-sm mt-1">Strict ATS scoring, missing keyword gaps, 1-minute recruiter email & LinkedIn pitch, with Google Sheets tracking.</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button onclick="exportDoc('pdf')" class="px-3.5 py-2 bg-white text-slate-900 hover:bg-slate-100 text-xs font-bold rounded-xl shadow transition-all flex items-center gap-1.5">
            📄 1-Page PDF
          </button>
          <button onclick="exportDoc('docx')" class="px-3.5 py-2 bg-white/15 hover:bg-white/25 text-white border border-white/20 text-xs font-semibold rounded-xl transition-all flex items-center gap-1.5">
            📝 1-Page Word
          </button>
          <button onclick="exportDoc('tex')" class="px-3.5 py-2 bg-white/15 hover:bg-white/25 text-white border border-white/20 text-xs font-semibold rounded-xl transition-all flex items-center gap-1.5">
            📄 LaTeX (.tex)
          </button>
          <button onclick="handleLogout()" class="px-3 py-2 bg-rose-500/30 hover:bg-rose-500/50 text-rose-100 border border-rose-400/30 text-xs font-semibold rounded-xl transition-all ml-1">
            Logout
          </button>
        </div>
      </div>
    </div>

    <!-- Preset Company Bar -->
    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div class="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
        <span>⚡ Quick Preset Roles:</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <button onclick="loadPreset('Stripe')" class="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 text-xs font-semibold rounded-lg border border-blue-200 transition-all">Stripe (APM)</button>
        <button onclick="loadPreset('Vercel')" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-lg border border-slate-300 transition-all">Vercel (Early PM)</button>
        <button onclick="loadPreset('Google')" class="px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-lg border border-emerald-200 transition-all">Google (APM)</button>
        <button onclick="loadPreset('OpenAI')" class="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-700 text-xs font-semibold rounded-lg border border-purple-200 transition-all">OpenAI (Product)</button>
        <button onclick="loadPreset('Amazon')" class="px-3 py-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 text-xs font-semibold rounded-lg border border-amber-200 transition-all">Amazon (PM-T)</button>
      </div>
    </div>

    <!-- Inputs Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      <!-- Left Column: Company Profile & Resume -->
      <div class="space-y-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-sm text-slate-800 flex items-center gap-2">
            <span>🏢</span> 1. Target Company Profile
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Company Name</label>
              <input id="companyName" type="text" value="Stripe" placeholder="e.g. Stripe, Vercel, Google" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-xs md:text-sm">
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Website / Careers URL</label>
              <input id="companyWebsite" type="text" value="https://stripe.com" placeholder="https://stripe.com" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-xs md:text-sm">
            </div>
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <div class="flex items-center justify-between">
            <h2 class="font-bold text-sm text-slate-800 flex items-center gap-2">
              <span>📄</span> 2. Candidate Resume
            </h2>
            <label class="cursor-pointer text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1">
              <span>📁 Upload File (PDF/TEX/TXT)</span>
              <input type="file" id="fileUpload" accept=".pdf,.tex,.txt" class="hidden" onchange="handleFileUpload(event)">
            </label>
          </div>
          <textarea id="resumeText" rows="11" class="w-full font-mono text-[11px] md:text-xs p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none" placeholder="Paste your resume content or LaTeX code here..."></textarea>
          <div class="flex items-center justify-between text-[11px] text-slate-500">
            <span id="resumeStats">Master Jake Ryan LaTeX Preloaded</span>
            <button onclick="resetMasterResume()" class="text-blue-600 hover:underline">Reset to Virat's Master Resume</button>
          </div>
        </div>
      </div>

      <!-- Right Column: JD & Optional Settings -->
      <div class="space-y-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-sm text-slate-800 flex items-center gap-2">
            <span>💼</span> 3. Target Job Description or LinkedIn Post
          </h2>
          <textarea id="jdText" rows="11" class="w-full text-[11px] md:text-xs p-3 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none leading-relaxed" placeholder="Paste a formal Job Description OR an informal LinkedIn 'We are hiring!' post text..."></textarea>
          <div class="text-[11px] text-slate-500 flex justify-between">
            <span>Compatible with formal JDs, LinkedIn posts & founder tweets</span>
            <span id="jdStats"></span>
          </div>
        </div>

        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
          <h2 class="font-bold text-sm text-slate-800 flex items-center gap-2">
            <span>⚙️</span> Optional Config (API Key / Sheet Webhook)
          </h2>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Gemini API Key (Optional)</label>
              <input id="apiKey" type="password" placeholder="Loaded automatically from Vercel" class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-xs">
            </div>
            <div>
              <label class="block text-[11px] font-bold uppercase text-slate-500 mb-1">Google Apps Script Webhook</label>
              <input id="webhookUrl" type="text" placeholder="https://script.google.com/..." class="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none text-xs">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Action Button -->
    <div class="mb-8">
      <button id="auditBtn" onclick="runAudit()" class="w-full py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 text-base md:text-lg">
        <span>🚀 Audit Resume, Score ATS & Draft 1-Min Outreach Suite</span>
      </button>
    </div>

    <!-- Loading Spinner -->
    <div id="loading" class="hidden text-center py-12">
      <div class="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent mb-3"></div>
      <p class="text-sm font-semibold text-slate-700">Auditing resume against company hiring bar & drafting outreach copy...</p>
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

      <!-- Perfect Match Banner -->
      <div id="perfectBanner" class="hidden p-4 bg-emerald-50 border border-emerald-300 rounded-2xl text-emerald-900 font-semibold text-xs md:text-sm">
        🏆 <strong>PERFECT MATCH — No Changes Required!</strong> Your resume satisfies all key requirements, scale metrics, and cultural pillars for this role.
      </div>

      <div class="bg-blue-50/70 border-l-4 border-blue-600 p-5 rounded-r-2xl">
        <div class="font-bold text-xs uppercase tracking-wider text-blue-900 mb-1">📋 Executive Recruiter Verdict:</div>
        <div id="resVerdict" class="text-xs md:text-sm text-slate-800 leading-relaxed font-medium"></div>
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
            <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Subject Line</label>
            <div id="resEmailSubject" class="p-2.5 bg-slate-50 rounded-xl text-xs font-semibold text-slate-800 border border-slate-200 select-all"></div>
          </div>
          <div>
            <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">Email Body (<span id="emailWordCount"></span> words)</label>
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
            <div class="flex justify-between items-center mb-1">
              <label class="block text-[10px] font-bold uppercase text-slate-500">Connection Note (&lt;300 chars)</label>
              <span id="liNoteLen" class="text-[10px] font-semibold text-slate-500"></span>
            </div>
            <textarea id="resLiNote" rows="3" class="w-full text-xs p-2.5 rounded-xl bg-slate-50 border border-slate-200 focus:outline-none"></textarea>
          </div>
          <div>
            <label class="block text-[10px] font-bold uppercase text-slate-500 mb-1">InMail / DM Pitch</label>
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

      <!-- Culture Fit & Red Flags -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <h3 class="font-bold text-sm text-slate-800 mb-2 flex items-center gap-1.5">
            <span>🏢</span> Company Hiring Bar & Culture Fit
          </h3>
          <p id="resCulture" class="text-xs md:text-sm text-slate-700 leading-relaxed"></p>
        </div>
        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <h3 class="font-bold text-sm text-rose-900 mb-2 flex items-center gap-1.5">
            <span>🚩</span> Potential Red Flags & Hesitations
          </h3>
          <div id="resRedFlags" class="space-y-2"></div>
        </div>
      </div>

      <!-- Action Checklist -->
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <h3 class="font-bold text-sm text-slate-900 flex items-center gap-1.5">
          <span>✅</span> Pre-Submission Action Checklist
        </h3>
        <div id="resChecklist" class="space-y-2"></div>
      </div>

      <!-- Google Sheets Tracker Row Section -->
      <div class="bg-emerald-50/70 border border-emerald-200 rounded-2xl p-5 space-y-3">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <h3 class="font-bold text-sm text-emerald-900 flex items-center gap-1.5">
            <span>📊</span> Log Application to Google Sheets Tracker
          </h3>
          <a href="https://docs.google.com/spreadsheets/d/1NoKDcOeBIveTgz-mIsE1t3T4_rAcf63uH2CcIImjRJI/edit?usp=sharing" target="_blank" class="text-xs text-emerald-700 font-semibold underline">Open Connected Google Sheet &rarr;</a>
        </div>
        <p class="text-xs text-slate-600">Copy this TSV row or push directly via Webhook:</p>
        <div id="resTsvRow" class="p-3 bg-white font-mono text-[11px] rounded-xl border border-emerald-300 text-slate-800 break-all select-all"></div>
        <div class="flex gap-2">
          <button onclick="copyElementText('resTsvRow')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-sm">📋 Copy Row to Clipboard</button>
          <button onclick="pushWebhook()" class="px-3.5 py-1.5 bg-white hover:bg-slate-50 text-emerald-800 border border-emerald-300 font-semibold text-xs rounded-xl shadow-sm">🚀 Push to Sheet via Webhook</button>
        </div>
      </div>

    </div>

  </div>

  <script>
    const MASTER_LATEX_RESUME = `\\documentclass[a4paper,11pt]{article}
\\usepackage{latexsym}
\\usepackage[empty]{fullpage}
\\usepackage{titlesec}
\\usepackage{marvosym}
\\usepackage[usenames,dvipsnames]{color}
\\usepackage{verbatim}
\\usepackage{enumitem}
\\usepackage[hidelinks]{hyperref}
\\usepackage{fancyhdr}
\\usepackage[english]{babel}
\\usepackage{tabularx}
\\input{glyphtounicode}

\\pagestyle{fancy}
\\fancyhf{}
\\fancyfoot{}
\\renewcommand{\\headrulewidth}{0pt}
\\renewcommand{\\footrulewidth}{0pt}

\\addtolength{\\oddsidemargin}{-0.57in}
\\addtolength{\\evensidemargin}{-0.57in}
\\addtolength{\\textwidth}{1.13in}
\\addtolength{\\topmargin}{-0.60in}
\\addtolength{\\textheight}{1.21in}

\\urlstyle{same}
\\raggedbottom
\\raggedright
\\setlength{\\tabcolsep}{0in}

\\titleformat{\\section}{
  \\vspace{2pt}\\scshape\\raggedright\\large
}{}{0em}{}[\\color{black}\\titlerule \\vspace{-3pt}]
\\titlespacing*{\\section}{0pt}{10pt}{5pt}

\\pdfgentounicode=1

\\newcommand{\\resumeItem}[1]{\\item\\small{#1}}

\\newcommand{\\resumeSubheading}[4]{
  \\vspace{-1pt}\\item
    \\begin{tabular*}{0.97\\textwidth}[t]{l@{\\extracolsep{\\fill}}r}
      \\textbf{#1} & #2 \\\\
      \\textit{\\small#3} & \\textit{\\small #4} \\\\
    \\end{tabular*}\\vspace{-5pt}
}

\\newcommand{\\resumeProjectHeading}[2]{
    \\item
    \\begin{tabular*}{0.97\\textwidth}{l@{\\extracolsep{\\fill}}r}
      \\small#1 & #2 \\\\
    \\end{tabular*}\\vspace{-2pt}
}

\\renewcommand\\labelitemii{$\\vcenter{\\hbox{\\tiny$\\bullet$}}$}

\\newcommand{\\resumeSubHeadingListStart}{\\begin{itemize}[leftmargin=0.15in, label={}]}
\\newcommand{\\resumeSubHeadingListEnd}{\\end{itemize}}
\\newcommand{\\resumeItemListStart}{%
  \\begin{itemize}[leftmargin=0.17in, topsep=3pt, itemsep=2.5pt,
                  parsep=0pt, partopsep=0pt]}
\\newcommand{\\resumeItemListEnd}{\\end{itemize}\\vspace{-2pt}}

\\begin{document}

\\begin{center}
    \\textbf{\\Huge \\scshape Virat Patel} \\\\ \\vspace{3pt}
    {\\large Product Management} \\\\ \\vspace{4pt}
    \\small
    +91 8319402171 $|$
    \\href{mailto:devxvirat@gmail.com}{\\underline{devxvirat@gmail.com}} $|$
    \\href{https://www.linkedin.com/in/virat-patel-28ab48285/}{\\underline{linkedin.com/in/virat-patel-28ab48285}} $|$
    \\href{https://github.com/Virat1315}{\\underline{github.com/Virat1315}}
\\end{center}

\\section{Experience}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {eComSuite}{Bangalore, Karnataka}
      {Product Intern}{Jun 2026 -- Aug 2026}
      \\resumeItemListStart
        \\resumeItem{Sellers had no LLM access to Amazon data, so shipped an \\textbf{MCP-powered AI product} for it.}
        \\resumeItem{Prioritized the \\textbf{backlog} by testing \\textbf{4 features} on \\textbf{40+ customers}, shipping \\textbf{5 validated fixes}.}
        \\resumeItem{Wrote \\textbf{20+ PRDs}, specs and acceptance criteria, cutting sprint rework via roadmap governance.}
      \\resumeItemListEnd

    \\resumeSubheading
      {Flick}{Raipur, Chhattisgarh}
      {Product Analyst Intern}{Feb 2026 -- Jun 2026}
      \\resumeItemListStart
        \\resumeItem{Onboarding drop-off capped growth, so fixing it \\textbf{grew users 6,000 to 15,000+ (2.5x)}.}
        \\resumeItem{Manual ops slowed the team, so AI automation workflows \\textbf{cut that load 30\\%} for 15,000+ users.}
        \\resumeItem{Ran funnel and cohort analysis to prioritize the \\textbf{growth roadmap} and weekly KPIs.}
      \\resumeItemListEnd

    \\resumeSubheading
      {Raipur Municipal Corporation}{Raipur, Chhattisgarh}
      {Product \\& Software Development Intern}{Jun 2025 -- Jul 2025}
      \\resumeItemListStart
        \\resumeItem{Citizens lacked a fast query channel, so an \\textbf{AI chatbot} absorbed \\textbf{4,200+} of them.}
        \\resumeItem{That deflected repeat queries from the front desk, freeing staff for high-value cases.}
        \\resumeItem{Integrated REST APIs and automated manual workflows, keeping uptime steady at peak volume.}
      \\resumeItemListEnd
  \\resumeSubHeadingListEnd

\\section{Education}
  \\resumeSubHeadingListStart
    \\resumeSubheading
      {International Institute of Information Technology, Naya Raipur}{Chhattisgarh, India}
      {B.Tech, Electronics and Communication Engineering}{Aug 2023 -- Jul 2027}
  \\resumeSubHeadingListEnd

\\section{Projects}
  \\resumeSubHeadingListStart
    \\resumeProjectHeading
      {\\textbf{ConverseIQ: Enterprise AI Voice Platform} $|$ \\emph{Python, FastAPI, LLMs}}
      {\\href{https://converseiq.vercel.app/}{\\underline{Live Demo}}}
      \\resumeItemListStart
        \\item[]\\small\\textit{Business outcome: \\textbf{cuts recruiter screening time} so hiring teams reach top candidates faster.}\\vspace{-1pt}
        \\resumeItem{Automated first-round screening end to end, saving a recruiter's \\textbf{20-minute call} per candidate.}
        \\resumeItem{Chained \\textbf{3 AI services} (speech-to-text, LLM, text-to-speech) into a live voice interview.}
        \\resumeItem{Built an LLM scoring engine and analytics dashboard ranking \\textbf{100\\%} of candidate calls.}
      \\resumeItemListEnd

    \\resumeProjectHeading
      {\\textbf{TechnoGate: Smart Event Ticketing Platform} $|$ \\emph{FastAPI, SQL, QR}}
      {\\href{https://technogate.vercel.app/}{\\underline{Live Demo}}}
      \\resumeItemListStart
        \\item[]\\small\\textit{Business outcome: \\textbf{replaced paper check-in}, cutting gate wait times at scale.}\\vspace{-1pt}
        \\resumeItem{Gate entry for \\textbf{10,000+ attendees} ran on a QR ticketing platform built end to end.}
        \\resumeItem{One-time QR validation eliminated duplicates across \\textbf{10,000+} ticket scans at the gates.}
        \\resumeItem{Gave \\textbf{50+ organizers and volunteers} one dashboard for gates, passes and access control.}
      \\resumeItemListEnd

    \\resumeProjectHeading
      {\\textbf{Apple AirDrop: Product Teardown} $|$ \\emph{User Research, Prioritization, Metrics}}
      {\\href{https://canva.link/t0usuvg59ckties}{\\underline{Case Study}}}
      \\resumeItemListStart
       \\item[]\\small\\textit{Business outcome: \\textbf{a prioritized fix roadmap} for improving AirDrop’s file transfer experience.}\\vspace{-1pt}
        \\resumeItem{Synthesized \\textbf{100+ community posts} across \\textbf{4 personas} into 5 ranked friction themes.}
        \\resumeItem{Scored each issue on impact, frequency and whether it blocks the core send-a-file job.}
        \\resumeItem{Proposed \\textbf{5 fixes (P1 to P3)} with \\textbf{6 success metrics}, incl. transfer completion rate.}
      \\resumeItemListEnd
  \\resumeSubHeadingListEnd

\\section{Skills}
 \\begin{itemize}[leftmargin=0.15in, label={}]
    \\small{\\item{
     \\textbf{Product}{: PRDs, Roadmap Governance, User Stories, Feature Prioritization} \\\\
     \\textbf{Research}{: User Research, A/B Testing, Funnel Analysis, Cohort Analysis, Personas} \\\\
     \\textbf{Analytics}{: SQL, Power BI, Mixpanel, Google Analytics, KPI Dashboards} \\\\
     \\textbf{Technical}{: Python, FastAPI, REST APIs, LLM Integration, MCP, React, Node.js, Git, GCP} \\\\
     \\textbf{Delivery}{: Jira, Figma, Notion, Agile \\& Scrum, Sprint Planning, Stakeholder Management}
    }}
 \\end{itemize}

\\section{Achievements}
  \\resumeItemListStart
    \\resumeItem{Research paper on HAM-1 and HAM-2 shortlisted for \\textbf{TENCON 2026}, Bali (IEEE Region 10 Conference).}
    \\resumeItem{\\textbf{UG Representative (College President)}, IIIT Naya Raipur, representing the UG body in institute decisions.}
    \\resumeItem{Led end-to-end execution of a student-run cultural fest of \\textbf{10,000+ participants}, the largest in IIIT-NR's history.}
  \\resumeItemListEnd

\\end{document}`;

    const PRESETS = {
      Stripe: {
        company: "Stripe",
        website: "https://stripe.com",
        jd: `Role: Associate Product Manager (Platform & AI Integrations)\\nCompany: Stripe\\nWebsite: https://stripe.com\\n\\nAbout Stripe & The Role:\\nStripe builds economic infrastructure for the internet. As an Associate Product Manager on our Platform & AI Integrations team, you will design developer-first APIs, build high-reliability payment workflows, and harness generative AI/LLMs to reduce integration friction for millions of global businesses.\\n\\nWhat You'll Do:\\n- Write high-clarity Product Requirement Documents (PRDs) with rigorous technical depth, user journeys, and API contracts.\\n- Partner closely with engineering, data science, and design to define product roadmap, quarterly OKRs, and backlog priorities.\\n- Perform quantitative user research, SQL cohort analysis, funnel drop-off analytics, and latency telemetry.\\n- Evaluate developer experience (DX), API reliability, SDK integrations, and Model Context Protocol (MCP) integrations.\\n- Drive cross-functional alignment and champion operational excellence across global stakeholders.\\n\\nWho You Are:\\n- Rigorous analytical thinker with a strong technical background (Computer Science, Engineering, or equivalent).\\n- Proven track record of user-centric product discovery, hypothesis testing, and data-driven prioritization.\\n- Experience with APIs, Python/FastAPI, SQL analytics, LLM workflows, and developer platforms.\\n- Clear, concise written communication and exceptional attention to detail.`
      },
      Vercel: {
        company: "Vercel",
        website: "https://vercel.com",
        jd: `🚀 We are hiring an Early Product Manager at Vercel!\\nLooking for someone who lives and breathes developer workflows, Next.js, v0, AI SDK, and fast execution.\\n\\nWhat you'll own:\\n- Deep customer discovery with 100+ devs weekly.\\n- Developer UX, CLI/API ergonomics, and AI platform integrations.\\n- Defining PRDs and collaborating with world-class engineers to ship weekly releases.\\n\\nIf you have built dev tools, shipped AI products with Python/Next.js/MCP, and love talking to developers, apply here or DM me!`
      },
      Google: {
        company: "Google",
        website: "https://careers.google.com",
        jd: `Role: Associate Product Manager (APM)\\nCompany: Google\\n\\nResponsibilities:\\n- Drive product strategy and execution for planetary-scale applications reaching 1B+ users.\\n- Partner with engineering to design ML/AI algorithms, technical architecture, and telemetry dashboards.\\n- Craft structured PRDs, conduct user experiments, and analyze large-scale telemetry using SQL and statistical modeling.\\n- Exhibit strong product intuition, analytical rigor, and leadership without authority.`
      },
      OpenAI: {
        company: "OpenAI",
        website: "https://openai.com",
        jd: `Role: Product Manager (API & Platform Ecosystem)\\nCompany: OpenAI\\n\\nAbout the Role:\\nWe are looking for a technical Product Manager to build platform developer tooling, model evaluation APIs, and agentic workflows (MCP, function calling, vector search).\\n\\nRequirements:\\n- Strong background in Computer Science or Software Engineering.\\n- Experience shipping developer platforms, LLM APIs, and Python/FastAPI microservices.\\n- Passion for AI alignment, safety, and high-velocity developer experience.`
      },
      Amazon: {
        company: "Amazon",
        website: "https://amazon.jobs",
        jd: `Role: Technical Product Manager (PM-T)\\nCompany: Amazon\\n\\nResponsibilities:\\n- Author Working Backwards documents (PR/FAQ) and detailed technical specifications.\\n- Own customer discovery and deep-dive data metrics using SQL and AWS analytics.\\n- Embody Amazon Leadership Principles (Customer Obsession, Ownership, Bias for Action, Deliver Results).`
      }
    };

    // Auth & Init
    const AUTH_KEY = "virat_ats_token";

    function checkAuth() {
      const token = localStorage.getItem(AUTH_KEY);
      if (token === "virat_ats_auth_session_token_2026") {
        document.getElementById("authScreen").classList.add("hidden");
        document.getElementById("appContainer").classList.remove("hidden");
      } else {
        document.getElementById("authScreen").classList.remove("hidden");
        document.getElementById("appContainer").classList.add("hidden");
      }
    }

    async function handleLogin() {
      const u = document.getElementById("loginUsername").value.trim();
      const p = document.getElementById("loginPassword").value.trim();
      
      try {
        const res = await fetch("/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        localStorage.setItem(AUTH_KEY, data.token);
        document.getElementById("loginError").classList.add("hidden");
        checkAuth();
      } catch (err) {
        document.getElementById("loginError").classList.remove("hidden");
      }
    }

    function handleLogout() {
      localStorage.removeItem(AUTH_KEY);
      checkAuth();
    }

    function loadPreset(name) {
      if (PRESETS[name]) {
        document.getElementById("companyName").value = PRESETS[name].company;
        document.getElementById("companyWebsite").value = PRESETS[name].website;
        document.getElementById("jdText").value = PRESETS[name].jd.replace(/\\\\n/g, '\\n');
      }
    }

    function resetMasterResume() {
      document.getElementById("resumeText").value = MASTER_LATEX_RESUME;
      alert("Reset to Virat's Master Jake Ryan LaTeX Resume!");
    }

    window.onload = function() {
      checkAuth();
      document.getElementById("resumeText").value = MASTER_LATEX_RESUME;
      loadPreset("Stripe");
    };

    function copyElementText(id) {
      const el = document.getElementById(id);
      const val = el.value || el.innerText;
      navigator.clipboard.writeText(val);
      alert("Copied to clipboard!");
    }

    async function handleFileUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch("/api/upload-resume", {
          method: "POST",
          body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Upload failed");
        
        document.getElementById("resumeText").value = data.text;
        document.getElementById("resumeStats").textContent = `Uploaded: ${data.filename} (${data.text.length} chars)`;
      } catch (err) {
        alert("File upload error: " + err.message);
      }
    }

    async function exportDoc(type) {
      const code = document.getElementById("resumeText").value;
      if (!code) {
        alert("Resume content is empty.");
        return;
      }

      if (type === "tex") {
        const blob = new Blob([code], { type: "text/plain" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "Virat_Patel_Resume.tex";
        a.click();
        return;
      }

      const endpoint = type === "pdf" ? "/api/export-pdf" : "/api/export-docx";
      const filename = type === "pdf" ? "Virat_Patel_Resume.pdf" : "Virat_Patel_Resume.docx";
      const token = localStorage.getItem(AUTH_KEY);

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ latex_code: code, auth_token: token })
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Export failed");
        }

        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
      } catch (err) {
        alert("Export error: " + err.message);
      }
    }

    async function runAudit() {
      const company_name = document.getElementById("companyName").value.trim();
      const company_website = document.getElementById("companyWebsite").value.trim();
      const resume_text = document.getElementById("resumeText").value.trim();
      const jd_text = document.getElementById("jdText").value.trim();
      const api_key = document.getElementById("apiKey").value.trim();
      const webhook_url = document.getElementById("webhookUrl").value.trim();
      const auth_token = localStorage.getItem(AUTH_KEY);

      if (!company_name || !resume_text || !jd_text) {
        alert("Please provide Company Name, Resume, and Job Description/Post.");
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
            api_key,
            webhook_url,
            auth_token
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
      document.getElementById("resCulture").textContent = data.company_culture_and_bar_fit;

      if (data.is_perfect_match) {
        document.getElementById("perfectBanner").classList.remove("hidden");
      } else {
        document.getElementById("perfectBanner").classList.add("hidden");
      }
      
      // Outreach
      document.getElementById("resEmailSubject").textContent = data.outreach_email_subject;
      document.getElementById("resEmailBody").value = data.outreach_email_body;
      document.getElementById("emailWordCount").textContent = data.outreach_email_body.split(/\\s+/).length;

      document.getElementById("resLiNote").value = data.linkedin_connection_note;
      document.getElementById("liNoteLen").textContent = data.linkedin_connection_note.length + " / 300 chars";
      document.getElementById("resLiDm").value = data.linkedin_outreach_dm;

      // Matched chips
      const matchedContainer = document.getElementById("resMatchedChips");
      matchedContainer.innerHTML = data.matched_keywords.map(kw => 
        `<span class="badge-matched px-2.5 py-1 rounded-full text-xs font-semibold">✓ ${kw}</span>`
      ).join("");

      // Missing chips
      const missingContainer = document.getElementById("resMissingChips");
      missingContainer.innerHTML = data.missing_or_gap_keywords.map(kw => 
        `<span class="badge-missing px-2.5 py-1 rounded-full text-xs font-semibold">! ${kw}</span>`
      ).join("");

      // Additions
      const additionsContainer = document.getElementById("resAdditions");
      if (data.suggested_additions_and_bullets && data.suggested_additions_and_bullets.length > 0) {
        additionsContainer.innerHTML = data.suggested_additions_and_bullets.map((add, idx) => 
          `<div class="p-3 bg-slate-50 border-l-4 border-emerald-500 rounded-r-xl text-xs text-slate-800 font-medium flex justify-between items-start gap-2">
             <div>
               <div class="text-[10px] uppercase font-bold text-emerald-700 mb-0.5">Addition #${idx+1}:</div>
               <div>${add}</div>
             </div>
             <button onclick="navigator.clipboard.writeText('${add.replace(/'/g, "\\\\'")}'); alert('Copied bullet!');" class="text-[10px] px-2 py-1 bg-white border border-slate-200 hover:bg-slate-50 rounded text-slate-700 font-semibold shrink-0">Copy</button>
           </div>`
        ).join("");
      } else {
        additionsContainer.innerHTML = `<div class="text-xs text-slate-500">No additional bullets required.</div>`;
      }

      // Red Flags
      const redFlagsContainer = document.getElementById("resRedFlags");
      if (data.company_specific_red_flags && data.company_specific_red_flags.length > 0) {
        redFlagsContainer.innerHTML = data.company_specific_red_flags.map(rf => 
          `<div class="p-2.5 bg-rose-50 border-l-4 border-rose-500 rounded-r-xl text-xs text-rose-800 font-medium">⚠️ ${rf}</div>`
        ).join("");
      } else {
        redFlagsContainer.innerHTML = `<div class="text-xs text-emerald-700">No critical red flags detected.</div>`;
      }

      // Checklist
      const checklistContainer = document.getElementById("resChecklist");
      checklistContainer.innerHTML = data.final_action_checklist.map(step => 
        `<label class="flex items-start gap-2 p-2 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 cursor-pointer">
           <input type="checkbox" class="mt-0.5 rounded text-blue-600 focus:ring-blue-500">
           <span>${step}</span>
         </label>`
      ).join("");

      // TSV Tracker Row
      const now = new Date().toISOString().split('T')[0];
      const tsv = `${now}\\t${companyName}\\t${companyWebsite}\\t${data.ats_score}/100\\t${data.score_tier}\\tApplied\\t${data.outreach_email_subject}`;
      document.getElementById("resTsvRow").textContent = tsv;

      document.getElementById("results").classList.remove("hidden");
      document.getElementById("results").scrollIntoView({ behavior: "smooth" });
    }

    async function pushWebhook() {
      const webhook = document.getElementById("webhookUrl").value.trim();
      if (!webhook) {
        alert("Please enter your Google Apps Script Webhook URL in the optional settings box.");
        return;
      }
      
      const tsv = document.getElementById("resTsvRow").textContent;
      const parts = tsv.split("\\t");
      
      try {
        await fetch(webhook, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            "Date": parts[0],
            "Company": parts[1],
            "Website": parts[2],
            "ATS Score": parts[3],
            "Tier": parts[4],
            "Status": parts[5],
            "Subject Line": parts[6]
          }),
          mode: "no-cors"
        });
        alert("Pushed to Google Sheets via Webhook!");
      } catch (err) {
        alert("Webhook push error: " + err.message);
      }
    }
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def serve_home():
    return HTMLResponse(content=HTML_TEMPLATE)
