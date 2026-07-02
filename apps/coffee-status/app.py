import streamlit as st
from pathlib import Path
from src.readers import resolve_project_root, file_exists, read_first_lines

# Determine Project Coffee root (two levels up from this file)
APP_DIR = Path(__file__).parent
PROJECT_ROOT = resolve_project_root(__file__)

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
    if file_exists(PROJECT_ROOT, file_rel):
        st.success(f"✅ {file_rel} exists")
        if file_rel == "brew-log/active_context.md":
            # Display first 20 lines of active_context.md
            lines = read_first_lines(PROJECT_ROOT, file_rel)
            if lines is not None:
                st.text("\n".join(lines))
            else:
                st.error(f"Error reading {file_rel}")
        elif file_rel == "config/house_blend.md":
            # Display first 20 lines of house_blend.md
            lines = read_first_lines(PROJECT_ROOT, file_rel)
            if lines is not None:
                st.text("\n".join(lines))
            else:
                st.error(f"Error reading {file_rel}")
        elif file_rel == "ROADMAP.md":
            # Display first 20 lines of ROADMAP.md
            lines = read_first_lines(PROJECT_ROOT, file_rel)
            if lines is not None:
                st.text("\n".join(lines))
            else:
                st.error(f"Error reading {file_rel}")
    else:
        st.warning(f"❌ {file_rel} is missing")