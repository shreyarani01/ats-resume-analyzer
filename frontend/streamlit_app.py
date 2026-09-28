import streamlit as st
import sys
from pathlib import Path

# Put the repo root on sys.path so `from frontend.views import ...` resolves
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure page
st.set_page_config(
    page_title="ATS Resume Scorer",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 1. Initialize session state for view management (defaults to 'landing')
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'landing'

# Auth state defaults
for key, default in [
    ("access_token", None),
    ("refresh_token", None),
    ("user_id", None),       # Supabase auth user id (uuid)
    ("user_email", None),
    ("auth_error", None),
    ("auth_info", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# If coming back from Google OAuth
if (
    not st.session_state.access_token
    and "code" in st.query_params
):
    from frontend.services import supabase_clients
    result = supabase_clients.exchange_code_for_session(st.query_params["code"])

    # Always clear the ?code= param so a refresh doesn't try to re-exchange.
    st.query_params.clear()
    if "error" in result:
        st.session_state.auth_error = f"Google sign-in failed: {result['error']}"
    else:
        st.session_state.access_token  = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id       = result["user_id"]
        st.session_state.user_email    = result["email"]
        # Explicitly keep current view on landing/home after OAuth return
        st.session_state.current_view = 'landing'
        st.rerun()

# Load custom CSS
def load_css():
    try:
        css_path = Path(__file__).parent / 'assets' / 'styles.css'
        with open(css_path, 'r') as f:
            return f'<style>{f.read()}</style>'
    except FileNotFoundError:
        return ''

st.markdown(load_css(), unsafe_allow_html=True)

# Sidebar navigation
with st.sidebar:
    st.markdown("## Navigation")
    
    # Highlight active button visually or handle switching
    if st.button("🏠 Home", use_container_width=True, type="primary" if st.session_state.current_view == 'landing' else "secondary"):
        st.session_state.current_view = 'landing'
        st.rerun()
    
    if st.button("🎯 ATS Scorer", use_container_width=True, type="primary" if st.session_state.current_view == 'scorer' else "secondary"):
        st.session_state.current_view = 'scorer'
        st.rerun()
    
    if st.button("📊 History", use_container_width=True, type="primary" if st.session_state.current_view == 'history' else "secondary"):
        st.session_state.current_view = 'history'
        st.rerun()
    
    if st.button("📚 Resources", use_container_width=True, type="primary" if st.session_state.current_view == 'resources' else "secondary"):
        st.session_state.current_view = 'resources'
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 👤 Account")

    from frontend.services import supabase_clients

    if st.session_state.access_token:
        # Signed-in state: show email + sign-out button.
        st.caption(f"Signed in as **{st.session_state.user_email}**")
        if st.button("Sign out", use_container_width=True):
            supabase_clients.sign_out()
            for k in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[k] = None
            st.session_state.current_view = 'landing'
            st.rerun()
    else:
        # Signed-out state
        if st.session_state.auth_error:
            st.error(st.session_state.auth_error)
            st.session_state.auth_error = None
        if st.session_state.auth_info:
            st.info(st.session_state.auth_info)
            st.session_state.auth_info = None

        tab_in, tab_up = st.tabs(["Sign in", "Sign up"])

        with tab_in:
            with st.form("signin_form", clear_on_submit=False):
                email = st.text_input("Email", key="signin_email")
                password = st.text_input("Password", type="password", key="signin_pw")
                submitted = st.form_submit_button("Sign in", use_container_width=True)
            if submitted:
                result = supabase_clients.sign_in_with_password(email, password)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                    st.session_state.current_view  = 'landing'
                st.rerun()

        with tab_up:
            with st.form("signup_form", clear_on_submit=False):
                email_up = st.text_input("Email", key="signup_email")
                password_up = st.text_input("Password (min 6 chars)", type="password", key="signup_pw")
                submitted_up = st.form_submit_button("Create account", use_container_width=True)
            if submitted_up:
                result = supabase_clients.sign_up_with_password(email_up, password_up)
                if "error" in result:
                    st.session_state.auth_error = result["error"]
                elif result.get("pending_confirmation"):
                    st.session_state.auth_info = (
                        f"Check your inbox — confirmation email sent to {result['email']}."
                    )
                else:
                    st.session_state.access_token  = result["access_token"]
                    st.session_state.refresh_token = result["refresh_token"]
                    st.session_state.user_id       = result["user_id"]
                    st.session_state.user_email    = result["email"]
                    st.session_state.current_view  = 'landing'
                st.rerun()

        st.markdown("<div style='text-align:center; margin: 8px 0; color:#94a3b8;'>or</div>",
                    unsafe_allow_html=True)

        oauth = supabase_clients.google_oauth_url()
        if "error" in oauth:
            st.caption(f"Google sign-in unavailable: {oauth['error']}")
        else:
            st.link_button(
                "Continue with Google",
                url=oauth["url"],
                use_container_width=True,
            )

# Main content area - fallback to landing if view is unknown
current_view = st.session_state.get('current_view', 'landing')

if current_view == 'scorer':
    from frontend.views import scorer
    scorer.render()
elif current_view == 'history':
    from frontend.views import history
    history.render()
elif current_view == 'resources':
    from frontend.views import resources
    resources.render()
else:
    # Default landing home view
    from frontend.views import landing
    landing.render()