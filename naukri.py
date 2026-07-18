import os
import time
import random
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    raise RuntimeError("EMAIL or PASSWORD not set. Check .env file")

MIN_INTERVAL = 10
MAX_INTERVAL = 40
SKIP_CHANCE = 1 - (MIN_INTERVAL / MAX_INTERVAL)

RESUME_PATH = BASE_DIR / "Your_Resume.pdf"
FIREFOX_PROFILE = BASE_DIR / "naukri_profile"
NAUKRI_PROFILE_URL = "https://www.naukri.com/mnjuser/profile"


def get_firefox_binary():
    if os.path.exists("/snap/firefox/current/usr/lib/firefox/firefox"):
        return "/snap/firefox/current/usr/lib/firefox/firefox"
    if os.path.exists("/var/lib/flatpak/app/org.mozilla.firefox"):
        return "flatpak run org.mozilla.firefox"
    ff_path = shutil.which("firefox")
    if ff_path:
        return ff_path
    return None


def wait_for_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception:
        return None


def update_naukri():
    options = Options()
    options.add_argument("-headless")
    options.add_argument("-profile")
    options.add_argument(str(FIREFOX_PROFILE))

    binary = get_firefox_binary()
    if binary:
        options.binary_location = binary

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

            login_btn = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'Login') and @type='submit']")
            ))
            driver.execute_script("arguments[0].click();", login_btn)

            wait.until(EC.invisibility_of_element_located((By.ID, "usernameField")))
            print("Login successful.")

            driver.get(NAUKRI_PROFILE_URL)

        # ---------------- UPLOAD ----------------
        time.sleep(3)

        # Try lazyAttachCV first (modern Naukri), then attachCV
        upload_el = None
        selectors = [
            (By.XPATH, "//*[contains(@class, 'upload')]//input[@value='Update resume']"),
            (By.ID, "lazyAttachCV"),
            (By.ID, "attachCV"),
            (By.CSS_SELECTOR, "input[type='file']"),
        ]
        for by, value in selectors:
            upload_el = wait_for_element(driver, by, value, timeout=5)
            if upload_el:
                print(f"Found upload input: {value}")
                break

        if not upload_el:
            driver.save_screenshot(str(BASE_DIR / "no_upload_input.png"))
            raise Exception("File upload input not found on page")

        driver.execute_script(
            "arguments[0].style.display = 'block';"
            "arguments[0].style.visibility = 'visible';"
            "arguments[0].style.opacity = '1';",
            upload_el
        )

        abs_path = str(RESUME_PATH.resolve())
        print(f"Uploading resume: {abs_path}")
        upload_el.send_keys(abs_path)

        # Dispatch change + input events so Naukri's JS picks it up
        driver.execute_script("""
            var input = arguments[0];
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('input', { bubbles: true }));
        """, upload_el)

        print("Waiting for upload to process...")
        time.sleep(10)

        # Click save button
        save_btn = wait_for_element(driver, By.XPATH, "//button[@type='button']", timeout=5)
        if save_btn:
            driver.execute_script("arguments[0].click();", save_btn)
            print("Clicked save button")
            time.sleep(5)
        else:
            print("No save button found — upload may be auto-saved")

        # ---------------- VERIFY ----------------
        checkpoint = wait_for_element(driver, By.XPATH, "//*[contains(@class, 'updateOn')]", timeout=10)
        if checkpoint:
            last_updated = checkpoint.text
            print(f"Profile last updated: {last_updated}")
            today1 = datetime.today().strftime("%b %d, %Y")
            today2 = datetime.today().strftime("%b %#d, %Y")
            if today1 in last_updated or today2 in last_updated:
                print("Resume updated successfully — today's date confirmed!")
            else:
                print(f"WARNING: Date mismatch. Expected {today1} or {today2}, got: {last_updated}")
        else:
            print("Could not find last-updated element")

    except Exception as e:
        print(f"Error: {e}")
        driver.save_screenshot(str(BASE_DIR / "error_screenshot.png"))
        raise
    finally:
        driver.quit()


if __name__ == "__main__":
    if random.random() < SKIP_CHANCE:
        skip_minutes = random.randint(MIN_INTERVAL, MAX_INTERVAL)
        print(f"Skipped this run (next ~{skip_minutes} min)")
        exit(0)

    if not RESUME_PATH.exists():
        raise FileNotFoundError(f"Resume not found: {RESUME_PATH}")

    FIREFOX_PROFILE.mkdir(exist_ok=True)
    update_naukri()
