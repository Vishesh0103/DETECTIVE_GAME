
import streamlit as st
import json
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. PAGE CONFIG & THEMING
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Gemini AI Murder Mystery",
    page_icon="🕵️‍♂️",
    layout="wide"
)

st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #f4ecd8; }
    h1, h2, h3 { color: #d4af37 !important; font-family: 'Courier New', Courier, monospace; }
    .stButton>button {
        background-color: #3e3e3e; color: #d4af37;
        border: 1px solid #d4af37; width: 100%;
    }
    .stButton>button:hover { background-color: #d4af37; color: #1a1a1a; }
    </style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 2. CASE GENERATION
# ---------------------------------------------------------------------------
FALLBACK_CASE = {
    "victim": "Lord Ashton",
    "murderer": "Professor Plum",
    "suspects": {
        "Professor Plum": {
            "description": "A nervous scientist with ink-stained fingers.",
            "alibi": "I was in the chemistry lab all night, never left once!"
        },
        "Miss Scarlett": {
            "description": "A calm and calculating actress.",
            "alibi": "I was sleeping in my bedroom the entire evening."
        },
        "Colonel Mustard": {
            "description": "A gruff, defensive retired officer.",
            "alibi": "I spent the night reading in the lounge by the fire."
        }
    },
    "crime_scene": {
        "Desk": "Clean and organized, with a half-written letter addressed to a lawyer.",
        "Floor": "A broken chemistry vial leaking a strange glowing chemical compound.",
        "Safe": "The safe door is ajar — clearly someone knew the combination."
    },
    "contradiction_guide": {
        "suspect_name": "Professor Plum",
        "scene_area": "Floor",
        "explanation": (
            "Plum swore he never left his lab, but his signature laboratory "
            "chemical vial is shattered right here on the crime scene floor!"
        )
    }
}


@st.cache_data(show_spinner="Generating your mystery case...")
def generate_mystery_case() -> dict:
    prompt = """
    Generate a classic detective murder mystery case data bundle.
    Output strictly raw JSON matching this structure — no markdown, no ```json fences:
    {
      "victim": "Name and title of the victim",
      "murderer": "The exact name of the character who is the killer (must match one of the 3 suspects)",
      "suspects": {
         "Suspect Name 1": {
            "description": "Short physical/personality description.",
            "alibi": "Their statement of where they were."
         },
         "Suspect Name 2": { "description": "...", "alibi": "..." },
         "Suspect Name 3": { "description": "...", "alibi": "..." }
      },
      "crime_scene": {
         "Desk": "Description of what is found on or around the desk.",
         "Floor": "Description of what is found on the floor.",
         "Safe": "Description of the state of the room safe."
      },
      "contradiction_guide": {
         "suspect_name": "The exact name of the killer",
         "scene_area": "Exactly one of: Desk, Floor, or Safe",
         "explanation": "How the evidence at that scene_area shatters the killer alibi."
      }
    }
    Requirements:
    - Exactly 3 suspects.
    - Only the murderer alibi must contain a lie contradicted by ONE item in the crime scene.
    - Make names, setting, and motive original and creative.
    """
    try:
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=1.0
            )
        )
        raw = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(raw)
    except Exception as e:
        st.warning(f"API call failed ({e}). Loading a backup case instead.")
        return FALLBACK_CASE


# ---------------------------------------------------------------------------
# 3. SESSION STATE INIT
# ---------------------------------------------------------------------------
if "case" not in st.session_state:
    st.session_state.case = generate_mystery_case()
    st.session_state.collected_clues = {}
    st.session_state.revealed_contradictions = []
    st.session_state.score = 0
    st.session_state.interrogated_alibi = None
    st.session_state.game_over = False
    st.session_state.game_result = ""

case = st.session_state.case


