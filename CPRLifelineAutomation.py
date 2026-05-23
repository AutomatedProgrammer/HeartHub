# main.py
# =======
# The orchestrator. Ties all modules together.
# Handles CLI arguments, the 5-step automation cycle, and monitoring mode.
#
# This is the file you actually run:
#   python main.py              — run full automation cycle
#   python main.py --dashboard  — show student dashboard
#   python main.py --remind     — send payment reminders only
#   python main.py --export     — export RQI CSV only
#   python main.py --upload     — export CSV and upload via SFTP
#   python main.py --monitor 5  — poll every 5 minutes continuously
#   python main.py --check      — dry run, check emails without sending
#   python main.py --add        — manually add a student

import argparse
import json
import os
import time
from config import PROJECT_DIR
from graph_auth import GraphAuth
from email_ops import EmailManager
from email_parser import parse_aha_enrollment, parse_acuity_appointment, identify_email_type
from student_tracker import StudentTracker


class CPRLifelineAutomation:
    def __init__(self):
        # Create instances of each module. This is where everything connects.
        self.auth = GraphAuth()
        self.email_mgr = EmailManager(self.auth)   # Pass auth into email manager
        self.tracker = StudentTracker()

        # Track which email IDs we've already processed so we don't
        # handle the same email twice on re-runs.
        # This is a set — like std::unordered_set in C++, no duplicates allowed.
        self.processed_file = os.path.join(PROJECT_DIR, "processed_emails.json")
        self.processed_ids = self._load_processed()

    def _load_processed(self):
        """Load the set of already-processed email IDs from disk."""
        if os.path.exists(self.processed_file):
            with open(self.processed_file, "r") as f:
                return set(json.load(f))  # set() for fast lookups
        return set()

    def _save_processed(self):
        """Save processed email IDs to disk."""
        with open(self.processed_file, "w") as f:
            # set isn't JSON-serializable, so convert to list first
            json.dump(list(self.processed_ids), f)

    def _is_processed(self, email_id):
        """Check if we've already handled this email."""
        return email_id in self.processed_ids

    def _mark_processed(self, email_id):
        """Mark an email as processed so we skip it next time."""
        self.processed_ids.add(email_id)
        self._save_processed()

    # ---- The 5-Step Automation Cycle ----

    def step1_check_enrollments(self, dry_run=False):
        """
        Step 1: Check inbox for AHA Atlas enrollment notification emails.
        These tell us new students have applied. We log them for the admin.
        """
        print("\n--- Step 1: Checking for AHA enrollment emails ---")
        emails = self.email_mgr.get_aha_emails()

        new_count = 0
        for email in emails:
            email_id = self.email_mgr.get_email_id(email)

            if self._is_processed(email_id):
                continue  # Already handled this one

            subject = self.email_mgr.get_email_subject(email)
            body = self.email_mgr.get_email_body(email)

            # Parse the email to extract course name and date
            parsed = parse_aha_enrollment(subject, body)

            if parsed:
                print(f"[ENROLLMENT] New request: {parsed['course']} on {parsed['date']}")
                new_count += 1

                if not dry_run:
                    self._mark_processed(email_id)
            # Silently skip emails that aren't AHA enrollments

        if new_count == 0:
            print("[ENROLLMENT] No new enrollment emails found.")
        else:
            print(f"[ENROLLMENT] Found {new_count} new enrollment notification(s).")

    def step2_send_welcome_emails(self, dry_run=False):
        """
        Step 2: Send welcome emails to students who haven't received one yet.
        """
        print("\n--- Step 2: Sending welcome emails ---")
        pending = self.tracker.get_pending_welcome()

        if not pending:
            print("[WELCOME] No pending welcome emails to send.")
            return

        for student in pending:
            name = f"{student['first_name']} {student['last_name']}"

            if dry_run:
                print(f"[WELCOME] Would send to: {name} ({student['email']})")
                continue

            # Send the email
            success = self.email_mgr.send_welcome_email(student)

            if success:
                # Mark it in the tracker so we don't send again
                self.tracker.mark_welcome_sent(student["email"])
                print(f"[WELCOME] Waiting 10s before next send...")
                time.sleep(10)

    def step3_check_payments(self, dry_run=False):
        """
        Step 3: Check inbox for Acuity Scheduling payment confirmations.
        Parse student info and mark them as paid.
        """
        print("\n--- Step 3: Checking for payment confirmations ---")
        emails = self.email_mgr.get_acuity_emails()

        new_payments = 0
        for email in emails:
            email_id = self.email_mgr.get_email_id(email)

            if self._is_processed(email_id):
                continue

            subject = self.email_mgr.get_email_subject(email)
            body = self.email_mgr.get_email_body(email)

            # Parse the Acuity email for student details
            parsed = parse_acuity_appointment(subject, body)

            if parsed:
                print(f"[PAYMENT] Found payment: {parsed.get('name', 'Unknown')} "
                      f"- ${parsed.get('paid_amount', '?')} at {parsed.get('location', '?')}")

                if not dry_run:
                    email_addr = parsed.get("email", "")

                    # Check if this student exists in our tracker
                    if self.tracker.check_duplicate(email_addr):
                        # Student exists — update their payment status
                        self.tracker.update_payment(
                            email_addr,
                            paid_amount=parsed.get("paid_amount", ""),
                            location=parsed.get("location", "")
                        )
                    else:
                        # New student we haven't seen — add them as already paid.
                        # This happens if admin didn't manually add them first.
                        name_parts = parsed.get("name", "").split(" ", 1)
                        first = name_parts[0] if name_parts else ""
                        last = name_parts[1] if len(name_parts) > 1 else ""

                        self.tracker.add_student(
                            first_name=first,
                            last_name=last,
                            email=email_addr,
                            phone=parsed.get("phone", ""),
                            course=parsed.get("course", ""),
                            location=parsed.get("location", "")
                        )
                        # Mark as paid immediately since they already paid
                        self.tracker.update_payment(
                            email_addr,
                            paid_amount=parsed.get("paid_amount", ""),
                            location=parsed.get("location", "")
                        )

                    self._mark_processed(email_id)
                    new_payments += 1
            else:
                # Silently skip emails that aren't Acuity appointments
                pass

        if new_payments == 0:
            print("[PAYMENT] No new payment confirmations found.")
        else:
            print(f"[PAYMENT] Processed {new_payments} new payment(s).")

    def step4_send_reminders(self, dry_run=False):
        """
        Step 4: Send payment reminders to students who enrolled 7+ days ago
        and haven't paid yet.
        """
        print("\n--- Step 4: Sending payment reminders ---")
        pending = self.tracker.get_pending_reminders()

        if not pending:
            print("[REMINDER] No students need reminders right now.")
            return

        for student in pending:
            name = f"{student['first_name']} {student['last_name']}"

            if dry_run:
                print(f"[REMINDER] Would remind: {name} ({student['email']})")
                continue

            success = self.email_mgr.send_reminder_email(student)

            if success:
                self.tracker.mark_reminder_sent(student["email"])
                print(f"[WELCOME] Waiting 10s before next send...")
                time.sleep(10)


    def step5_export_rqi(self, dry_run=False, upload=False):
        """
        Step 5: Export dashboard as AHA registration.
        Then export students for RQI registration.
        Then create a third for prepod.
        Then optionally upload prepod via SFTP.
        """
        print("\n--- Step 5: Exporting RQI data ---")

        if dry_run:
            unexported = self.tracker.get_unexported_paid()
            print(f"[RQI] Would export {len(unexported)} student(s).")
            self.tracker.export_aha_csv()
            self.tracker.export_rqi_csv()
            self.tracker.export_prepod_csv(dry_run=True)
            return

        self.tracker.export_aha_csv()
        self.tracker.export_rqi_csv()

        result = self.tracker.export_prepod_csv()

        if result and upload:
            self.tracker.upload_sftp()

    def run_full_cycle(self, dry_run=True, upload=False):
        """Run all 5 steps of the automation cycle."""
        print("\n" + "=" * 60)
        print("  CPR LIFELINE - FULL AUTOMATION CYCLE")
        print("=" * 60)

        if dry_run:
            print("  *** DRY RUN MODE — no emails will be sent ***\n")

        self.step1_check_enrollments(dry_run=dry_run)
        self.step2_send_welcome_emails(dry_run=dry_run)
        self.step3_check_payments(dry_run=dry_run)
        self.step4_send_reminders(dry_run=dry_run)
        self.step5_export_rqi(dry_run=dry_run, upload=upload)

        # Show the dashboard at the end
        self.tracker.print_dashboard()

        print("Cycle complete.\n")
        #print("=====================================")

    def run_monitor(self, interval_minutes, upload=False, dry_run=False):
        """
        Run the full cycle repeatedly, polling every N minutes.
        This is the continuous monitoring mode.

        Ctrl+C to stop.
        """
        print(f"\n[MONITOR] Starting continuous monitoring (every {interval_minutes} min)")

        try:
            while True:
                self.run_full_cycle(upload=upload, dry_run=dry_run)
                print(f"[MONITOR] Sleeping for {interval_minutes} minutes...")
                # time.sleep() takes seconds, so multiply minutes by 60
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            # Ctrl+C was pressed — exit gracefully
            print("\n[MONITOR] Stopped by user.")


def add_student_interactive(tracker):
    """
    Manually add a student via command-line prompts.
    Used with: python main.py --add
    """
    print("\n--- Add Student ---")
    first = input("First name: ").strip()
    last = input("Last name: ").strip()
    email = input("Email: ").strip()
    phone = input("Phone (optional): ").strip()
    course = input("Course (e.g. BLS Provider Course): ").strip()
    date = input("Course date (MM/DD/YYYY, optional): ").strip()

    if not first or not last or not email:
        print("[ERROR] First name, last name, and email are required.")
        return

    tracker.add_student(first, last, email, phone=phone, course=course, course_date=date)