with open('dashboard/src/App.jsx', 'r') as f:
    content = f.read()

import re
# Find the button and replace its event handlers to stop everything.
old_button = '''<button
          type="button"
          className="sidebar-expand-btn"
          onClick={(e) => { e.stopPropagation(); setIsSidebarExpanded(true); }} onPointerDown={(e) => e.stopPropagation()}
          aria-label="Expand Sidebar"
        >'''

new_button = '''<button
          type="button"
          className="sidebar-expand-btn"
          onClick={(e) => { e.stopPropagation(); setIsSidebarExpanded(true); }}
          onPointerDown={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
          onMouseUp={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
          onTouchEnd={(e) => e.stopPropagation()}
          aria-label="Expand Sidebar"
        >'''

content = content.replace(old_button, new_button)

with open('dashboard/src/App.jsx', 'w') as f:
    f.write(content)
