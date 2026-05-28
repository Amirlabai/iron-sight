with open('dashboard/src/components/Sidebar/Sidebar.jsx', 'r') as f:
    content = f.read()

import re
print("useLayoutEffect block:")
print(re.search(r'React\.useLayoutEffect\(\(\) => \{.*?\n  \}, \[collapsedY, isMobile, isSidebarExpanded, sheetY\]\);', content, flags=re.DOTALL).group(0))

print("\nuseEffect block:")
print(re.search(r'React\.useEffect\(\(\) => \{.*?\n  \}, \[isSidebarExpanded, isMobile, sheetY\]\);', content, flags=re.DOTALL).group(0))
