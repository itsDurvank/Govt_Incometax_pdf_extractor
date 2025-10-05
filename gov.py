from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import os, time, re, urllib.parse

SAVE_DIR = "downloads"
START_PAGE = 812   # 🔹 change this to whichever page you want to start from
TOTAL_PAGES = 1999
os.makedirs(SAVE_DIR, exist_ok=True)

def safe_filename(name):
    name = re.sub(r"[\\/*?<>:|\"']", "_", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name[:240]

def make_absolute_url(base, url):
    return urllib.parse.urljoin(base, url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://incometaxindia.gov.in/Pages/communications/notifications.aspx")
    page.wait_for_timeout(3000)

    # 🔹 Navigate directly to a specified page number using the input box
    try:
        print(f"Jumping directly to page {START_PAGE}...")
        textbox = page.wait_for_selector("input[id*='txtPageNumber']", timeout=10000)
        textbox.fill(str(START_PAGE))
        textbox.press("Enter")  # triggers postback
        page.wait_for_timeout(4000)
        page.wait_for_selector("span.NotificationNumber", timeout=15000)
        print(f"✅ Arrived at page {START_PAGE}")
    except Exception as e:
        print(f"⚠️ Could not jump to page {START_PAGE}: {e}")

    for page_no in range(START_PAGE, TOTAL_PAGES + 1):
        print(f"\n=== Processing listing page {page_no} ===")
        try:
            page.wait_for_selector("span.NotificationNumber", timeout=15000)
        except PlaywrightTimeoutError:
            print("No notifications found, stopping.")
            break

        notifications = page.query_selector_all("span.NotificationNumber")
        if not notifications:
            print("Empty page, stopping.")
            break

        for idx, notif in enumerate(notifications, 1):
            try:
                print(f"[{page_no}-{idx}] Clicking notification...")

                current_url = page.url
                notif.click()
                page.wait_for_timeout(2000)

                page.wait_for_function("oldURL => window.location.href !== oldURL", current_url, timeout=10000)
                new_url = page.url

                if ".pdf" in new_url.lower():
                    print(f"📄 PDF opened: {new_url}")
                    # You’ll manually click download, no need to auto-download
                else:
                    print(f"⚠️ No PDF URL detected (new URL = {new_url})")

                page.go_back(timeout=30000)
                page.wait_for_selector("span.NotificationNumber", timeout=15000)
                page.wait_for_timeout(500)

            except Exception as e:
                print(f"❌ Error processing notification {idx} on page {page_no}: {e}")
                try:
                    if ".pdf" in page.url.lower():
                        page.go_back(timeout=30000)
                        page.wait_for_selector("span.NotificationNumber", timeout=15000)
                except Exception:
                    pass

        # 🔹 Move to next page using the textbox (reliable method)
        if page_no < TOTAL_PAGES:
            try:
                print(f"➡️ Moving to next page ({page_no + 1}) via textbox...")
                textbox = page.wait_for_selector("input[id*='txtPageNumber']", timeout=10000)
                textbox.fill(str(page_no + 1))
                textbox.press("Enter")
                page.wait_for_timeout(4000)
                page.wait_for_selector("span.NotificationNumber", timeout=15000)
                print(f"✅ Now on listing page {page_no + 1}")
            except Exception as e:
                print(f"Pagination failed: {e}")
                break

    print("\n✅ Finished all pages. Closing browser.")
    browser.close()