# ---------------------------------------------------------------------------
# 4. SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("📂 Detective Log")
    st.metric(label="Score", value=f"{st.session_state.score} pts")
    st.markdown(f"**Current Case:** The Death of *{case['victim']}*")
    st.write("---")

    st.subheader("📝 Gathered Clues")
    if not st.session_state.collected_clues:
        st.info("No clues yet. Search the room!")
    else:
        for area, text in st.session_state.collected_clues.items():
            st.markdown(f"🔎 **{area}:** *{text}*")

    st.write("---")

    st.subheader("🚨 Final Accusation")
    suspect_options = ["Select a suspect..."] + list(case["suspects"].keys())
    accuse_target = st.selectbox("Who is the killer?", suspect_options)

    if st.button("File Final Charges", disabled=st.session_state.game_over):
        if accuse_target == "Select a suspect...":
            st.warning("Please select a suspect first.")
        else:
            st.session_state.game_over = True
            if accuse_target == case["murderer"]:
                st.session_state.score += 200
                st.session_state.game_result = "win"
            else:
                st.session_state.score = max(0, st.session_state.score - 100)
                st.session_state.game_result = "lose"
            st.rerun()


# ---------------------------------------------------------------------------
# 5. MAIN UI
# ---------------------------------------------------------------------------
st.title("🕵️‍♂️ Gemini AI Murder Mystery")
st.caption("A fresh, AI-generated crime scene every new game.")

# --- GAME OVER SCREEN ---
if st.session_state.game_over:
    if st.session_state.game_result == "win":
        st.balloons()
        st.success(
            f"🎉 **CASE CLOSED!** {case['murderer']} confessed to the murder of "
            f"{case['victim']}! Final Score: **{st.session_state.score} pts**"
        )
    else:
        st.error(
            f"❌ **WRONG ACCUSATION!** The true killer, **{case['murderer']}**, "
            f"escaped. Final Score: **{st.session_state.score} pts**"
        )

    if st.button("🔄 New Game"):
        generate_mystery_case.clear()
        st.session_state.clear()
        st.rerun()
    st.stop()


# --- STEP 1: SUSPECT CARDS ---
st.subheader("👥 Interrogate Suspects")
cols = st.columns(3)

for idx, (name, info) in enumerate(case["suspects"].items()):
    with cols[idx]:
        st.markdown(f"### {name}")
        st.caption(info["description"])
        if st.button(f"Question {name.split()[-1]}", key=f"q_{idx}"):
            st.session_state.interrogated_alibi = (name, info["alibi"])
            st.session_state.score += 10
            st.rerun()

if st.session_state.interrogated_alibi:
    s_name, s_alibi = st.session_state.interrogated_alibi
    with st.chat_message("user", avatar="🗣️"):
        st.markdown(f"**{s_name} states:** *\"{s_alibi}\"*")

st.write("---")

# --- STEP 2: CRIME SCENE SEARCH ---
st.subheader("🔍 Search the Study")
scene_cols = st.columns(3)

for idx, area in enumerate(case["crime_scene"].keys()):
    with scene_cols[idx]:
        already_found = area in st.session_state.collected_clues
        label = f"✅ {area} (searched)" if already_found else f"Inspect {area}"
        if st.button(label, key=f"scene_{idx}", disabled=already_found):
            st.session_state.collected_clues[area] = case["crime_scene"][area]
            st.session_state.score += 20
            st.toast(f"Clue logged for: {area}")
            st.rerun()

st.write("---")

# --- STEP 3: CONTRADICTION CHECKER ---
st.subheader("🧠 Break an Alibi")
st.write("Select a suspect and the crime scene area whose evidence exposes their lie:")

con_col1, con_col2 = st.columns([1, 2])
with con_col1:
    challenge_suspect = st.selectbox(
        "Who is lying?", list(case["suspects"].keys()), key="challenge_sus"
    )
with con_col2:
    challenge_area = st.selectbox(
        "Which area exposes the lie?", list(case["crime_scene"].keys()), key="challenge_ar"
    )

if st.button("🔦 Expose Contradiction"):
    guide = case["contradiction_guide"]
    correct_suspect = challenge_suspect == case["murderer"]
    correct_area = challenge_area == guide["scene_area"]

    if correct_suspect and correct_area:
        if challenge_area not in st.session_state.collected_clues:
            st.error("You haven't searched that area yet. Go collect the evidence first!")
        elif challenge_suspect in st.session_state.revealed_contradictions:
            st.warning("You've already exposed this contradiction. No double points!")
        else:
            st.session_state.revealed_contradictions.append(challenge_suspect)
            st.session_state.score += 100
            st.success(f"💡 **EUREKA!** {guide['explanation']}")
            st.rerun()
    else:
        st.error("That evidence doesn't break their story. Keep digging. (-15 pts)")
        st.session_state.score = max(0, st.session_state.score - 15)
        st.rerun()
