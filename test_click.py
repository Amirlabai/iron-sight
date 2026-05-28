from playwright.sync_api import sync_playwright

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 414, "height": 896})
        page = context.new_page()
        page.goto("http://localhost:5173", wait_until='networkidle')

        # Dismiss onboarding
        try:
            btn = page.wait_for_selector('button:has-text("Skip and start monitoring")', timeout=5000)
            btn.click()
        except:
            pass

        page.wait_for_selector('.splash-screen', state='hidden', timeout=10000)
        page.evaluate("document.querySelectorAll('.alert-prefs-overlay').forEach(el => el.remove())")

        page.mouse.click(200, 200) # Hide sidebar if expanded
        page.wait_for_timeout(1000)

        # Try clicking normally without force
        try:
            page.click('.sidebar-expand-btn', timeout=3000)
            print("Click successful without force!")
        except Exception as e:
            print("Click failed:", e)

        browser.close()

if __name__ == "__main__":
    test()
