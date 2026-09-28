import streamlit as st

def render() -> None:
    st.title("📄 ATS Resume Analyzer & Scorer")
    st.markdown("### Optimize your resume for Applicant Tracking Systems and get hired faster.")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Key Features")
        st.markdown("""
        * **Instant ATS Match Score**: Get an overall match rating against job descriptions.
        * **Skill & Keyword Gap Analysis**: Discover missing hard skills and keywords.
        * **Detailed Feedback**: Actionable tips on formatting, content, and ATS compatibility.
        * **PDF Export**: Download structured ATS optimization reports.
        """)
        
        if st.button("🚀 Start Scoring Resume", use_container_width=True, type="primary"):
            st.session_state.current_view = "scorer"
            st.rerun()

    with col2:
        st.subheader("💡 How It Works")
        st.markdown("""
        1. **Upload Resume**: Upload your resume in PDF or DOCX format.
        2. **Paste Job Description**: Optional job text to calculate keyword alignment.
        3. **Analyze**: Advanced spaCy NLP & embeddings analyze your skills.
        4. **Improve**: Apply AI-driven fixes and track your history!
        """)

    st.markdown("---")
    
    # Sign-in callout if not logged in
    if not st.session_state.get("access_token"):
        st.info("💡 **Tip**: Sign in from the sidebar to automatically save your analysis history across sessions.")