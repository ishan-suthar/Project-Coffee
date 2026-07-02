import streamlit as st
from pathlib import Path

# Determine Project Coffee root (two levels up from this file)
APP_DIR = Path(__file__).parent
PROJECT_ROOT = APP_DIR.parent.parent

st.title("Project Coffee Status")
st.code(f"Project Coffee root: {PROJECT_ROOT}")

# Files to check for existence
files_to_check = [
    "brew-log/active_context.md",
    "ROADMAP.md",
    "config/house_blend.md",
    "ledger/cost_log.md",
    "roastery/tasting_notes.md"
]

for file_rel in files_to_check:
    file_path = PROJECT_ROOT / file_rel
    if file_path.exists():
        st.success(f"✅ {file_rel} exists")
        if file_rel == "brew-log/active_context.md":
            # Display first 20 lines of active_context.md
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()[:20]
                st.text("\n".join(lines))
            except Exception as e:
                st.error(f"Error reading {file_rel}: {e}")
    else:
        st.warning(f"❌ {file_rel} is missing")