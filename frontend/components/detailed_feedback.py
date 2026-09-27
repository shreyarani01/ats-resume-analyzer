from typing import Any, Dict
import streamlit as st


def display_detailed_feedback(analysis: Dict[str, Any]):
    st.subheader("🔍 Detailed Feedback")

    if not isinstance(analysis, dict):
        st.info("No detailed feedback available.")
        return

    detailed = analysis.get("detailed_feedback", {})

    if not detailed:
        st.info("No detailed feedback available.")
        return

    # Tabs layout
    tab1, tab2, tab3 = st.tabs(
        ["Section Breakdown", "Formatting & ATS", "Content Quality"]
    )

    # 1. TAB 1: SECTION BREAKDOWN
    with tab1:
        st.write("### Section Breakdown")

        sections_data = None
        if isinstance(detailed, dict):
            sections_data = detailed.get("section_analysis", {})
        elif isinstance(detailed, list):
            sections_data = detailed

        if not sections_data:
            st.info("No section breakdown available.")
        elif isinstance(sections_data, dict):
            for section_name, feedback in sections_data.items():
                with st.expander(f"📌 {str(section_name).title()}"):
                    if isinstance(feedback, (dict, list)):
                        st.json(feedback)
                    else:
                        st.write(str(feedback))
        elif isinstance(sections_data, list):
            for item in sections_data:
                if isinstance(item, dict):
                    name = (
                        item.get("section_name")
                        or item.get("name")
                        or "Section"
                    )
                    feedback = item.get("feedback") or item.get("details") or item
                    with st.expander(f"📌 {str(name).title()}"):
                        if isinstance(feedback, (dict, list)):
                            st.json(feedback)
                        else:
                            st.write(str(feedback))
                else:
                    st.markdown(f"- {item}")

    # 2. TAB 2: ATS & FORMATTING CHECKS
    with tab2:
        st.write("### ATS & Formatting Checks")
        formatting_checks = []
        if isinstance(detailed, dict):
            formatting_checks = detailed.get("formatting_checks", [])

        if formatting_checks and isinstance(formatting_checks, list):
            for item in formatting_checks:
                st.markdown(f"- {item}")
        else:
            st.info("No formatting issues detected.")

    # 3. TAB 3: WRITING & CONTENT SUGGESTIONS
    with tab3:
        st.write("### Writing & Content Suggestions")
        writing_improvements = []
        if isinstance(detailed, dict):
            writing_improvements = detailed.get("writing_improvements", [])

        if writing_improvements and isinstance(writing_improvements, list):
            for suggestion in writing_improvements:
                st.markdown(f"- 💡 {suggestion}")
        else:
            st.info("No specific writing suggestions.")