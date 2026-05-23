Created by AutomatedProgrammer, MintMap, and Jllemons.

Project Overview
Program provides an AHA script that will auto approve students on the AHA website. It also reads the user's email inbox for AHA signups. It takes the AHA sign up students and sends a reminder email for them to pay for the courses. It also checks the inbox for payment emails. The collected students are stored into a database for export into three CSV files. The AHA registration CSV for students that have registered on the AHA website. A RQI registration csv for students who have registered and paid for their classes. And a prepod CSV that syncs the students who have recently paid to the sftp server. This is all done in one single process, which can be set to auto run every X minutes.

INSTALLION 
Download the release folder and go into the dist folder to find the exe. You'll need to input your information into the config file before running. Config file is in dist\AHAEmailProgram\_internal. It is named config.json.

KNOWN ISSUES
Adding students from the AHA website requires the program to be closed and reopened again for the database to update.

Button Instructions
Run AHA Script - Enter the date range for students to approve. Runs a script that automatically approves students and adds them
to the database.
Add Student - Manually add a student to the database file.
Display Dashboard - Displays the database.
Set Auto Run - Set the interval for the program to refresh and read/send emails (full cycle). Interval is accepted in minutes only.
Export CSVs - Export the AHA registration, RQI registration, and prepod csvs.
Export AHA - Export AHA registration.
Export RQI - Export RQI registration.
Export Prepod - Export prepod, DOES NOT SYNC to scp.
Dry Run - Run a test run of the program without sending emails. This needs to be in full number intervals, 1,2,3,4,5.
Full Cycle - Perform email operations, export csvs and sync to scp server.
Config file is in dist\AHAEmailProgram\_internal. It is named config.json.
CSVs are exported to dist\AHAEmailProgram\_internal.

Config Instructions
MAILBOX - Email to be read for emails.
AHA_SENDER - Email that is sending AHA emails to the mailbox.
ACUITY_SENDER - Email that is sending Acuity emails to the mailbox.
REMINDER_DAYS - Day interval before sending reminder emails.
SFTP_HOST - Host link.
SFTP_PORT - SFTP Port.
SFTP_USERNAME - SFTP Username.
SFTP_PASSWORD - SFTP Password.
SFTP_UPLOAD_PATH - Upload path for the SFTP.
SFTP_FILENAME - Name of the csv to sync to sftp.
AHA_EMAIL - Email to login to the aha interface to approve students.
AHA_PASSWORD - AHA password to login to aha interface to approve students.
DELAY - Delay in seconds between script operations, increase value if the aha student approve script breaks.
DRY_RUN - Sets the auto run function to run the full cycle without sending emails. Leave false to send emails.
UPLOAD - Sets the auto run function to run the full cycle and sync to sftp. Leave true to sync.
