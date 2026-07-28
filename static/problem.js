// ── Boilerplates ──────────────────────────────────────────────────────
const BOILERPLATES = {
    cpp: `#include <bits/stdc++.h>
using namespace std;
using ll = long long;

void solve(){
    
}

int main(){
    ios::sync_with_stdio(0);
    cin.tie(nullptr);
    int t = 1;
    cin >> t;
    while(t--) solve();
}`,
    python: `import sys
input = sys.stdin.readline

def solve():
    pass

t = int(input())
for _ in range(t):
    solve()`,
    java: `import java.util.*;
import java.io.*;

public class Main {
    static BufferedReader br = new BufferedReader(new InputStreamReader(System.in));
    
    static void solve() throws IOException {
        
    }
    
    public static void main(String[] args) throws IOException {
        int t = Integer.parseInt(br.readLine().trim());
        while(t-- > 0) solve();
    }
}`
};

const LANG_MAP = { cpp: 'cpp', python: 'python', java: 'java' };

let currentLang = 'cpp';
let editor = null;

// ── Monaco init ───────────────────────────────────────────────────────
require(["vs/editor/editor.main"], function () {
    editor = monaco.editor.create(document.getElementById("monaco-editor"), {
        value: BOILERPLATES.cpp,
        language: "cpp",
        theme: "vs-dark",
        automaticLayout: true,
        fontSize: 14,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        suggestOnTriggerCharacters: true,
        quickSuggestions: true,
        lineNumbers: "on",
        padding: { top: 12 }
    });
});

// ── Language switcher ─────────────────────────────────────────────────
function changeLanguage(lang) {
    currentLang = lang;
    if (!editor) return;
    const model = editor.getModel();
    monaco.editor.setModelLanguage(model, LANG_MAP[lang]);
    editor.setValue(BOILERPLATES[lang]);
}

// ── Run code ──────────────────────────────────────────────────────────
async function runCode() {
    const btn = document.getElementById('run-btn');
    btn.textContent = '⏳ Running...';
    btn.disabled = true;

    const code = editor ? editor.getValue() : '';
    const input = document.getElementById('run-input').value;

    try {
        const res = await fetch('/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, input })
        });
        const data = await res.json();
        document.getElementById('run-output').textContent = data.output || '(no output)';
    } catch (e) {
        document.getElementById('run-output').textContent = 'Error: could not connect to server';
    } finally {
        btn.textContent = '▶ Run';
        btn.disabled = false;
    }
}

// ── AI assistant ──────────────────────────────────────────────────────
async function askAI(mode) {
    const code = editor ? editor.getValue() : '';
    const customText = document.getElementById('ai-input').value.trim();
    const messages = document.getElementById('ai-messages');

    // add user bubble
    const userText = mode === 'hint' ? '💡 Give me a hint'
                   : mode === 'solution' ? '🔍 Show the solution'
                   : customText;
    if (!userText) return;

    messages.innerHTML += `<div class="ai-msg user-msg">${escapeHtml(userText)}</div>`;
    document.getElementById('ai-input').value = '';

    // thinking indicator
    const thinkId = 'think-' + Date.now();
    messages.innerHTML += `<div class="ai-msg bot-msg thinking" id="${thinkId}">...</div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        const res = await fetch('/ai-help', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                problem_name: PROBLEM_NAME,
                problem_html: '',
                code: code,
                mode: mode === 'custom' ? 'hint' : mode,
                custom_question: customText
            })
        });
        const data = await res.json();
        document.getElementById(thinkId).classList.remove('thinking');
        document.getElementById(thinkId).innerHTML = formatAIResponse(data.response);
    } catch (e) {
        document.getElementById(thinkId).textContent = 'Error connecting to AI.';
    }
    messages.scrollTop = messages.scrollHeight;
}

function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function formatAIResponse(text) {
    // simple markdown-ish: wrap code blocks
    return text
        .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

// ── Resizable panels ──────────────────────────────────────────────────
function makeResizable(resizerId, leftId, rightId) {
    const resizer = document.getElementById(resizerId);
    const left    = document.getElementById(leftId);
    const right   = document.getElementById(rightId);
    let dragging = false, startX = 0, startLeft = 0, startRight = 0;

    resizer.addEventListener('mousedown', e => {
        dragging = true;
        startX = e.clientX;
        startLeft  = left.getBoundingClientRect().width;
        startRight = right.getBoundingClientRect().width;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });

    document.addEventListener('mousemove', e => {
        if (!dragging) return;
        const dx = e.clientX - startX;
        const newLeft  = Math.max(180, startLeft + dx);
        const newRight = Math.max(180, startRight - dx);
        left.style.flex  = 'none';
        right.style.flex = 'none';
        left.style.width  = newLeft  + 'px';
        right.style.width = newRight + 'px';
    });

    document.addEventListener('mouseup', () => {
        dragging = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    });
}

makeResizable('resizer-1', 'panel-problem', 'panel-editor');
makeResizable('resizer-2', 'panel-editor', 'panel-ai');

// ── Keyboard shortcut: Ctrl+Enter to run ─────────────────────────────
document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') runCode();
});