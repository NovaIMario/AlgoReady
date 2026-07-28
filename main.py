import subprocess
import tempfile
import time
import os
from contextlib import asynccontextmanager
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from google import genai
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import re
from markupsafe import escape

def format_cf_text(text: str) -> str:
    if not text:
        return ""

    # Convert CF's $$$...$$$ into MathJax-compatible \( ... \)
    text = re.sub(r'\$\$\$(.+?)\$\$\$', r'\\(\1\\)', text)

    # Insert a newline after sentence-ending periods, but not
    # inside numbers like 3.14 or 1.5
    text = re.sub(r'(?<!\d)\.(?!\d)', '.\n', text)

    return text

def render_cf_text(text: str) -> str:
    """Escape HTML then convert our inserted \n into <br> for display."""
    formatted = format_cf_text(text)
    return str(escape(formatted)).replace("\n", "<br>\n")


load_dotenv() 

engine = create_engine(os.getenv("DATABASE_URL"), connect_args={"sslmode": "require"})
api_key = os.environ.get("GEMINI_API_KEY")
client = None

CF_TAGS = []
NAMES = []
RATINGS = []
problems_cache = []
@asynccontextmanager
async def lifespan(app: FastAPI):
    global NAMES, CF_TAGS, RATINGS, problems_cache, client
    response = requests.get("https://codeforces.com/api/problemset.problems?lang=en")
    data = response.json()
    problems_cache = data["result"]["problems"]
    NAMES = [p["name"] for p in problems_cache]
    CF_TAGS = sorted({t for p in problems_cache for t in p.get("tags", [])})
    RATINGS = sorted({p.get("rating") for p in problems_cache if p.get("rating") is not None})
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        client = genai.Client()
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"cf_tags": CF_TAGS, "names": NAMES, "ratings": RATINGS}
    )

from sqlalchemy import text

@app.get("/problem")
def get_problem(request: Request, contestId: str, index: str, name: str, rating: str):
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT statement, input_spec, output_spec, note, examples
                FROM problems
                WHERE contest_id = :cid AND problem_index = :idx
            """),
            {"cid": contestId, "idx": index}
        ).fetchone()

    if not row:
        return templates.TemplateResponse(
            request=request,
            name="problem.html",
            context={"problem_html": "<p>Could not load problem text.</p>"}
        )

    return templates.TemplateResponse(
        request=request,
        name="problem.html",
        context={ 
            "name": name,
            "problem_html": render_cf_text(row.statement),
            "input_spec_html": render_cf_text(row.input_spec),
            "output_spec_html": render_cf_text(row.output_spec),
            "note_html": render_cf_text(row.note),
            "examples": row.examples,
            "rating": rating,
            "contestId": contestId,
            "index": index,
        }
    )

@app.get("/problems")
def get_problems(name: str = None, rating: int = None, tag: str = None):
    start = time.time()

    query = """
        SELECT contest_id, problem_index, name, rating, tags
        FROM problems
        WHERE 1=1
    """
    params = {}

    if name:
        query += " AND name ILIKE :name"
        params["name"] = f"%{name}%"

    if rating:
        query += " AND rating = :rating"
        params["rating"] = rating

    if tag:
        query += " AND :tag = ANY(tags)"
        params["tag"] = tag

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).fetchall()

    end = (time.time() - start) * 1000
    print(f"Search took {end:.2f}ms")

    return [
        {
            "contestId": r.contest_id,
            "index": r.problem_index,
            "name": r.name,
            "rating": r.rating,
            "tags": r.tags,
        }
        for r in rows
    ]


class RunRequest(BaseModel):
    code: str
    input: str

@app.post("/run")
def run_code(req: RunRequest):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".cpp", mode="w") as f:
        f.write(req.code)
        cpp_path = f.name
    exe_path = cpp_path.replace(".cpp", "")
    compile_proc = subprocess.run(
        ["g++", cpp_path, "-o", exe_path],
        capture_output=True, text=True
    )
    if compile_proc.returncode != 0:
        return {"output": compile_proc.stderr}
    try:
        run_proc = subprocess.run(
            [exe_path],
            input=req.input,
            capture_output=True, text=True,
            timeout=2
        )
        return {"output": run_proc.stdout or run_proc.stderr}
    except subprocess.TimeoutExpired:
        return {"output": "Time limit exceeded (2s)"}

class HintRequest(BaseModel):
    problem_name: str
    problem_html: str
    code: str
    mode: str  # "hint" or "solution" or "any"
    custom_question: str
    contest_id: str
    problem_index: str

def get_editorial_for_problem(contest_id: int, problem_index: str) -> str | None:
    with engine.connect() as conn:
        result = conn.execute(
            text("""
            SELECT editorial_text FROM problems
            WHERE contest_id = :contest_id AND problem_index = :problem_index
            """),
            {"contest_id": contest_id, "problem_index": problem_index},
        )
        row = result.fetchone()
        return row[0] if row and row[0] else None

@app.post("/ai-help")
def ai_help(req: HintRequest):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return {"response": "Gemini API key not configured."}
    
    if req.mode == "hint":
        prompt = f"""You are a competitive programming coach. 
The user is solving: {req.problem_name}

Their current code:
{req.code}

Give a helpful HINT only — do not reveal the full solution or algorithm directly.
Point them in the right direction with 2-3 sentences maximum."""
    elif req.mode == "solution":
        # Fetch the editorial for this problem from Supabase
        editorial_text = get_editorial_for_problem(req.contest_id, req.problem_index)

        editorial_block = (
            f"\n\nOfficial editorial for reference:\n{editorial_text}"
            if editorial_text
            else "\n\n(No official editorial is available for this problem.)"
        )

        prompt = f"""You are a competitive programming coach.
    The user is solving: {req.problem_name}

    Their current code:
    {req.code}
    {editorial_block}

    Explain the optimal solution approach and provide a clean C++ solution with comments."""

    try:
        response = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )
        return {"response": response.output_text}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}