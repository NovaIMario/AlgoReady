require(["vs/editor/editor.main"], function () {
    window.editor = monaco.editor.create(document.getElementById("editor"), {
    value: `#include <bits/stdc++.h>
using namespace std;
using ll = long long;

void solve(){

}
int main(){
    freopen("input.txt", "r", stdin);
    ios::sync_with_stdio(0);
    cin.tie(nullptr);
    int t=1;
    cin>>t;
    while(t--)solve();
}`,
    language: "cpp",
    theme: "vs-dark",
    automaticLayout: true,
    suggestOnTriggerCharacters: false,
    quickSuggestions: false
});

});
document.getElementById("run-btn").onclick = () => {
    const code = window.editor.getValue();
    const input = document.getElementById("run-input").value;

    document.getElementById("run-btn").onclick = async () => {
    const code = window.editor.getValue();
    const input = document.getElementById("run-input").value;

    const res = await fetch("/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, input })
    });

    const data = await res.json();
    document.getElementById("run-output").textContent = data.output;
};

};
