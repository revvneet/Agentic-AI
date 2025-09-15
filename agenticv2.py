"""
Agentic AI Planner - Streamlit app with Checkboxes for Weekly Tasks
Features:
- Input: goal, timeframe (weeks), mentor style
- AI-driven plan generation via OpenAI (with fallback)
- Weekly plan displayed as checkboxes
- Progress bar dynamically updates based on completed tasks
- XP / Emoji Progress Tree
- Flashcards generation
- Download plan as PDF / JSON
Instructions:
- Install: pip install streamlit openai reportlab
- Run: streamlit run agentic_planner_app.py
"""

import streamlit as st
import os
import json
import random
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# ------------------ Helper Functions ------------------ #

def get_openai_api_key():
    key = None
    try:
        key = st.secrets["OPENAI_API_KEY"]
    except:
        key = os.environ.get("OPENAI_API_KEY")
    return key

def call_openai_for_plan(goal, weeks, mentor_style):
    api_key = get_openai_api_key()
    prompt = f"""
You are an expert study planner and mentor with the persona: {mentor_style}.
User goal: "{goal}". Timeframe: {weeks} weeks.
Output a JSON with keys:
- milestones: [..]
- weeks: {{ "Week 1": {{ "Tasks":[..], "Resources":[..], "Reflection": "...", "Mentor_Tip": "..." }}, ... }}
- mentor_notes: "..."
Return only valid JSON. Keep resources short (title or url if relevant).
"""
    if not api_key:
        return fallback_plan(goal, weeks, mentor_style)

    try:
        import openai
        openai.api_key = api_key
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role":"system", "content": "You are a helpful planning assistant that returns valid JSON."},
                {"role":"user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=900
        )
        text = response["choices"][0]["message"]["content"].strip()
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            text = text[start:end+1]
        plan_json = json.loads(text)
        return plan_json
    except Exception as e:
        st.warning(f"OpenAI call failed or returned invalid JSON. Using fallback plan. ({str(e)})")
        return fallback_plan(goal, weeks, mentor_style)

def fallback_plan(goal, weeks, mentor_style):
    weeks = int(max(1, weeks))
    milestones = []
    milestones_templates = ["Foundation", "Core Skills", "Practice & Projects", "Final Project"]
    for i in range(min(4, weeks)):
        milestones.append(f"{milestones_templates[i]} - Week {i+1}")
    if weeks > 4:
        milestones.append("Polish & Review")

    weeks_dict = {}
    for w in range(1, weeks+1):
        tasks = [
            f"{mentor_style} Task: Spend focused 60-90 minutes on a core topic (week {w})",
            f"Practice: 30 minutes of hands-on exercises (week {w})",
        ]
        resources = ["Official docs / Quick YouTube tutorial", "A short project or code-along"]
        reflection = "What was the biggest challenge this week and one action to fix it?"
        tip = random.choice([
            "Consistency beats intensity. Try daily small steps.",
            "Break tasks into 25-minute Pomodoro sprints.",
            "Google errors, read docs, then refactor."
        ])
        weeks_dict[f"Week {w}"] = {
            "Tasks": tasks,
            "Resources": resources,
            "Reflection": reflection,
            "Mentor_Tip": tip
        }

    mentor_notes = f"As {mentor_style}, I'll push you to be consistent. Goal: {goal} in {weeks} weeks."

    return {"milestones": milestones, "weeks": weeks_dict, "mentor_notes": mentor_notes}

def recompress_plan(plan_json, original_weeks, remaining_weeks):
    weeks_keys = list(plan_json.get("weeks", {}).keys())
    all_tasks = []
    all_resources = []
    for k in weeks_keys:
        entry = plan_json["weeks"][k]
        all_tasks.extend(entry.get("Tasks", []))
        all_resources.extend(entry.get("Resources", []))
    rem = max(1, int(remaining_weeks))
    new_weeks = {}
    t_per_week = max(1, len(all_tasks)//rem)
    for i in range(rem):
        slice_tasks = all_tasks[i*t_per_week:(i+1)*t_per_week]
        if not slice_tasks:
            slice_tasks = ["Catch-up session: review core concepts"]
        new_weeks[f"Week {i+1}"] = {
            "Tasks": slice_tasks,
            "Resources": all_resources[i*t_per_week:(i+1)*t_per_week] if all_resources else ["Docs"],
            "Reflection": "What will you prioritize next week?",
            "Mentor_Tip": "Focus on the highest-impact tasks first."
        }
    plan_json["weeks"] = new_weeks
    return plan_json

def generate_flashcards(plan_json, current_week=1):
    week_key = f"Week {current_week}"
    entry = plan_json.get("weeks", {}).get(week_key, {})
    cards = []
    tasks = entry.get("Tasks", [])
    for i, t in enumerate(tasks[:5], start=1):
        q = f"What is the key action for: {t.split(':')[0][:60]}?"
        a = f"Do: {t}"
        cards.append({"q": q, "a": a})
    return cards

def create_pdf_bytes(plan_json, title="Agentic Plan"):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    margin = 40
    y = height - margin
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, title)
    y -= 30
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    y -= 25
    # Milestones
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Milestones:")
    y -= 18
    c.setFont("Helvetica", 11)
    for m in plan_json.get("milestones", []):
        c.drawString(margin+10, y, f"- {m}")
        y -= 14
        if y < 60:
            c.showPage()
            y = height - margin
    y -= 8
    # Weeks
    for wk, content in plan_json.get("weeks", {}).items():
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, wk)
        y -= 16
        c.setFont("Helvetica", 11)
        for t in content.get("Tasks", []):
            c.drawString(margin+8, y, f"• {t}")
            y -= 12
            if y < 60:
                c.showPage()
                y = height - margin
        res = content.get("Resources", [])
        if res:
            c.drawString(margin+8, y, "Resources: " + ", ".join(res[:3]))
            y -= 14
        refl = content.get("Reflection", "")
        tip = content.get("Mentor_Tip", "")
        if refl:
            c.drawString(margin+8, y, "Reflection: " + refl)
            y -= 12
        if tip:
            c.drawString(margin+8, y, "Tip: " + tip)
            y -= 18
        if y < 80:
            c.showPage()
            y = height - margin
    # Mentor notes
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Mentor Notes:")
    y -= 16
    c.setFont("Helvetica", 11)
    for line in plan_json.get("mentor_notes", "").split("\n"):
        c.drawString(margin+8, y, line)
        y -= 12
        if y < 60:
            c.showPage()
            y = height - margin
    c.save()
    buffer.seek(0)
    return buffer

