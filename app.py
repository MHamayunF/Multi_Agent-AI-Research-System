import re
import time
import streamlit as st

from pipeline import stream_research_pipeline

st.set_page_config(page_title="Research Lab", page_icon="🔎", layout="wide")

STEPS = [
    ("search", "🔍", "Search", "Finds sources"),
    ("reader", "📖", "Read", "Scrapes best page"),
    ("writer", "✍️", "Write", "Drafts the report"),
    ("critic", "🧐", "Critique", "Scores quality"),
]
EXAMPLES = [
    "Future of solar energy in Pakistan",
    "How do AI agents work?",
    "Impact of remote work on productivity",
]

# ---------- styling ----------
st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {background: radial-gradient(1200px 600px at 10% -10%, #1b1448 0%, transparent 60%),
        radial-gradient(900px 500px at 100% 0%, #0e2a47 0%, transparent 55%), #0a0e1a;}
.block-container {padding-top: 2rem; max-width: 1100px;}
.hero {text-align:center; padding: 1.2rem 0 0.4rem;}
.hero h1 {font-size: 3rem; font-weight: 800; margin: 0; letter-spacing: -1px;}
.hero h1 span {background: linear-gradient(90deg,#8b5cf6,#22d3ee); -webkit-background-clip:text;
        -webkit-text-fill-color: transparent;}
.hero p {color:#8b93b0; font-size:1.05rem; margin-top:.4rem;}
.steps {display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin: 1.2rem 0;}
.step {background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:16px;
        padding:16px; text-align:center; transition:.3s; backdrop-filter: blur(6px);}
.step .ic {font-size:1.8rem;} .step .nm {font-weight:700; margin-top:4px;}
.step .ds {color:#8b93b0; font-size:.8rem;} .step .bd {margin-top:10px; font-size:.78rem; font-weight:600;
        padding:3px 10px; border-radius:99px; display:inline-block; background:rgba(255,255,255,.06); color:#8b93b0;}
.step.running {border-color:#8b5cf6; box-shadow:0 0 24px rgba(139,92,246,.45); animation:pulse 1.4s infinite;}
.step.running .bd {background:#8b5cf6; color:#fff;}
.step.done {border-color:rgba(52,211,153,.6);} .step.done .bd {background:rgba(52,211,153,.18); color:#34d399;}
.step.error {border-color:#f87171;} .step.error .bd {background:rgba(248,113,113,.2); color:#f87171;}
@keyframes pulse {0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)}}
.stat {background: rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); border-radius:16px;
        padding:16px; text-align:center; height:100%;}
.stat .v {font-size:1.9rem; font-weight:800;} .stat .l {color:#8b93b0; font-size:.8rem;}
.ring {--p:0; --c:#34d399; width:92px; height:92px; border-radius:50%; margin:0 auto; display:grid; place-items:center;
        background: conic-gradient(var(--c) calc(var(--p)*1%), rgba(255,255,255,.08) 0);}
.ring div {width:72px; height:72px; border-radius:50%; background:#111830; display:grid; place-items:center;
        font-weight:800; font-size:1.3rem;}
.chip {display:inline-block; margin:4px 6px 4px 0; padding:6px 12px; border-radius:99px; font-size:.82rem;
        background:rgba(139,92,246,.15); border:1px solid rgba(139,92,246,.4); color:#c4b5fd !important;
        text-decoration:none;}
.chip:hover {background:rgba(139,92,246,.35);}
.stButton>button {border-radius:12px;}
</style>
""", unsafe_allow_html=True)

# ---------- state ----------
st.session_state.setdefault("history", [])
st.session_state.setdefault("results", None)
st.session_state.setdefault("topic", "")


def set_topic(t):
    st.session_state.topic = t


def load_result(i):
    st.session_state.results = st.session_state.history[i]


def render_tracker(ph, status, times):
    cards = ""
    for key, icon, name, desc in STEPS:
        s = status.get(key, "pending")
        t = times.get(key)
        badge = {"pending": "Waiting", "running": "Working…", "error": "Failed",
                 "done": f"Done · {t:.1f}s" if t else "Done"}[s]
        cards += (f'<div class="step {s}"><div class="ic">{icon}</div><div class="nm">{name}</div>'
                  f'<div class="ds">{desc}</div><div class="bd">{badge}</div></div>')
    ph.markdown(f'<div class="steps">{cards}</div>', unsafe_allow_html=True)


def extract_score(feedback):
    m = re.search(r"Score:\s*(\d+(?:\.\d+)?)\s*/\s*10", feedback)
    return float(m.group(1)) if m else None


def extract_urls(text):
    urls = re.findall(r"https?://[^\s)\]>\"']+", text)
    seen, out = set(), []
    for u in (u.rstrip(".,;") for u in urls):
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def short_url(u):
    return re.sub(r"^https?://(www\.)?", "", u)[:48]


# ---------- sidebar ----------
with st.sidebar:
    st.markdown("### 🕘 History")
    if not st.session_state.history:
        st.caption("Your past research will show up here.")
    for i, h in enumerate(reversed(st.session_state.history)):
        idx = len(st.session_state.history) - 1 - i
        st.button(h["topic"][:34], key=f"h{idx}", on_click=load_result, args=(idx,), use_container_width=True)
    st.markdown("---")
    st.caption("Powered by Gemini + LangChain agents")

# ---------- hero + input ----------
st.markdown('<div class="hero"><h1>Multi-Agent <span>Research Lab</span></h1>'
            '<p>Four AI agents search, read, write and critique — so you don\'t have to.</p></div>',
            unsafe_allow_html=True)

c1, c2 = st.columns([5, 1])
c1.text_input("Topic", key="topic", placeholder="What do you want to research?", label_visibility="collapsed")
run = c2.button("🚀 Research", type="primary", use_container_width=True, disabled=not st.session_state.topic.strip())

cols = st.columns(len(EXAMPLES))
for col, ex in zip(cols, EXAMPLES):
    col.button(f"💡 {ex}", key=f"ex_{ex}", on_click=set_topic, args=(ex,), use_container_width=True)

tracker_ph = st.empty()
results = st.session_state.results
render_tracker(tracker_ph, {k: "done" for k, *_ in STEPS} if results else {}, results.get("times", {}) if results else {})

# ---------- run ----------
if run:
    topic = st.session_state.topic.strip()
    status, times, start, final = {}, {}, 0, None
    render_tracker(tracker_ph, status, times)
    try:
        for step, phase, state in stream_research_pipeline(topic):
            if phase == "start":
                status[step], start = "running", time.time()
            else:
                status[step], times[step] = "done", time.time() - start
            render_tracker(tracker_ph, status, times)
            final = state
        res = {**final, "topic": topic, "times": times}
        st.session_state.history.append(res)
        st.session_state.results = res
        st.toast("Research complete! 🎉")
        st.rerun()
    except Exception as e:
        for k, v in status.items():
            if v == "running":
                status[k] = "error"
        render_tracker(tracker_ph, status, times)
        st.error(f"Something went wrong: {e}")

# ---------- results ----------
if results:
    report, feedback = results["report"], results["feedback"]
    score = extract_score(feedback)
    urls = extract_urls(report) or extract_urls(results["search_results"])
    words = len(report.split())

    st.markdown(f"### 📌 {results['topic']}")
    a, b, c, d = st.columns(4)
    if score is not None:
        color = "#34d399" if score >= 8 else "#fbbf24" if score >= 6 else "#f87171"
        a.markdown(f'<div class="stat"><div class="ring" style="--p:{score*10};--c:{color}"><div>{score:g}</div></div>'
                   f'<div class="l" style="margin-top:8px">Critic score / 10</div></div>', unsafe_allow_html=True)
    else:
        a.markdown('<div class="stat"><div class="v">—</div><div class="l">Critic score</div></div>', unsafe_allow_html=True)
    b.markdown(f'<div class="stat"><div class="v">{words}</div><div class="l">Words</div></div>', unsafe_allow_html=True)
    c.markdown(f'<div class="stat"><div class="v">{max(1, round(words/200))} min</div><div class="l">Read time</div></div>', unsafe_allow_html=True)
    d.markdown(f'<div class="stat"><div class="v">{len(urls)}</div><div class="l">Sources</div></div>', unsafe_allow_html=True)

    st.write("")
    tabs = st.tabs(["📄 Report", "🧐 Critic", "🔗 Sources", "🛠️ Raw output"])
    with tabs[0]:
        st.markdown(report)
        st.download_button("⬇️ Download report (.md)", report,
                           file_name=f"{results['topic'][:40].replace(' ', '_')}_report.md", mime="text/markdown")
    with tabs[1]:
        st.markdown(feedback)
    with tabs[2]:
        if urls:
            st.markdown("".join(f'<a class="chip" href="{u}" target="_blank">{short_url(u)}</a>' for u in urls),
                        unsafe_allow_html=True)
        else:
            st.caption("No URLs found in the output.")
    with tabs[3]:
        with st.expander("Search agent output"):
            st.markdown(results["search_results"])
        with st.expander("Reader agent output"):
            st.markdown(results["scraped_content"])