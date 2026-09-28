"""
6_Recommendations.py  --  Pair C, Step 9: Recommendation Engine display (SRS Steps 37-39)

Reads data/models/recommendations.csv, built by build_recommendations.py
in this same folder (Step 8 of this guide's build order). Every row here
already carries its own evidence -- this page just displays and filters it.
"""
import streamlit as st

from utils import load_recommendations, download_button

st.set_page_config(page_title="Recommendations -- DineIQ", layout="wide")
st.title("Recommendation Engine")
st.caption("Every recommendation is backed by real numbers pulled from Pair B's models -- none of these are unexplained suggestions.")

recs = load_recommendations()

priority_filter = st.multiselect(
    "Priority", ["Critical", "High", "Medium", "Low"],
    default=["Critical", "High", "Medium", "Low"],
)
shown = recs[recs["priority"].isin(priority_filter)]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total recommendations", f"{len(shown):,}")
col2.metric("Critical", f"{(shown['priority'] == 'Critical').sum():,}")
col3.metric("High", f"{(shown['priority'] == 'High').sum():,}")
col4.metric("Medium", f"{(shown['priority'] == 'Medium').sum():,}")

st.divider()

priority_color = {"Critical": "\U0001F534", "High": "\U0001F7E0", "Medium": "\U0001F7E1", "Low": "\U0001F7E2"}
for _, r in shown.iterrows():
    with st.expander(f"{priority_color.get(r.priority, '')} [{r.priority}] {r.recommended_action}"):
        st.write(f"**Recommended action:** {r.recommended_action}")
        st.write("**Evidence:**")
        for reason in str(r.reason).split(" | "):
            st.write(f"- {reason}")

st.divider()
download_button(shown, "recommendations", "recommendations_export.csv")
