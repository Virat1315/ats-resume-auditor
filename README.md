# Company-Specific ATS Resume Auditor & Screener

An AI-powered ATS screening and recruiter evaluation engine tailored to your target company's specific hiring bar (e.g. Stripe, Google, Amazon, OpenAI).

## 🚀 Features

- **Company-Specific Targeting**: Calibrates evaluation against the target company's culture, hiring bar, and domain requirements.
- **Honest ATS Score & Recruiter Verdict**: Objective 0–100 score, tier rating, and *"No changes required"* badge if already perfect.
- **Keyword Gap Match**: Matched vs missing hard skills & frameworks.
- **Actionable Bullet Enhancements**: Concrete bullet points ready to copy-paste directly into your resume.
- **Company Red Flags & Pre-Submission Checklist**: Specific friction points to address before submitting.

---

## 🌐 Deploying on Vercel

1. Push this repository to GitHub.
2. Go to [Vercel Dashboard](https://vercel.com/dashboard).
3. Click **Add New...** -> **Project** -> Import your GitHub repository (`Virat1315/ats-resume-auditor`).
4. Add the Environment Variable in Vercel:
   - `GEMINI_API_KEY`: Your Google Gemini API Key.
5. Click **Deploy**.

---

## 💻 Running Locally (Streamlit)

```bash
pip install -r requirements.txt
streamlit run app.py
```
