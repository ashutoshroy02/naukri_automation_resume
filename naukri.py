import os
import time
import random
import shutil
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

# ------------------------------------------------------------------
# Load .env explicitly (this is the missing piece)
# ------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    raise RuntimeError("EMAIL or PASSWORD not set. Check .env file")

# Random interval: cron runs every 10 min, this skips ~75% of runs
# Effective upload interval is random between 10-40 minutes
MIN_INTERVAL = 10
MAX_INTERVAL = 40
SKIP_CHANCE = 1 - (MIN_INTERVAL / MAX_INTERVAL)  # ~0.75

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
RESUME_PATH = BASE_DIR / "Your_Resume.pdf"
FIREFOX_PROFILE = BASE_DIR / "naukri_profile"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"

def get_firefox_binary():
    """Finds the actual firefox executable, prioritizing native paths and snap."""
    # Check snap real binary first (geckodriver hates wrapper scripts like /usr/bin/firefox or /snap/bin/firefox)
    if os.path.exists("/snap/firefox/current/usr/lib/firefox/firefox"):
        return "/snap/firefox/current/usr/lib/firefox/firefox"

    # Check flatpak
    if os.path.exists("/var/lib/flatpak/app/org.mozilla.firefox"):
        return "flatpak run org.mozilla.firefox" # Geckodriver might still complain here, but it's an option

    # Fallback to shutil
    ff_path = shutil.which("firefox")
    if ff_path:
        return ff_path

    return None

def update_naukri():
    options = Options()
    options.add_argument("-headless")
    options.add_argument("-profile")
    options.add_argument(str(FIREFOX_PROFILE))

    # Set the resolved binary location
    binary = get_firefox_binary()
    if binary:
        options.binary_location = binary

    # Stability in background environments
    options.set_preference("browser.tabs.remote.autostart", False)
    options.set_preference("browser.tabs.remote.autostart.2", False)

    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(options=options, service=service)

    try:
        print("Navigating to Naukri Profile...")
        driver.get(NAUKRI_PROFILE_URL)

        wait = WebDriverWait(driver, 25)

        # ---------------- LOGIN ----------------
        if "login" in driver.current_url:
            print("Session expired. Logging in...")

            wait.until(EC.presence_of_element_located((By.ID, "usernameField"))).send_keys(EMAIL)
            driver.find_element(By.ID, "passwordField").send_keys(PASSWORD)

            # Use explicit wait for the submit button and click it
            login_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login') and @type='submit']")))
            driver.execute_script("arguments[0].click();", login_btn)

            wait.until(EC.invisibility_of_element_located((By.ID, "usernameField")))
            print("Login successful.")

            driver.get(NAUKRI_PROFILE_URL)

        # ---------------- UPLOAD ----------------
        # Save page source for debugging
        with open(str(BASE_DIR / "page_before.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot(str(BASE_DIR / "page_before.png"))

        print("Looking for resume upload section...")
        # Try multiple selectors for the file input
        upload_input = None
        for selector in ["#attachCV", "input[type='file']", "//input[@type='file']"]:
            try:
                if selector.startswith("//"):
                    upload_input = driver.find_element(By.XPATH, selector)
                else:
                    upload_input = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"Found upload input with: {selector}")
                break
            except Exception:
                continue

        if not upload_input:
            print("Could not find file input. Saving page for debug...")
            driver.save_screenshot(str(BASE_DIR / "no_upload_input.png"))
            raise Exception("File upload input not found on page")

        # Make sure element is interactable
        driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.visibility = 'visible'; arguments[0].style.opacity = '1';", upload_input)

        print(f"Uploading resume: {RESUME_PATH}")
        upload_input.send_keys(str(RESUME_PATH))

        print("Waiting for upload to process...")
        time.sleep(10)

        # Try clicking any "Save" button that appears after upload
        try:
            save_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Save')]")
            driver.execute_script("arguments[0].click();", save_btn)
            print("Clicked Save button")
            time.sleep(5)
        except Exception:
            print("No Save button found, upload may be auto-saved")

        # Save page source after upload
        with open(str(BASE_DIR / "page_after.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot(str(BASE_DIR / "page_after.png"))

        # Verify — check if resume name appears on page or success message
        page_source = driver.page_source
        if "Your_Resume.pdf" in page_source or "uploaded" in page_source.lower() or "success" in page_source.lower():
            print("Resume upload appears successful")
        else:
            print("Upload verification failed — check debug artifacts")

    except Exception as e:
        print(f"❌ Error: {e}")
        driver.save_screenshot(str(BASE_DIR / "error_screenshot.png"))
        print(f"📸 Screenshot saved to {BASE_DIR / 'error_screenshot.png'}")
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    # Random skip to make effective interval 10-40 min
    if random.random() < SKIP_CHANCE:
        skip_minutes = random.randint(MIN_INTERVAL, MAX_INTERVAL)
        print(f"Skipped this run (next ~{skip_minutes} min)")
        exit(0)

    if not RESUME_PATH.exists():
        raise FileNotFoundError(f"Resume not found: {RESUME_PATH}")

    FIREFOX_PROFILE.mkdir(exist_ok=True)
    update_naukri()
