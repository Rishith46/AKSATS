# AKSATS
ATS TOOL

## Resume parsing

Apply database migrations before running the backend:

```powershell
cd backend
alembic upgrade head
```

DOCX extraction includes body text, tables, headers, and footers. Legacy `.doc` files
require Microsoft Word on Windows, or LibreOffice/antiword as an available converter.
Digitally generated PDFs are read as text; scanned/image-only PDFs require OCR, which is
not currently bundled.
The parser structures contact/recruiting fields, work history, education, certifications,
and skills listed in a resume's skills section. New catalog skills are marked for review.
It keeps and displays all extracted text on the candidate document so information that
doesn't fit a structured field remains available for review. Use **Parse again** on a resume
to apply parser improvements to an existing upload. Structured fields remain best-effort,
so verify them against the original resume and extracted text.
From a candidate profile, preview the original PDF or download another original resume file.
Use **Edit candidate** to update verified work history, skills, skill evidence, and dates; skill
evidence and dates are also shown in job-match details. Exporting an ATS-managed DOCX or PDF
creates a separate file from the saved profile and never replaces the uploaded resume.

## Importing resumes from Gmail

The inbox worker can poll a Gmail mailbox and stage supported PDF, DOC, and DOCX attachments
from recent inbox messages. Attachments are checked against their actual file format and
resume/application context before they enter the same inbox processing pipeline as manual
uploads. The worker then creates a candidate, parses the resume, and records the result in
Resume Inbox. Identical files and already-scanned Gmail messages are not imported again.
Gmail messages are read-only; the integration does not mark messages read, move, or delete
them. The default lookback is 30 days and the default polling interval is 60 seconds.

To enable it:

1. In Google Cloud, enable the Gmail API and create OAuth client credentials for the mailbox
   `jobs@allknownservices.com`. Use the read-only Gmail scope
   `https://www.googleapis.com/auth/gmail.readonly` and obtain an OAuth refresh token for
   that mailbox. Do not use the mailbox password or commit OAuth secrets.
2. Set these variables in the repository-root `.env` file, which is read by the backend:

   ```dotenv
   GMAIL_CLIENT_ID=your-oauth-client-id
   GMAIL_CLIENT_SECRET=your-oauth-client-secret
   GMAIL_REFRESH_TOKEN=your-refresh-token
   GMAIL_POLL_SECONDS=60
   GMAIL_LOOKBACK_DAYS=30
   ```

3. Apply migrations with `alembic upgrade head` from `backend`, then restart the backend.
   The Resume Inbox shows whether Gmail polling is configured and labels email-sourced
   resumes separately from manual uploads.

Only attachments included in the email can be imported. If LinkedIn sends an application
notification containing a link instead of the resume file, this integration will not fetch
the linked resume. Gmail OAuth access also depends on the Google Cloud project's consent
screen and token settings; a refresh token may need to be reauthorized if Google expires it.

## Creating jobs from a description

On the New job form, paste a job description and choose **Fill fields from JD** to draft
the title, location, work mode, experience, rate, skills, and any recognized visa types.
Review and edit the populated fields before saving; the pasted text is kept as the job
description. Visa requirements use the same canonical multi-select options as candidates.

The skill matcher reads the current database catalog for every JD parse. Seed the curated
IT, non-IT, and legal starter vocabulary (543 canonical entries plus aliases) with:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe scripts\seed_skills_catalog.py
```

The seed is additive and safe to rerun. ATS reset clears candidates and jobs but keeps this
shared skill catalog and its aliases.

## Deleting ATS records

Users with `candidate.delete` can permanently delete a candidate and related resume files
and submission records. Users with `job.delete` can permanently delete a job and its
related submissions and interviews. Both actions require confirmation in the UI.

The Candidates screen has separate **Candidates** and **Archived** views. Users with
`candidate.archive` can move a candidate to Archived and restore them later. Users with
`candidate.edit` can open Modify directly from a candidate row, and users with
`candidate.delete` can permanently delete a candidate.

## Candidate recruiting statuses

Users with `candidate.edit` can update a candidate's recruiting status from the Candidates
list: Open, Vendor Submission, Client Submission, Vendor Interview Scheduled, Client Interview
Scheduled, or Rejected. Each actual status change automatically adds a note with the previous
and new status, the acting user's name and email, and the UTC change timestamp. Choosing the
current status again does not add a duplicate note.

## Team and guest accounts

After applying migrations, seed role permissions (safe to rerun) and create a guest account
with its own email and password:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m scripts.seed
.\.venv\Scripts\python.exe -m scripts.create_user guest@allknownservices.com "Guest User" guest
```

The script prompts for a password and stores only its Argon2 hash. Share the credentials
privately. A guest can use candidate, resume, jobs, matching, skills, notes, and submission
features, but cannot permanently delete candidates/jobs, manage users, view the audit log,
or run the full ATS reset. Use a distinct guest login; do not change an existing team
account's role.

## Admin dashboard

Users with the `user.manage` permission can open the Dashboard tab to see active candidate and
open-job totals, candidate and resume-parse status breakdowns, active candidates added per month,
successfully parsed resumes by email versus manual drag-and-drop upload, job roles created per
month, and inbox items awaiting processing or review. Candidate totals and breakdowns exclude
archived and merged records; deleted records are not present. Monthly charts cover the latest 12
months; failed, duplicate, and review-needed inbox rows are not counted as successfully parsed
resumes. The `ats.reset` permission is assigned only to
`vamshi@allknownservices.com`; run `python -m scripts.seed` and then
`python -m scripts.equalize_team` to apply the team access configuration.

## Remote access for the team

The app's default configuration is local-only. A teammate at home cannot access your
`localhost` services. For a small team, use a private VPN such as Tailscale on the office
computer and the remote device; do not expose the database or forward the app's ports
directly to the public internet. Keep the office computer on and connected while it is
being used as the host.

For VPN access, configure the frontend API URL at build time as the office computer's
private VPN address and allow the frontend's exact private URL in the backend CORS list:

```dotenv
# Repository-root .env (backend)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://OFFICE-TAILSCALE-IP:3000
```

```dotenv
# frontend/.env.local (replace with the office computer's private VPN address)
NEXT_PUBLIC_API_URL=http://OFFICE-TAILSCALE-IP:8000
```

After installing Tailscale and connecting both devices to the same private tailnet, start
the services on the office computer:

```powershell
# Backend, from backend\
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend, from frontend\
npm.cmd run build
npm.cmd run start -- --hostname 0.0.0.0 --port 3000
```

In Windows Firewall, allow ports 3000 and 8000 only for the private Tailscale network; do
not create public router port-forwarding rules. Vamshi can then visit
`http://OFFICE-TAILSCALE-IP:3000` while connected to the same tailnet and sign in with his
own account. The frontend must be rebuilt after changing `NEXT_PUBLIC_API_URL`. Keep the
office computer awake and the backend/frontend running during remote use. For long-term
business use, prefer hosting behind HTTPS with managed backups and access controls rather
than relying on an office workstation.