# ------------------ Streamlit UI ------------------ #

st.set_page_config(page_title="Agentic AI Planner", layout="centered")
st.title("Agentic AI Planner 🌱")
st.markdown("Turn big goals into an actionable, adaptive weekly plan — powered by AI.")

# Input form
with st.form("input_form"):
    goal = st.text_input("Enter your goal (e.g., 'Learn Django and deploy a small app')", max_chars=200)
    weeks = st.number_input("Timeframe (weeks)", min_value=1, max_value=52, value=4)
    mentor_style = st.selectbox("Choose your mentor style", ["Coach (tough-love)", "Zen Monk (calm)", "Tech Bro (hype)"])
    submitted = st.form_submit_button("Generate Plan")

# Session state initialization
if "plan" not in st.session_state: st.session_state.plan = None
if "xp" not in st.session_state: st.session_state.xp = 0
if "percent" not in st.session_state: st.session_state.percent = 0
if "current_week" not in st.session_state: st.session_state.current_week = 1
if "tasks_checked" not in st.session_state: st.session_state.tasks_checked = {}

# Generate plan
if submitted:
    if not goal.strip():
        st.error("Please enter a goal to generate a plan.")
    else:
        with st.spinner("Generating plan with AI..."):
            plan = call_openai_for_plan(goal, weeks, mentor_style)
            st.session_state.plan = plan
            st.session_state.percent = 0
            st.session_state.current_week = 1
            st.session_state.tasks_checked = {}  # reset tasks
        st.success("Plan generated! Scroll down to view.")

# Show Milestones
if st.session_state.plan:
    plan = st.session_state.plan
    st.subheader("Milestones")
    for m in plan.get("milestones", []):
        st.write("• " + m)

    st.subheader("Weekly Plan with Checkboxes")
    total_tasks = 0
    completed_tasks = 0
    for wk, content in plan.get("weeks", {}).items():
        with st.expander(wk):
            st.markdown("**Tasks:**")
            for t in content.get("Tasks", []):
                key = f"{wk}_{t}"
                checked = st.checkbox(t, key=key, value=st.session_state.tasks_checked.get(key, False))
                st.session_state.tasks_checked[key] = checked
                total_tasks += 1
                if checked: completed_tasks += 1

            st.markdown("**Resources:**")
            for r in content.get("Resources", []):
                st.write("- " + r)
            st.markdown("**Reflection prompt:**")
            st.write(content.get("Reflection", ""))
            st.markdown("**Mentor tip:**")
            st.write(content.get("Mentor_Tip", ""))

    # Update progress based on tasks checked
    if total_tasks > 0:
        st.session_state.percent = int(completed_tasks/total_tasks*100)

# Show Mentor Notes
if st.session_state.plan:
    st.subheader("Mentor Notes")
    st.info(st.session_state.plan.get("mentor_notes", ""))

# Progress panel
st.subheader("Progress")
st.progress(st.session_state.percent)

def emoji_tree(p):
    if p < 10: return "🌱"
    if p < 40: return "🌱🌿"
    if p < 70: return "🌱🌿🌳"
    return "🌱🌿🌳🌲"

st.markdown("**Progress Tree:** " + emoji_tree(st.session_state.percent))
st.metric("XP", st.session_state.percent*10)

# Flashcards
if st.session_state.plan:
    if st.button("Generate Flashcards for Current Week"):
        cards = generate_flashcards(st.session_state.plan, st.session_state.current_week)
        st.subheader(f"Flashcards - Week {st.session_state.current_week}")
        for i, c in enumerate(cards, start=1):
            st.markdown(f"**Q{i}.** {c['q']}")
            st.write(f"**A{i}.** {c['a']}")

# Download Plan
if st.session_state.plan:
    pdf_bytes = create_pdf_bytes(st.session_state.plan, title=f"Plan: {goal[:60]}")
    st.download_button(label="Download Plan as PDF", data=pdf_bytes, file_name="agentic_plan.pdf", mime="application/pdf")
    st.download_button(label="Download Plan (JSON)", data=json.dumps(st.session_state.plan, indent=2), file_name="agentic_plan.json", mime="application/json")

st.markdown("---")
st.caption("Built with Streamlit + OpenAI. Progress bar now dynamically updates as you check off tasks.")