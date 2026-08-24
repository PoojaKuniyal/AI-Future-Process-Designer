import os
import streamlit as st
import httpx
import pandas as pd
import time
from dotenv import load_dotenv

# Load env variables for local convenience
load_dotenv()

BACKEND_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")

# Set Page Config
st.set_page_config(
    page_title="AI Future Process Designer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    theme={"base": "dark"} 
)

# Custom Styling CSS for Sleek Dark Theme/Cards
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .main-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FF6B6B 0%, #4D96FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        font-size: 1.2rem;
        color: #888888;
        margin-bottom: 2rem;
    }
    
    .card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 20px;
    }
    
    .current-card {
        border-left: 5px solid #EF4444;
    }
    
    .future-card {
        border-left: 5px solid #10B981;
    }
    
    .evidence-card {
        border-left: 5px solid #3B82F6;
        background-color: #0F172A;
    }
    
    .problem-badge {
        background-color: #FEE2E2;
        color: #991B1B;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 9999px;
        display: inline-block;
        margin-top: 5px;
    }
    
    .decision-badge {
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 8px;
        border-radius: 9999px;
        display: inline-block;
        margin-top: 5px;
    }
    
    .badge-fully-automated { background-color: #D1FAE5; color: #065F46; }
    .badge-ai-assisted { background-color: #DBEAFE; color: #1E40AF; }
    .badge-human-in-the-loop { background-color: #FEF3C7; color: #92400E; }
    .badge-human-decision { background-color: #F3F4F6; color: #374151; }
    
    .url-link {
        color: #3B82F6;
        text-decoration: none;
        font-weight: 500;
    }
    .url-link:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---

def fetch_processes():
    try:
        response = httpx.get(f"{BACKEND_URL}/api/processes")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.sidebar.error(f"Cannot connect to backend API: {e}")
    return []


def fetch_process_detail(pid: str):
    try:
        response = httpx.get(f"{BACKEND_URL}/api/processes/{pid}")
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch details: {e}")
    return None


def run_transformation(industry: str, name: str):
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/processes/run",
            json={"industry": industry, "process_name": name},
            timeout=httpx.Timeout(600.0, connect=60.0)
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.json().get("detail", "Error executing agent workflow.")
    except Exception as e:
        return None, str(e)


def run_existing_transformation(pid: str):
    try:
        response = httpx.post(
            f"{BACKEND_URL}/api/processes/{pid}/transform", 
            timeout=httpx.Timeout(600.0, connect=60.0)
        )
        if response.status_code == 200:
            return response.json(), None
        else:
            return None, response.json().get("detail", "Error executing agent workflow.")
    except Exception as e:
        return None, str(e)


def get_search_config():
    try:
        response = httpx.get(f"{BACKEND_URL}/api/config/search")
        if response.status_code == 200:
            return response.json().get("search_provider", "tavily")
    except Exception:
        pass
    return "tavily"


def update_search_config(provider: str):
    try:
        httpx.post(f"{BACKEND_URL}/api/config/search", json={"search_provider": provider})
    except Exception:
        pass


# --- Sidebar UI ---
st.sidebar.markdown("### ⚙️ Control Panel")

# 1. Search Provider Choice
current_provider = get_search_config()
provider_idx = 0 if current_provider == "tavily" else 1
selected_provider = st.sidebar.radio(
    "Active Search Provider",
    ["Tavily", "Brave"],
    index=provider_idx,
    help="Select which search provider the Researcher Agent will invoke."
)
update_search_config(selected_provider.lower())

st.sidebar.markdown("---")

st.sidebar.markdown("---")

# 3. Process History Selection
st.sidebar.markdown("### 🕰️ Analysis History")
processes = fetch_processes()
if processes:
    process_options = {f"{p['industry']} - {p['name']} ({p['created_at'][:10]})": p['id'] for p in processes}
    selected_option = st.sidebar.selectbox("Load previous analysis", list(process_options.keys()))
    selected_process_id = process_options[selected_option]
else:
    st.sidebar.info("No past analyses found. Run a new one below or load the seed data!")
    selected_process_id = None


# --- Main Dashboard ---
st.markdown("<h1 class='main-title'>⚡ AI Future Process Designer</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Map standard procedures, trigger targeted technology research, synthesize evidence, and structure future-state process designs.</p>", unsafe_allow_html=True)

# Tabs
tab_run, tab_compare = st.tabs(["🚀 Run New Transformation", "📊 Current vs Future Comparison"])

# --- Tab 1: Run Transformation ---
with tab_run:
    st.markdown("### Initialize Operational Analysis")
    st.write("Input the industry and target process name. The agent workflow will map the current state, run queries, fetch evidence, and design the future state.")
    
    with st.form("agent_run_form"):
        col1, col2 = st.columns(2)
        with col1:
            industry_input = st.text_input("Industry", placeholder="e.g. Healthcare, Manufacturing, Retail")
        with col2:
            process_input = st.text_input("Business Process Name", placeholder="e.g. Patient Admissions, Quality Audit, Order Fulfillment")
            
        submit_btn = st.form_submit_with_clicks = st.form_submit_button("Start Transformation Agent 🚀")
        
    if submit_btn:
        if not industry_input or not process_input:
            st.error("Please fill in both Industry and Process Name.")
        else:
            with st.status("Invoking LangGraph Agents (takes 30-90s)...", expanded=True) as status:
                st.write("1. Initializing Process Discovery Node...")
                time.sleep(1.0)
                
                st.write("2. Formulating targeted queries for the active search provider...")
                time.sleep(1.0)
                
                st.write("3. Gathering real-world search evidence & analyzing sources...")
                
                # Run the actual API call
                result, error = run_transformation(industry_input, process_input)
                
                if error:
                    status.update(label="Transformation workflow failed!", state="error")
                    st.error(error)
                else:
                    status.update(label="Transformation workflow finished successfully!", state="complete")
                    st.success(f"Successfully processed and stored transformation for '{process_input}'!")
                    st.write("Navigating to comparison view...")
                    time.sleep(1.0)
                    st.rerun()


# --- Tab 2: Compare ---
with tab_compare:
    if not selected_process_id:
        st.info("Please select an analysis history item from the sidebar, or trigger a new analysis to compare states.")
    else:
        detail = fetch_process_detail(selected_process_id)
        if detail:
            st.markdown(f"## **Process**: {detail['name']} ({detail['industry']})")
            st.write(f"Analyzed on: {detail['created_at'][:19].replace('T', ' ')}")
            st.markdown("---")
            
            # Metric Row
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Discovered Activities", len(detail["current_activities"]))
            with col_m2:
                st.metric("Synthesized Evidence Analyses", len(detail["analyses"]))
            with col_m3:
                st.metric("AI/Automation Opportunities", len(detail["opportunities"]))
                
            st.markdown("---")
            
            # Check if this process needs transformation
            is_untransformed = len(detail["future_activities"]) == 0
            if is_untransformed:
                st.warning("⚡ **Seeded Current State Only**: This process only has current-state activities in PostgreSQL. Run the research agent to generate AI interventions and design the future state process.")
                if st.button("Transform Process ⚡", use_container_width=True):
                    with st.spinner("Agent mapping and researching process technology..."):
                        res, err = run_existing_transformation(selected_process_id)
                        if err:
                            st.error(f"Transformation failed: {err}")
                        else:
                            st.success("Transformation completed successfully!")
                            time.sleep(1.0)
                            st.rerun()
            st.markdown("### **Operational Flow: Current State → AI Intervention → Future State**")
            
            # Map activities by current activity matching
            # For each current activity, find matching analyses, opportunities, and future activities
            for c_act in detail["current_activities"]:
                col_curr, col_interv, col_future = st.columns(3)
                
                # 1. Left Column: Current State Activity
                with col_curr:
                    curr_name = c_act['name'].replace("<", "&lt;").replace(">", "&gt;")
                    curr_role = str(c_act['role']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                    curr_sys = str(c_act['system']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                    curr_prob = str(c_act['problem']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                    st.markdown(f'<div class="card current-card"><h4>{curr_name}</h4><p><b>Role:</b> {curr_role}</p><p><b>System:</b> {curr_sys}</p><div class="problem-badge">⚠️ {curr_prob}</div></div>', unsafe_allow_html=True)
                
                # 2. Middle Column: Intervention & Provenance Evidence
                # Look for matching evidence analysis for this activity
                matching_analyses = [a for a in detail["analyses"] if a["activity_id"] == c_act["id"]]
                with col_interv:
                    if matching_analyses:
                        analysis = matching_analyses[0]
                        source_info = ""
                        if analysis.get("source"):
                            src = analysis["source"]
                            src_title = (src.get('title') or src.get('url', 'Source')).replace("<", "&lt;").replace(">", "&gt;")
                            source_info = f'<p style="margin-top: 10px; font-size: 0.85rem;"><b>Source:</b> <a class="url-link" href="{src["url"]}" target="_blank">{src_title}</a></p>'
                        
                        tech_txt = str(analysis.get('technology', '')).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        works_txt = str(analysis.get('how_it_works', '')).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        override_txt = str(analysis.get('human_control', '')).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        
                        card_html = f'<div class="card evidence-card"><h5 style="color: #60A5FA;">🔬 Synthesized Tech Evidence</h5><p><b>Technology:</b> {tech_txt}</p><p><b>How It Works:</b> {works_txt}</p><p><b>Human Override:</b> {override_txt}</p>{source_info}</div>'
                        st.markdown(card_html, unsafe_allow_html=True)
                    else:
                        st.write("No specific research analysis matched this activity.")
                
                # 3. Right Column: Future State Activity
                # Look for future activity replacing this current activity
                matching_futures = [f for f in detail["future_activities"] if f["current_activity_id"] == c_act["id"]]
                with col_future:
                    if matching_futures:
                        f_act = matching_futures[0]
                        
                        # Set decision type style class
                        d_type = str(f_act['decision_type']).strip().lower()
                        badge_class = "badge-ai-assisted"
                        if "fully automated" in d_type:
                            badge_class = "badge-fully-automated"
                        elif "human-in-the-loop" in d_type:
                            badge_class = "badge-human-in-the-loop"
                        elif "human decision" in d_type:
                            badge_class = "badge-human-decision"
                            
                        f_name = f_act['name'].replace("<", "&lt;").replace(">", "&gt;")
                        f_role = str(f_act['role']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        f_sys = str(f_act['system']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        f_ben = str(f_act['expected_benefit']).replace("\n", "<br>").replace("<", "&lt;").replace(">", "&gt;")
                        f_dec = str(f_act['decision_type']).replace("<", "&lt;").replace(">", "&gt;")

                        future_html = f'<div class="card future-card"><h4>{f_name}</h4><p><b>Future Role:</b> {f_role}</p><p><b>Future System:</b> {f_sys}</p><p><b>Benefit:</b> {f_ben}</p><div class="decision-badge {badge_class}">⚙️ {f_dec}</div></div>'
                        st.markdown(future_html, unsafe_allow_html=True)
                    else:
                        st.write("No future activity mapping exists for this step.")
                
                st.markdown("<hr style='border-top: 1px dashed #334155; margin: 15px 0;' />", unsafe_allow_html=True)
                
            # Opportunities Overview Section
            st.markdown("### 💡 High-Level AI Initiatives / Opportunities")
            for opp in detail["opportunities"]:
                with st.expander(opp["opportunity_name"]):
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.markdown(f"**Description:** {opp['description']}")
                        st.markdown(f"**Core Technology:** {opp['technology']}")
                    with col_r:
                        st.markdown(f"**Expected Benefit:** {opp['expected_benefit']}")
                        st.markdown(f"**Implementation Risk:** {opp['risk']}")
