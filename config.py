# config.py
# =========
# This file holds every setting and credential the system needs.
# Other modules do: from config import TENANT_ID, CLIENT_ID, etc.
# That way if a credential changes, you only edit this one file.

import os
import json

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(PROJECT_DIR, "config.json"), "r") as f:
    config = json.load(f)

# --- Project Directory ---
# This anchors all file paths to wherever this config.py file lives.
# So no matter where you run "python main.py" from, files save to the project folder.


# --- Azure AD Credentials ---
# These 3 values are what MSAL needs to authenticate with Microsoft.
# Jonathan set these up when he registered the "sstreamliner" app.

TENANT_ID = "c8ad3954-f47c-41d5-bef2-c162a913b10d"
CLIENT_ID = "0ba3652b-3eeb-4620-b032-1bbbf2452a97"
CLIENT_SECRET = "HCZ8Q~VgXwqmQhn-POp-QM53Vt1WRBx4irgvpaG8"

# --- Microsoft Graph API ---
# This is the base URL for all Graph API calls.
# Every email read/send goes through this.

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# The mailbox we're monitoring and sending from.
MAILBOX = config["MAILBOX"]

# --- Email Sender Filters ---
# These are how we identify which emails are from AHA vs Acuity.
# We match on the "from" address when scanning the inbox.

AHA_SENDER = config["AHA_SENDER"]
ACUITY_SENDER = config["ACUITY_SENDER"]

# --- CPR Lifeline Info ---
# The booking link that goes in welcome emails.
LOCATIONS_URL = "https://cprlifeline.net/locations/"

# --- Reminder Settings ---
# How many days to wait before sending a payment reminder.
REMINDER_DAYS = config["REMINDER_DAYS"]

# --- File Paths ---
# Where we store our student "database" and exports.
# os.path.join() builds the path safely across Windows/Mac/Linux.
STUDENT_DB_FILE = os.path.join(PROJECT_DIR, "student_records.json")
PREPOD_EXPORT_FILE = os.path.join(PROJECT_DIR, "preprod_cl.csv")
AHA_EXPORT_FILE = os.path.join(PROJECT_DIR, "aha_registration.csv")
RQI_EXPORT_FILE = os.path.join(PROJECT_DIR, "rqi_registration.csv")

# --- SFTP Credentials (RQI 1Stop Preprod) ---
# For uploading the CSV to the RQI system.

SFTP_HOST = config["SFTP_HOST"]
SFTP_PORT = config["SFTP_PORT"]
SFTP_USERNAME = config["SFTP_USERNAME"]
SFTP_PASSWORD = config["SFTP_PASSWORD"]
SFTP_UPLOAD_PATH = config["SFTP_UPLOAD_PATH"]
SFTP_FILENAME = config["SFTP_FILENAME"]

#AHA Credentials
AHA_EMAIL = config["AHA_EMAIL"]
AHA_PASSWORD = config["AHA_PASSWORD"]

#Delay between webpage commands in seconds
DELAY = config["DELAY"]

#Dry run variable for the auto run option
DRY_RUN = config["DRY_RUN"]
UPLOAD = config["UPLOAD"]