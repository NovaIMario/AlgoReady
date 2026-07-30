# AlgoReady

A full-stack competitive programming platform for browsing, searching, and solving problems — with an in-browser code editor, AI-powered hints, and live difficulty predictions for unrated problems.

**Live demo:** https://algoready-yqza.onrender.com/
**Repo:** https://github.com/NovaIMario/AlgoReady

---

## Features

- **Problem search** over an 10K+ problem corpus, powered by a Trie-based prefix search (`O(k)` lookup vs. the original `O(n)` linear scan — a ~180x reduction in average query latency, from 0.36ms to 0.002ms).
- **In-browser code editor** (Monaco Editor) supporting C++, Python, and Java, with server-side execution via a sandboxed subprocess and a 2-second timeout to prevent runaway code.
- **AI assistant** powered by the Gemini API, providing contextual hints and solution walkthroughs for the problem currently open.
- **Resizable three-panel workspace**: problem statement, code editor, and AI chat side by side, with UX inspired by platforms like LeetCode and Codeforces.
- **Provisional difficulty ratings** for problems Codeforces hasn't officially rated yet, sourced live from the companion service [CFSeer](https://github.com/NovaIMario/CFSeer) via a cross-origin API call.

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL (Supabase)
- **Frontend:** JavaScript, Monaco Editor
- **AI:** Gemini API
- **CI/CD:** GitHub Actions — runs import checks and live smoke tests against deployed endpoints on every push
- **Deployment:** Render

## Architecture Notes

- FastAPI's `lifespan` context is used to preload and cache problem metadata at startup, avoiding cold-start API calls on the first request.
- Environment-based configuration keeps API keys and the database connection string out of source control.
- The rating-prediction path calls out to CFSeer's `/predict-rating` endpoint; if CFSeer has no official tags for a problem, it falls back to predicting tags from the statement text before estimating a rating.

## Local Setup

```bash
git clone https://github.com/NovaIMario/AlgoReady.git
cd AlgoReady
pip install -r requirements.txt
```

Create a `.env` file with:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>
GEMINI_API_KEY=<your-key>
```

Run locally:

```bash
uvicorn main:app --reload
```

## CI/CD

Every push and pull request triggers a GitHub Actions workflow that:
1. Installs dependencies
2. Runs an import check against `main.py`
3. Starts the server and smoke-tests key endpoints (`/`, `/problems`) against the live deployment

This catches integration failures (missing env vars, broken imports, dependency issues) before they reach production.
