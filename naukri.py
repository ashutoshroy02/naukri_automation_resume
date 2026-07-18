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

MIN_INTERVAL = 360   # 6 hours in minutes
MAX_INTERVAL = 720   # 12 hours in minutes
SKIP_CHANCE = 1 - (MIN_INTERVAL / MAX_INTERVAL)  # ~0.5

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

        # Find file input — handles both regular Naukri and Naukri Campus
        upload_el = None
        selectors = [
            (By.CSS_SELECTOR, "input[type='file'].upload-input"),
            (By.CSS_SELECTOR, "input[type='file']"),
            (By.ID, "attachCV"),
            (By.ID, "lazyAttachCV"),
        ]
        for by, value in selectors:
            upload_el = wait_for_element(driver, by, value, timeout=5)
            if upload_el:
                print(f"Found upload input: {value}")
                break

        if not upload_el:
            driver.save_screenshot(str(BASE_DIR / "no_upload_input.png"))
            raise Exception("File upload input not found on page")

        # Click "Update resume" button if present (Naukri Campus)
        try:
            update_btn = driver.find_element(By.CSS_SELECTOR, "button.upload-button")
            driver.execute_script("arguments[0].click();", update_btn)
            print("Clicked 'Update resume' button")
            time.sleep(2)
        except Exception:
            pass

        # Make inputs visible and re-find file input
        driver.execute_script("""
            var inputs = document.querySelectorAll("input[type='file']");
            for (var i = 0; i < inputs.length; i++) {
                inputs[i].style.display = 'block';
                inputs[i].style.visibility = 'visible';
                inputs[i].style.opacity = '1';
            }
        """)

        abs_path = str(RESUME_PATH.resolve())
        print(f"Uploading resume: {abs_path}")

        # Re-find with fresh reference to avoid stale element
        upload_el = driver.find_element(By.CSS_SELECTOR, "input[type='file'].upload-input")
        upload_el.send_keys(abs_path)

        print("Waiting for upload to process...")
        time.sleep(10)

        # ---------------- VERIFY ----------------
        today = datetime.today().strftime("%b %#d, %Y")
        try:
            date_el = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".uploaded-date"))
            )
            last_updated = date_el.text
            print(f"Resume status: {last_updated}")
            if today in last_updated:
                print("Resume updated successfully — today's date confirmed!")
            else:
                print(f"WARNING: Not today. Got: {last_updated}, expected: {today}")
        except Exception:
            # Fallback: check updateOn class (regular Naukri)
            checkpoint = wait_for_element(driver, By.XPATH, "//*[contains(@class, 'updateOn')]", timeout=5)
            if checkpoint:
                last_updated = checkpoint.text
                print(f"Profile last updated: {last_updated}")
            else:
                print("Could not verify upload date")

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
