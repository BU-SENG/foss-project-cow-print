# AetherDB Admin Console - UI Components

## Author
Aneke Kamsiyohcukwu Anthony

## Description
UI components and styling for the AetherDB Admin Console. Provides a cyberpunk/terminal-themed interface with green neon aesthetics matching the Figma design.

## File
- `ui_components.py` - Page configuration, CSS styling, and session state initialization

## Features
- ✅ Cyberpunk/terminal aesthetic with green neon (#00ff41) theme
- ✅ Angled corners and glowing effects
- ✅ Custom styled inputs, buttons, and sections
- ✅ Session state management for connections and logs
- ✅ Responsive two-column layout
- ✅ Dark background with gradients

## Installation
```bash
pip install streamlit
```

## Usage
```python
from ui_components import setup_page_config, apply_custom_css, initialize_session_state

# Setup
setup_page_config()
apply_custom_css()
initialize_session_state()
```

## Functions

### `setup_page_config()`
Configures Streamlit page settings (title, icon, layout)

### `apply_custom_css()`
Applies cyberpunk CSS theme with:
- Green neon borders and text
- Angled section headers
- Custom buttons and inputs
- Terminal-style fonts

### `initialize_session_state()`
Initializes default data:
- Sample database connections (MySQL, PostgreSQL, SQLite)
- System logs with timestamps

## Session State Structure

### Connections
```python
{
    "name": "studentdb",
    "type": "MySQL",
    "host": "localhost:3306",
    "status": "active"
}
```

### Logs
```python
{
    "time": "2025-11-02 17:55:01",
    "type": "info",
    "message": "AetherDB service started."
}
```

## Testing
```bash
python -m streamlit run aetherdb_ui/app.py
```

## Integration
This module works with `business_logic.py` (Person 2's work):

```python
# app.py
from ui_components import setup_page_config, apply_custom_css, initialize_session_state
from business_logic import render_main_interface

setup_page_config()
apply_custom_css()
initialize_session_state()
render_main_interface()
```

## Git Workflow
```bash
# Create branch
git checkout -b person1/ui-components

# Add files
git add aetherdb_ui/

# Commit
git commit -m "Add UI components for AetherDB admin console"

# Push
git push -u origin person1/ui-components
```

## Color Scheme
- Primary Green: `#00ff41`
- Secondary Green: `#00cc33`
- Error Red: `#ff4444`
- Background: `#0a0e1a` to `#151922`

## Next Steps
- Merge with `business_logic.py` from Person 2
- Integrate with AI core (Gemini API)
- Connect to real databases

## Related Files
- `business_logic.py` - Person 2's work
- `app.py` - Main integration file
- `OSS project.pdf` - Full project documentation

---
**Status**: ✅ Ready for Integration  
**Last Updated**: November 19, 2025