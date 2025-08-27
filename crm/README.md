# CRM app Setup

This guide provides instructions to set up and run the CRM application, including installing dependencies, running migrations, starting Celery workers, and verifying logs.

Prerequisites

Python 3.8 or higher

Redis server

pip (Python package manager)

Virtual environment (recommended)

## Setup Instructions
### 1. Install Redis and Dependencies

Install Redis

Ubuntu/Debian:

`sudo apt update
sudo apt install redis-server`


macOS (Homebrew):

`brew install redis`


Windows (Chocolatey):

`choco install redis-64`


Start Redis

`redis-server`


Verify Redis is running:

`redis-cli ping`


Expected output:

`PONG
`

Set Up Python Virtual Environment

`python -m venv venv
source venv/bin/activate  
`


Install Project Dependencies

`pip install -r requirements.txt`

2. Run Database Migrations
`python manage.py migrate`

3. Start Celery Worker
`celery -A crm worker -l info`


Ensure the worker starts without errors and connects to Redis.

4. Start Celery Beat
`celery -A crm beat -l info`


This will schedule periodic tasks (e.g., weekly CRM reports).

5. Verify Logs

Check the log file:

`cat /tmp/crm_report_log.txt`


You should see something like:

=== 2025-08-27 06:00:00 ===
Report: 20 customers, 35 orders, 4999.50 revenue

Manual Test (Optional)

Run the task immediately without waiting for schedule:

`python manage.py shell`
>>> from crm.tasks import generate_crm_report
>>> generate_crm_report.delay()


Then check:

`cat /tmp/crm_report_log.txt`

Notes

Ensure Redis is running before starting Celery worker or Beat.

Use a process manager like supervisord or systemd in production to keep workers alive.

Troubleshooting

Redis not running:
`
ps aux | grep redis`


Celery not connecting to Redis:
Verify in crm/settings.py:

`CELERY_BROKER_URL = "redis://localhost:6379/0"`


Log file missing:
Ensure the Celery task is writing to /tmp/crm_report_log.txt.