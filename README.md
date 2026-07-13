# naukri_automation_resume

### Steps before running the script
  1. Install python3 virtual environment
     ```bash
     sudo apt install python3-venv
     ```
  2. Initialize python3 virtual environment in the project directory
     ```bash
     python3 -m venv venv
     ```
  3. Create a `.env` file with your Naukri Email and password like `.env.example`
  4. Run the script
     ```bash
     bash run_naukri.sh
     ```
  5. Create a cron job
     ```bash
     crontab -e
     ```

  6. Paste the following with the time of your choice and path of your project directory
  ```bash
      minutes hour * * * /path/to/naukri_automation_resume/run_naukri.sh >> /path/to/naukri_automation_resume/naukri_cron.log 2>&1
  ```
