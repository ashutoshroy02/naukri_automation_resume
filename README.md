# naukri_automation_resume

Automatically re-uploads your resume on Naukri to keep your profile fresh in recruiter search results. Runs on GitHub Actions (free, 24/7) with random intervals between 10-40 minutes.

> **Credit:** Forked from [itshoax/naukri_automation_resume](https://github.com/itshoax/naukri_automation_resume). Thanks to the original creator for the foundation.

## Features

- **GitHub Actions** — free, no machine needed, runs 24/7
- **Random interval** — 10-40 min between uploads (not fixed)
- **Naukri Campus support** — works for student profiles too
- **Upload verification** — confirms the resume date matches today
- **Auto geckodriver** — managed via `webdriver-manager`
- **Debug artifacts** — screenshots saved on failure

## Setup (GitHub Actions)

### 1. Fork this repo

### 2. Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**:
- `NAUKRI_EMAIL` — your Naukri login email
- `NAUKRI_PASSWORD` — your Naukri login password

### 3. Add your resume
Commit your resume PDF as `Your_Resume.pdf` in the repo root.

### 4. Enable Actions
Go to **Actions** tab → click **I understand my workflows, go ahead and enable them**.

### 5. Trigger manually
**Actions → Naukri Resume Upload → Run workflow**. Check the logs for `Resume updated successfully`.

The workflow runs automatically every 10 minutes (with ~75% skip chance for random intervals).

## Setup (Local / Cron)

### 1. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Create `.env`
```
EMAIL=your_email@example.com
PASSWORD=your_password
```

### 3. Run
```bash
bash run_naukri.sh
```

### 4. Cron (optional)
```bash
crontab -e
```
```
*/10 * * * * /path/to/run_naukri.sh >> /path/to/naukri_cron.log 2>&1
```

## How It Works

1. Logs into Naukri (handles session expiry)
2. Navigates to profile page
3. Finds the resume upload input (supports both regular Naukri and Naukri Campus)
4. Uploads `Your_Resume.pdf`
5. Verifies the upload date matches today
6. Repeats every 10-40 min (random)

## License

[GPL-3.0](LICENSE)
