
Agentic AI Planner - Streamlit app
=================================

Files:
- agentic_planner_app.py : The Streamlit single-file app.

Requirements:
- Python 3.8+
- pip install streamlit openai reportlab

Run locally:
1. (Optional) Set your OpenAI API key:
   export OPENAI_API_KEY="sk-..."
   or configure Streamlit secrets.

2. Run:
   streamlit run agentic_planner_app.py

Notes:
- If OpenAI key is not set or the API call fails, the app will use a fallback plan generator.
- The app supports PDF download using reportlab (no external wkhtmltopdf required).
