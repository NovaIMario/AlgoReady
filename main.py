import subprocess
import tempfile
import time
import os
from contextlib import asynccontextmanager
from bs4 import BeautifulSoup
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from google import genai
from dotenv import load_dotenv


load_dotenv() 
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

@app.get("/problem")
def get_problem(request: Request, contestId: str, index: str, name: str, rating: str):
    url = f"https://codeforces.com/problemset/problem/{contestId}/{index}"
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9"
    })
    session.get("https://codeforces.com")
    try:
        
        response = session.get(url)
        print("URL fetched:", url)
        print("Status code:", response.status_code)
        print("Final URL after redirects:", response.url)
        print("HTML length:", len(response.text))
        print(response.text[:500])
        soup = BeautifulSoup(response.text, "html.parser")
        statement = soup.find("div", class_="problem-statement")
        if statement:
            for div in statement.find_all("div", class_=[
                "input-specification", "output-specification",
                "note", "sample-tests"
            ]):
                div.decompose()
            problem_html = str(statement)
        else:
            problem_html = "<p>Could not load problem text.</p>"
    except Exception as e:
        print(f"Failed {contestId}{index}: {e}")
        problem_html = "<p>Error loading problem.</p>"

    return templates.TemplateResponse(
        request=request,
        name="problem.html",
        context={
            "contestId": contestId,
            "index": index,
            "name": name,
            "rating": rating,
            "problem_html": problem_html
        }
    )

@app.get("/problems")
def get_problems(name: str = None, rating: int = None, tag: str = None):
    start = time.time()
    # brute force — fetches from API every time (to be optimised later)
    response = requests.get("https://codeforces.com/api/problemset.problems?lang=en")
    data = response.json()
    problems = data["result"]["problems"]
    filtered = problems[::]
    if rating:
        filtered = [p for p in filtered if p.get("rating") == rating]
    if tag:
        filtered = [p for p in filtered if tag in p.get("tags", [])]
    if name:
        filtered = [p for p in filtered if name.lower() in p.get("name", "").lower()]
    end = (time.time() - start) * 1000
    print(f"Search took {end:.2f}ms")
    return filtered

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
    mode: str  # "hint" or "solution"

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
    else:
        prompt = f"""You are a competitive programming coach.
The user is solving: {req.problem_name}

Their current code:
{req.code}

Explain the optimal solution approach and provide a clean C++ solution with comments."""

    try:
        response = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )
        return {"response": response.output_text}
    except Exception as e:
        return {"response": f"Error: {str(e)}"}