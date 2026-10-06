import streamlit as st
from src.readers import resolve_project_root
from src.status_builder import PREVIEWABLE_FILE_PATHS, build_coffee_status

# Determine Project Coffee root (two levels up from this file)
PROJECT_ROOT = resolve_project_root(__file__)
STATUS = build_coffee_status(PROJECT_ROOT)

st.title("Project Coffee Status")
st.code(f"Project Coffee root: {STATUS.project_root}")

for file_status in STATUS.tracked_files:
    if file_status.exists:
        st.success(f"✅ {file_status.relative_path} exists")
        if file_status.preview_lines is not None:
            st.text("\n".join(file_status.preview_lines))
        elif file_status.relative_path in PREVIEWABLE_FILE_PATHS:
            st.error(f"Error reading {file_status.relative_path}")
    else:
        st.warning(f"❌ {file_status.relative_path} is missing")
