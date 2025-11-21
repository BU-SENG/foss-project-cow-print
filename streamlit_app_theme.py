# streamlit_app_theme.py
import streamlit as st

def apply_custom_theming():
    theme = st.session_state.get("theme", "dark")

    st.markdown(
        f"""
        <style>
            :root {{
                --bg-gradient-dark: linear-gradient(-45deg, #667eea, #764ba2, #f093fb, #f5576c);
                --bg-gradient-light: linear-gradient(135deg, #e0e7ff, #c3dafe, #ddd6fe, #fde2e4);
                --text-dark: #ffffff; /* White text for dark mode */
                --text-light: #000000; /* Dark text for light mode */
                --card-dark: rgba(255, 255, 255, 0.08);
                --card-light: rgba(255, 255, 255, 0.9);
            }}

            .stApp {{
                background: {'var(--bg-gradient-dark)' if theme == 'dark' else 'var(--bg-gradient-light)'};
                background-size: 400% 400%;
                animation: gradient 15s ease infinite;
                color: {'var(--text-dark)' if theme == 'dark' else 'var(--text-light)'};
            }}

            /* Apply text color to all relevant elements */
            h1, h2, h3, h4, h5, h6, p, .stMarkdown, .stTextInput > div > div > input, .stTextArea > div > div > textarea {{
                color: {'var(--text-dark)' if theme == 'dark' else 'var(--text-light)'} !important;
            }}

            @keyframes gradient {{
                0% {{ background-position: 0% 50%; }}
                50% {{ background-position: 100% 50%; }}
                100% {{ background-position: 0% 50%; }}
            }}

            /* Glassmorphism cards */
            .stExpander, .stAlert, [data-testid="stMetric"] > div, 
            [data-testid="stDataFrame"], .stCodeBlock {{
                background: {'var(--card-dark)' if theme == 'dark' else 'var(--card-light)'};
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: 12px;
                border: 1px solid {'rgba(255,255,255,0.1)' if theme == 'dark' else 'rgba(0,0,0,0.05)'};
                box-shadow: 0 8px 32px rgba(0,0,0,0.{20 if theme == 'dark' else 1});
                transition: all 0.4s ease;
            }}

            /* Buttons */
            .stButton > button {{
                background: {'linear-gradient(135deg, #667eea, #764ba2)' if theme == 'dark' else '#667eea'} !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 0.75rem 1.5rem !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
            }}1

            /* Theme toggle button - floating top-right */
            [data-testid="stHeader"] {{
                position: relative;
            }}
            [data-testid="stHeader"]::after {{
                content: ' '; /* The icon is now a background image */
                position: absolute;
                top: 1rem;
                right: 1.5rem;
                width: 35px;
                height: 35px;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='{'%23fff' if theme == 'dark' else '%23333'}' stroke='currentColor' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'%3E%3C/path%3E%3C/svg%3E" );
                background-size: cover;
                cursor: pointer;
                z-index: 9999;
                border-radius: 50%; /* Make it circular */
                transition: all 0.3s ease;
                transform: {'rotate(0deg)' if theme == 'dark' else 'rotate(90deg) scale(1.1)'};
            }}
            [data-testid="stHeader"]::after:hover {{
                transform: scale(1.15);
            }}
        </style>

        <script>
            // Find the theme toggle button by its key and click it
            function toggleTheme() {{
                const themeToggleButton = parent.document.querySelector('button[data-testid="stButton"][key="theme_toggle"]');
                if (themeToggleButton) {{
                    themeToggleButton.click();
                }}
            }}

            // Add a click listener to the header's pseudo-element
            const header = parent.document.querySelector('[data-testid="stHeader"]');
            if (header && !header.dataset.themeListenerAdded) {{
                header.addEventListener('click', function(event) {{
                    // Check if the click is on the pseudo-element area (top-right corner)
                    if (event.clientX > header.offsetWidth - 70 && event.clientY < 70) {{
                        toggleTheme();
                    }}
                }}, true);
                header.dataset.themeListenerAdded = 'true';
            }}
        </script>
        """,
        unsafe_allow_html=True,
    )

def theme_toggle():
    # This button is now hidden but is clicked by the script
    # We keep it to maintain Streamlit's server-side state management
    new_theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"

    if st.button("Toggle Theme", key="theme_toggle", help="Toggle light/dark mode"):
        st.session_state.theme = new_theme
        st.rerun()
