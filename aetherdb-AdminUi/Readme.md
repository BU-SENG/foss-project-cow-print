# AetherDB Admin Console - UI Components

## Author
Anthony Aneke

## Description
UI components and styling for the AetherDB Admin Console. Provides a modern purple gradient interface with glassmorphism effects matching the project requirements.

## Files
- `ui_components.py` - Page configuration, CSS styling, and session state initialization
- `app.py` - Main application file that integrates all components
- `README.md` - This documentation

## Features
- ✅ **Purple Gradient Theme** - Beautiful gradient background (#667eea → #764ba2 → #f093fb)
- ✅ **Glassmorphism UI** - Modern transparent cards with backdrop blur
- ✅ **Responsive Layout** - Two-column design for connections and logs
- ✅ **Session State Management** - Handles connections and system logs
- ✅ **Interactive Forms** - Add, edit, and delete database connections
- ✅ **Smooth Animations** - Hover effects and transitions
- ✅ **Custom Styled Components** - Buttons, inputs, and sections

## Installation

### Prerequisites
```bash
pip install streamlit
```

### File Structure
```
aetherdb_ui/
├── ui_components.py    # UI setup and styling (My work)
├── business_logic.py   # Business logic (chiedu's work - coming soon)
├── app.py             # Main integration file
└── README.md          # This documentation
```

## Usage

### Running the Application
```bash
# Navigate to project directory
cd foss-project-cow-print

# Run the app
python -m streamlit run aetherdb_ui/app.py
```

### Import in Custom Applications
```python
from ui_components import setup_page_config, apply_custom_css, initialize_session_state

# Setup
setup_page_config()
apply_custom_css()
initialize_session_state()
```

## Functions

### `setup_page_config()`
Configures Streamlit page settings:
- Sets page title and icon
- Configures wide layout
- Collapses sidebar by default

### `apply_custom_css()`
Applies custom CSS styling including:
- Purple gradient background
- Glassmorphism effects (transparent cards with blur)
- Custom button and input styling
- Smooth animations and transitions
- Rounded corners and shadows
- Custom scrollbar design

### `initialize_session_state()`
Initializes session state with default data:
- **connections**: Sample database connections (MySQL, PostgreSQL, SQLite)
- **logs**: System log entries with timestamps

## Session State Structure

### Connections
```python
{
    "name": "database_name",
    "type": "MySQL|PostgreSQL|SQLite|MongoDB",
    "host": "hostname:port",
    "status": "active|inactive"
}
```

### Logs
```python
{
    "time": "YYYY-MM-DD HH:MM:SS",
    "type": "info|error",
    "message": "Log message text"
}
```

## CSS Classes Reference

### Main Containers
- `.main-header` - Top header with gradient background
- `.section-box` - Glass-effect container for sections
- `.section-header` - Purple gradient header bars
- `.section-content` - Content area inside sections

### Components
- `.connection-item` - Individual connection cards with hover effect
- `.connection-name` - Connection name and type display
- `.log-entry` - Individual log entries
- `.log-timestamp` - Timestamp in logs
- `.log-message` - Regular log message
- `.log-error` - Error log message with red styling
- `.log-container` - Scrollable log container
- `.glass-effect` - Glassmorphism effect class

## Color Scheme

| Element | Color | Hex Code | Usage |
|---------|-------|----------|-------|
| Primary Purple | Deep Purple | `#667eea` | Main gradient, buttons |
| Secondary Purple | Medium Purple | `#764ba2` | Gradient middle, accents |
| Accent Purple | Light Purple | `#f093fb` | Gradient end, highlights |
| Error Red | Bright Red | `#ff6b6b` | Error messages |
| Success Green | Green | `#48bb78` | Success messages |
| Text | White | `#ffffff` | Primary text |
| Text Secondary | Light Gray | `#f0f0f0` | Secondary text |

## Testing

### Run the application:
```bash
python -m streamlit run aetherdb_ui/app.py
```

### Visual Checklist:
- [ ] Page loads with purple gradient background
- [ ] Header displays "AETHER DB - Admin Console"
- [ ] All text is visible in white
- [ ] Sections have glassmorphism effect
- [ ] Headers have purple gradient
- [ ] Input fields have transparent background
- [ ] Buttons have purple gradient
- [ ] Hover effects work smoothly
- [ ] Scrollbar is purple themed
- [ ] Sample connections display correctly
- [ ] Sample logs display with timestamps
- [ ] EDIT/DELETE buttons are functional

## Features Implemented

### Current Connections Section
- Displays all active database connections
- Shows connection type (MySQL, PostgreSQL, SQLite, MongoDB)
- Displays host and port information
- EDIT button (shows info message)
- DELETE button (removes connection)

### Add New Connection Form
- Database type selector dropdown
- Connection name input
- Host and port inputs (side by side)
- Username input
- Password input (masked)
- CANCEL button (refreshes form)
- SAVE CONNECTION button (validates and adds connection)

### System Logs Section
- Displays chronological log entries
- Shows timestamps for each entry
- Differentiates between info and error messages
- Error messages highlighted in red
- Scrollable container for long logs

## Integration with Business Logic

This module is designed to work with `business_logic.py`:

```python
# app.py (future integration)
from ui_components import setup_page_config, apply_custom_css, initialize_session_state
from business_logic import render_main_interface

# Setup
setup_page_config()
apply_custom_css()
initialize_session_state()

# Render
render_main_interface()
```

## Git Workflow

### Current Branch:
```bash
# Branch name: anthony-Adminui
git branch
```

### Committing Changes:
```bash
# Check status
git status

# Stage changes
git add aetherdb_ui/

# Commit
git commit -m "Update UI to purple gradient theme

- Implement purple gradient background
- Add glassmorphism effects
- Update all component styling
- Match project requirements"

# Push
git push origin anthony-Adminui
```

### Creating Pull Request:
1. Go to: https://github.com/BU-SENG/foss-project-cow-print
2. Click "Compare & pull request" button
3. Fill in title and description
4. Request reviewers
5. Submit PR

## Technical Details

### Technologies Used
- **Streamlit** - Web framework
- **Python 3.x** - Programming language
- **CSS3** - Custom styling
- **HTML5** - Markup (via st.markdown)
- **Google Fonts** - Inter & Poppins fonts

### Browser Compatibility
Tested and working on:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+

### Performance Notes
- CSS loaded once on initialization
- Minimal JavaScript usage
- Efficient session state management
- Backdrop blur may impact performance on older devices
- Smooth animations using CSS transitions

## Troubleshooting

### Issue: Blank screen / Black background
**Solution**: Make sure you have both `ui_components.py` AND `app.py` in the same folder. Run `app.py`, not `ui_components.py`

### Issue: Import error - "cannot import ui_components"
**Solution**: 
```bash
# Make sure you're in the correct directory
cd foss-project-cow-print
python -m streamlit run aetherdb_ui/app.py
```

### Issue: Styles not applying
**Solution**: 
1. Clear browser cache (`Ctrl + Shift + Delete`)
2. Stop streamlit (`Ctrl + C`)
3. Restart: `python -m streamlit run aetherdb_ui/app.py`

### Issue: Fonts not loading
**Solution**: Check internet connection (Google Fonts requires internet access)

### Issue: Buttons not working
**Solution**: Make sure session state is initialized before rendering buttons

### Issue: Purple gradient not showing
**Solution**: Browser may not support CSS gradients. Update browser or check CSS inspector

## Future Enhancements

### Planned Features:
1. **Theme Switcher** - Toggle between light/dark/purple modes
2. **Real Database Integration** - Connect to actual databases
3. **Connection Testing** - Test database connection before saving
4. **Export Functionality** - Export connections and logs
5. **Search & Filter** - Search logs and filter connections
6. **Notifications** - Toast notifications for actions
7. **Mobile Responsive** - Better mobile layout

### Integration Goals:
- Connect to Gemini AI API for schema discovery
- Implement real database connection testing
- Add authentication and user management
- Enable query execution from UI
- Add data visualization

## Support & Contact

- **GitHub Repository**: https://github.com/BU-SENG/foss-project-cow-print
- **Branch**: anthony-Adminui
- **Author**: Anthony Aneke
- **Project**: AetherDB - AI-Powered Natural Language Database Processor

## Related Documentation

- [Business Logic Module](business_logic.py) - Person 2's work (in progress)
- [Main Project README](../README.md) - Full project information
- [OSS Project PDF](../OSS_project.pdf) - Complete project specifications
- [Streamlit Docs](https://docs.streamlit.io) - Framework documentation

## Version History

### v1.1.0 (Current)
- Updated to purple gradient theme
- Implemented glassmorphism effects
- Added rounded corners
- Improved animations
- Enhanced form validation

### v1.0.0
- Initial implementation with green cyberpunk theme

## Design Philosophy

The purple gradient theme was chosen to:
- Match project requirements for "Gradient purple UI"
- Provide modern, professional appearance
- Create visual hierarchy with glassmorphism
- Ensure readability with high contrast text
- Offer smooth, engaging user experience

## Acknowledgments

- Design matches project requirements from main README
- Built with Streamlit framework
- Uses Google Fonts (Inter, Poppins)
- Inspired by modern glassmorphism design trends
- Gradient colors inspired by Purple Rain palette

---

**Last Updated**: November 19, 2025  
**Status**: ✅ Ready for Integration  
**Theme**: Purple Gradient with Glassmorphism  
**Next Steps**: Integrate with business_logic.py module