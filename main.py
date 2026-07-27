import subprocess
import tempfile
import time
from contextlib import asynccontextmanager
from bs4 import BeautifulSoup
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import requests 
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

"""
{
  "contestId": 1234,
  "index": "A",
  "name": "Problem Name",
  "rating": 1200,
  "tags": ["dp", "graphs"]
}
"""

CF_TAGS = []
NAMES = []
RATINGS = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    global NAMES, CF_TAGS, RATINGS
    response = requests.get("https://codeforces.com/api/problemset.problems?lang=en")
    data = response.json()
    NAMES = [p["name"] for p in data["result"]["problems"]]
    CF_TAGS = sorted({t for p in data["result"]["problems"] for t in p.get("tags", [])})
    RATINGS = sorted({p.get("rating") for p in data["result"]["problems"] if p.get("rating") is not None})
    yield  


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name = "static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "index.html",
        context = {"cf_tags": CF_TAGS, "names": NAMES, "ratings": RATINGS}
    )

@app.get("/problem")
def get_problem(request: Request, contestId: str, index: str, name: str, rating: str):

    url = f"https://codeforces.com/contest/{contestId}/problem/{index}"
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    }
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    })
    try:
        response = session.get(url)
        print(url)
        print(response.status_code)
        soup = BeautifulSoup(response.text, "html.parser")

        statement = soup.find("div", class_="problem-statement")
        if statement:
            for div in statement.find_all("div", class_=[
                "input-specification",
                "output-specification",
                "note",
                "sample-tests"
            ]):
                div.decompose()

            problem_html = str(statement)
        else:
            problem_html = "<p>Could not load problem text.</p>"

    except Exception as e:
        print(f"Failed {contestId}{index}: {e}")
        problem_html = "<p>Error loading problem.</p>"

    return templates.TemplateResponse(
        request = request,
        name = "problem.html",
        context = {
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
    end = (time.time()-start) * 1000
    print(f"Search took {end:.2f}ms")
    return filtered

class RunRequest(BaseModel):
    code: str
    input: str

@app.post("/run")
def run_code(req: RunRequest):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".cpp") as f:
        f.write(req.code.encode())
        cpp_path = f.name

    exe_path = cpp_path.replace(".cpp", "")

    compile_proc = subprocess.run(
        ["g++", cpp_path, "-o", exe_path],
        capture_output=True,
        text=True
    )

    if compile_proc.returncode != 0:
        return {"output": compile_proc.stderr}

    run_proc = subprocess.run(
        [exe_path],
        input=req.input,
        capture_output=True,
        text=True,
        timeout=2
    )

    return {"output": run_proc.stdout or run_proc.stderr}
