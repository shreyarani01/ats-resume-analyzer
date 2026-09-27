import importlib
from typing import Any, Dict

import streamlit as st

import frontend.components.detailed_feedback as detailed_feedback_module

# Force Streamlit/Python to pick up changes in detailed_feedback.py
importlib.reload(detailed_feedback_module)
from frontend.components.detailed_feedback import display_detailed_feedback

from frontend.components.action_items import display_action_items
from frontend.components.jd_comparision import display_jd_comparison
from frontend.components.recommendations import display_recommendations
from frontend.components.score_display import (
    display_overall_score,
    display_score_breakdown,
)
from frontend.components.skill_validation import display_skill_validation
from frontend.components.strengths_issues import (
    display_critical_issues,
    display_strengths,
)


def display_results_dashboard(analysis: Dict[str, Any]) -> None:
    """Render the full results page from one backend response dict.

    `analysis` is the JSON body returned by POST /api/v1/analyze-resume (i.e. an
    AnalysisResponse). No transformation is done here — every section reads the
    fields it needs directly.
    """
    display_overall_score(analysis)
    st.markdown("---")

    display_score_breakdown(analysis)
    st.markdown("---")

    display_strengths(analysis.get("strengths") or [])
    st.markdown("---")

    display_critical_issues(analysis)
    st.markdown("---")

    display_skill_validation(analysis)
    st.markdown("---")

    # JD comparison only shows up if the user actually submitted a JD.
    jd_comparison = analysis.get("jd_comparison") or analysis.get(
        "jd_match_analysis"
    )
    if jd_comparison:
        display_jd_comparison(jd_comparison)
        st.markdown("---")

    display_detailed_feedback(analysis)
    st.markdown("---")

    display_action_items(analysis)
    st.markdown("---")

    display_recommendations(analysis)