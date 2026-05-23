# student_tracker.py
# ===================
# The "database" layer. Stores student records in a JSON file,
# handles lookups, status updates, duplicate detection, CSV export,
# SFTP upload, and the dashboard display.
#
# JSON storage means: we load the file into a Python list of dictionaries,
# modify it in memory, then write it back to disk. Simple but effective.

import json
import csv
import os
import paramiko
from datetime import datetime
from config import (
    STUDENT_DB_FILE, PREPOD_EXPORT_FILE, REMINDER_DAYS,
    SFTP_HOST, SFTP_PORT, SFTP_USERNAME, SFTP_PASSWORD,
    SFTP_UPLOAD_PATH, SFTP_FILENAME, AHA_EXPORT_FILE, RQI_EXPORT_FILE
)

import sys

class StudentTracker:
    def __init__(self):
        # Load existing records from the JSON file, or start with empty list.
        # This runs when you do: tracker = StudentTracker()
        self.students = self._load_db()

    # ---- Private helper methods (start with _ by convention) ----

    def _load_db(self):
        """Load student records from JSON file. Returns empty list if file doesn't exist."""
        # os.path.exists() checks if the file is on disk — like checking
        # if a file exists before fopen() in C.
        if os.path.exists(STUDENT_DB_FILE):
            # "with open(...) as f" opens the file and auto-closes it when done.
            # No need to manually call f.close(). It's like RAII in C++.
            with open(STUDENT_DB_FILE, "r") as f:
                return json.load(f)  # Parses the JSON text into a Python list
        return []

    def _save_db(self):
        """Write current student records back to JSON file."""
        with open(STUDENT_DB_FILE, "w") as f:
            # json.dump() converts the Python list back to JSON text.
            # indent=2 makes it human-readable (not all on one line).
            json.dump(self.students, f, indent=2)

    # ---- Core operations ----

    def check_duplicate(self, email):
        """Check if a student with this email already exists."""
        # any() returns True if at least one item matches the condition.
        # The C++ equivalent would be:
        #   for (auto& s : students) { if (s.email == email) return true; }
        return any(s["email"].lower() == email.lower() for s in self.students)

    def add_student(self, first_name, last_name, email, phone="", course="",
                    course_date="", location=""):
        """
        Add a new student to the tracker.
        Returns True if added, False if duplicate.
        """
        if self.check_duplicate(email):
            print(f"[TRACKER] Duplicate detected: {email}")
            return False

        # A student record is just a dictionary with all their info and status flags.
        # This mirrors the columns from the AHA Student Registration Google Sheet.
        student = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "course": course,
            "course_date": course_date,
            "location": location,
            "enrollment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "paid": False,
            "paid_amount": "",
            "welcome_email_sent": False,
            "reminder_email_sent": False,
            "reminder_date": "",
            "rqi_exported": False
        }

        self.students.append(student)  # Add to the in-memory list
        self._save_db()                # Write to disk
        print(f"[TRACKER] Added student: {first_name} {last_name} ({email})")
        return True

    def update_payment(self, email, paid_amount="", location=""):
        """Mark a student as paid and update their location/amount."""
        for student in self.students:
            if student["email"].lower() == email.lower():
                student["paid"] = True
                student["paid_amount"] = paid_amount
                if location:
                    student["location"] = location
                self._save_db()
                print(f"[TRACKER] Payment recorded for: {email}")
                return True

        print(f"[TRACKER] Student not found for payment update: {email}")
        return False

    def mark_welcome_sent(self, email):
        """Mark that the welcome email has been sent to this student."""
        for student in self.students:
            if student["email"].lower() == email.lower():
                student["welcome_email_sent"] = True
                self._save_db()
                return True
        return False

    def mark_reminder_sent(self, email):
        """Mark that a payment reminder has been sent."""
        for student in self.students:
            if student["email"].lower() == email.lower():
                student["reminder_email_sent"] = True
                student["reminder_date"] = datetime.now().strftime("%Y-%m-%d")
                self._save_db()
                return True
        return False

    # ---- Query methods ----

    def get_pending_welcome(self):
        """Get students who haven't received a welcome email yet."""
        return [s for s in self.students if not s["welcome_email_sent"]]

    def get_pending_reminders(self):
        """
        Get students who need a payment reminder:
        - Enrolled 7+ days ago
        - Haven't paid
        - Haven't already been reminded
        """
        reminders = []
        now = datetime.now()

        for student in self.students:
            if student["paid"] or student["reminder_email_sent"]:
                continue  # Skip paid students and already-reminded ones

            # Parse the enrollment date string back into a datetime object
            # so we can do math with it (how many days ago was it?)
            enrolled = datetime.strptime(student["enrollment_date"], "%Y-%m-%d %H:%M:%S")
            days_since = (now - enrolled).days  # .days gives us whole days difference

            if days_since >= REMINDER_DAYS:
                reminders.append(student)

        return reminders

    def get_paid_students(self, location=None):
        """
        Get all students who have paid.
        If location is given, filter to only that location.
        """
        paid = [s for s in self.students if s["paid"]]
        if location:
            paid = [s for s in paid if location.lower() in s["location"].lower()]
        return paid

    def get_unexported_paid(self, location=None):
        """Get paid students who haven't been exported to RQI yet."""
        unexported = [s for s in self.students if s["paid"] and not s["rqi_exported"]]
        if location:
            unexported = [s for s in unexported if location.lower() in s["location"].lower()]
        return unexported

    def get_all_locations(self):
        """Get a list of all unique locations in the tracker."""
        # set() removes duplicates automatically — like std::set in C++
        locations = set()
        for s in self.students:
            if s["location"]:
                locations.add(s["location"])
        return sorted(locations)  # sorted() returns an alphabetically sorted list

    #EXPORT AHA REGISTRATION

    def export_aha_csv(self):
        with open(AHA_EXPORT_FILE, "w", newline="") as f: 
            writer = csv.DictWriter(f, fieldnames=[
                "EMAIL", "First Name", "M", "Last Name", "Phone", "Course", "Date", "Acuity Regist.", "AHA Regist.", "Reminder Email Sent"
            ])
            writer.writeheader()
            students = self.students
            for student in students:
                writer.writerow({
                    "EMAIL": student["email"],
                    "First Name": student["first_name"],
                    "M": "",
                    "Last Name": student["last_name"],
                    "Phone": student["phone"],
                    "Course": student["course"],
                    "Date": student["course_date"],
                    "Acuity Regist.": student["paid"],
                    "AHA Regist.": True,
                    "Reminder Email Sent": student["reminder_email_sent"]
                })

            print("Exported AHA CSV to " + os.path.dirname(os.path.abspath(sys.argv[0])))

    def export_rqi_csv(self):
        with open(RQI_EXPORT_FILE, "w", newline="") as f: 
            writer = csv.DictWriter(f, fieldnames=[
                "LocationID", "LocationName", "UserID", "FirstName", "MiddleName", "LastName", 
                "Email", "JobCode", "JobName", "HireDate", "Status", "DateOfBirth", "Gender", "YearsofExperience",
                "ActiveDate", "InactiveDate", "Group"
            ])
            writer.writeheader()
            students = self.students
            for student in students:
                if student["paid"]:
                    location = student["location"].rsplit(',', 2)
                    city = location[-2].strip()
                    state = location[-1].strip().split(' ')[0]
                    writer.writerow({
                    "LocationID": "",
                    "LocationName": f"{city}, {state}",
                    "UserID": student["email"],
                    "FirstName": student["first_name"],
                    "MiddleName": "",
                    "LastName": student["last_name"],
                    "Email": student["email"],
                    "JobCode": "",
                    "JobName": "",
                    "HireDate": "",
                    "Status": "Active" if student["paid"] else "",
                    "DateOfBirth": "",
                    "Gender": "",
                    "YearsofExperience": "",
                    "ActiveDate": "",
                    "InactiveDate": "",
                    "Group": student["course"]
                })
            print("Exported RQI CSV to " + os.path.dirname(os.path.abspath(sys.argv[0])))
                

    # ---- Export and Upload ----

    def export_prepod_csv(self, location=None, dry_run=False):
        """
        Export paid students to a CSV file for RQI 1Stop demographic import.
        File must be named preprod_cl.csv exactly.
        Only includes students not yet exported (delta file).
        Optionally filter by location.
        """
        students_to_export = self.get_unexported_paid(location=location)

        if not students_to_export:
            print("[TRACKER] No new paid students to export.")
            return None

        # csv.DictWriter writes dictionaries as CSV rows.
        # fieldnames = the column headers.
        with open(PREPOD_EXPORT_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "LocationID", "LocationName", "UserID", "FirstName", "MiddleName", "LastName", 
                "Email", "JobCode", "JobName", "HireDate", "Status", "DateOfBirth", "Gender", "YearsofExperience",
                "ActiveDate", "InactiveDate", "Group"
            ])
            writer.writeheader()  # Writes the column header row

            for student in students_to_export:
                if student["paid"] != True:
                    continue
                location = student["location"].rsplit(',', 2)
                city = location[-2].strip()
                state = location[-1].strip().split(' ')[0]
                writer.writerow({
                    "LocationID": "",
                    "LocationName": f"{city}, {state}",
                    "UserID": student["email"],
                    "FirstName": student["first_name"],
                    "MiddleName": "",
                    "LastName": student["last_name"],
                    "Email": student["email"],
                    "JobCode": "",
                    "JobName": "",
                    "HireDate": "",
                    "Status": "Active" if student["paid"] else "",
                    "DateOfBirth": "",
                    "Gender": "",
                    "YearsofExperience": "",
                    "ActiveDate": "",
                    "InactiveDate": "",
                    "Group": student["course"]
                })
                if dry_run == False:
                    student["rqi_exported"] = True  # Mark as exported

        self._save_db()
        print(f"[TRACKER] Exported {len(students_to_export)} students to {PREPOD_EXPORT_FILE}")
        return PREPOD_EXPORT_FILE

    def upload_sftp(self):
        """Upload the RQI CSV to the SFTP server."""
        if not os.path.exists(PREPOD_EXPORT_FILE):
            print("[TRACKER] No CSV file to upload. Run export first.")
            return False

        try:
            # Connect to the SFTP server (like connecting to a game server)
            transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
            transport.connect(username=SFTP_USERNAME, password=SFTP_PASSWORD)

            # Open an SFTP session over the connection
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Build the full remote path: /uploads/116286/preprod_cl.csv
            remote_path = f"{SFTP_UPLOAD_PATH}/{SFTP_FILENAME}"

            # Upload the file
            sftp.put(PREPOD_EXPORT_FILE, remote_path)
            print(f"[TRACKER] Uploaded {PREPOD_EXPORT_FILE} to {remote_path}")

            # Clean up
            sftp.close()
            transport.close()
            return True

        except Exception as e:
            # If anything goes wrong (connection refused, bad password, etc.)
            print(f"[TRACKER] SFTP upload failed: {e}")
            return False

    # ---- Dashboard ----

    def print_dashboard(self, location=None):
        """
        Print a summary of all students and their statuses.
        Optionally filter by location.
        """
        # Filter by location if specified
        if location:
            students = [s for s in self.students if location.lower() in s["location"].lower()]
            location_label = f" ({location})"
        else:
            students = self.students
            location_label = ""

        total = len(students)
        paid = len([s for s in students if s["paid"]])
        unpaid = total - paid
        welcomed = len([s for s in students if s["welcome_email_sent"]])
        reminded = len([s for s in students if s["reminder_email_sent"]])
        exported = len([s for s in students if s["rqi_exported"]])

        print("\n" + "=" * 60)
        print(f"       CPR LIFELINE - STUDENT DASHBOARD{location_label}")
        print("=" * 60)
        print(f"  Total Students:    {total}")
        print(f"  Paid:              {paid}")
        print(f"  Unpaid:            {unpaid}")
        print(f"  Welcome Sent:      {welcomed}")
        print(f"  Reminders Sent:    {reminded}")
        print(f"  RQI Exported:      {exported}")
        print("=" * 60)

        # Print individual student details if there are any
        if students:
            print(f"\n  {'NAME':<25} {'EMAIL':<30} {'LOCATION':<20} {'PAID':<8}")
            print("-" * 85)
            for s in students:
                name = f"{s['first_name']} {s['last_name']}"
                paid_str = "YES" if s["paid"] else "NO"
                loc = s["location"][:18] if s["location"] else "N/A"
                print(f"  {name:<25} {s['email']:<30} {loc:<20} {paid_str:<8}")

        # Show all locations if not filtering
        if not location:
            locations = self.get_all_locations()
            if locations:
                print(f"\n  Locations: {', '.join(locations)}")

        print()
