# email_ops.py
# =============
# The email manager. Reads the Outlook inbox via Graph API,
# sends welcome and reminder emails.
#
# "requests" is Python's HTTP library. Every Graph API call is just:
#   requests.get(url, headers=headers)   — to READ data
#   requests.post(url, headers=headers, json=data)  — to SEND data
#
# The Graph API URLs follow a pattern:
#   GET  /users/{mailbox}/messages          — read inbox
#   POST /users/{mailbox}/sendMail          — send an email

import re
import requests
from config import GRAPH_BASE_URL, AHA_SENDER, ACUITY_SENDER, LOCATIONS_URL


class EmailManager:
    def __init__(self, auth):
        # auth is a GraphAuth object — we call auth.get_headers() to get the token.
        # We store it so every method in this class can use it.
        self.auth = auth
        # With delegated auth, we use /me instead of /users/{mailbox}
        # because the token belongs to the logged-in user directly.
        self.base_url = f"{GRAPH_BASE_URL}/me"

    # ---- Reading Emails ----

    def get_emails(self, sender_filter=None, limit=50):
        """
        Fetch emails from the inbox.

        sender_filter: only get emails from this sender address (optional)
        limit: max number of emails to fetch (Graph API calls this "$top")

        Returns a list of email dictionaries, or empty list on failure.
        """
        headers = self.auth.get_headers()

        # Fetch emails without server-side filtering.
        # Personal Outlook.com accounts don't support complex $filter queries,
        # so we fetch all emails and filter by sender in Python instead.
        url = f"{self.base_url}/mailFolders/inbox/messages?$top={limit}"

        try:
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                emails = data.get("value", [])

                # Filter by sender in Python if needed
                if sender_filter:
                    emails = [
                        e for e in emails
                        if e.get("from", {}).get("emailAddress", {}).get("address", "").lower()
                        == sender_filter.lower()
                    ]

                print(f"[EMAIL] Fetched {len(emails)} emails" +
                      (f" from {sender_filter}" if sender_filter else ""))
                return emails
            else:
                print(f"[EMAIL] Failed to fetch emails: {response.status_code}")
                print(f"[EMAIL] {response.text}")
                return []

        except Exception as e:
            print(f"[EMAIL] Error fetching emails: {e}")
            return []

    def get_aha_emails(self):
        """Fetch AHA Atlas enrollment notification emails."""
        return self.get_emails(sender_filter=AHA_SENDER)

    def get_acuity_emails(self):
        """Fetch Acuity Scheduling appointment confirmation emails."""
        return self.get_emails(sender_filter=ACUITY_SENDER)

    def get_email_body(self, email):
        """
        Extract the body text from a Graph API email object.

        Graph API emails have a "body" field with "contentType" (html or text)
        and "content" (the actual body text/html).
        If the body is HTML, we strip the tags to get clean plain text
        so the regex parsers can work correctly.
        """
        body = email.get("body", {})
        content = body.get("content", "")

        # Strip HTML tags to get plain text
        # First replace <br> and </div> with newlines to preserve line breaks
        text = re.sub(r'<br\s*/?>', '\n', content)
        text = re.sub(r'</div>', '\n', text)
        text = re.sub(r'</p>', '\n', text)
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        # Clean up excessive whitespace/newlines
        text = re.sub(r'\n\s*\n', '\n', text)
        return text.strip()

    def get_email_sender(self, email):
        """Extract the sender email address from a Graph API email object."""
        return email.get("from", {}).get("emailAddress", {}).get("address", "")

    def get_email_subject(self, email):
        """Extract the subject line from a Graph API email object."""
        return email.get("subject", "")

    def get_email_id(self, email):
        """Get the unique ID of an email (used to track which ones we've processed)."""
        return email.get("id", "")

    # ---- Sending Emails ----

    def send_email(self, to_email, subject, html_body):
        """
        Send an email via Graph API.

        to_email: recipient address
        subject: email subject line
        html_body: the email content as HTML

        Returns True if sent, False if failed.
        """
        headers = self.auth.get_headers()
        url = f"{self.base_url}/sendMail"

        # The Graph API expects this exact JSON structure for sending mail.
        # "message" contains the email details.
        # "saveToSentItems" puts a copy in the Sent folder.
        payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            },
            "saveToSentItems": True
        }

        try:
            # POST request to send the email.
            # json=payload automatically converts the dict to JSON
            # and sets the right Content-Type.
            response = requests.post(url, headers=headers, json=payload)

            # 202 = Accepted (Graph API returns 202 for sendMail, not 200)
            if response.status_code == 202:
                print(f"[EMAIL] Sent email to {to_email}: {subject}")
                return True
            else:
                print(f"[EMAIL] Failed to send to {to_email}: {response.status_code}")
                print(f"[EMAIL] {response.text}")
                return False

        except Exception as e:
            print(f"[EMAIL] Error sending email: {e}")
            return False

    def send_welcome_email(self, student):
        """
        Send a welcome email to a newly enrolled student.
        Contains a link to the CPR Lifeline locations page for booking.
        """
        first_name = student["first_name"]
        course = student.get("course", "your CPR course")

        subject = f"Welcome to CPR Lifeline – {course} Enrollment"

        # Minimal HTML template — you can style this later.
        html_body = f"""
        <html>
        <body>
            <p>Hi {first_name},</p>

            <p>Welcome to CPR Lifeline! You have been enrolled in <strong>{course}</strong>.</p>

            <p>To complete your registration, please visit our locations page to choose
            your preferred training site and schedule your class:</p>

            <p><a href="{LOCATIONS_URL}">{LOCATIONS_URL}</a></p>

            <p>If you have any questions, feel free to reach out to us.</p>

            <p>Thank you,<br>
            CPR Lifeline Team</p>
        </body>
        </html>
        """

        return self.send_email(student["email"], subject, html_body)

    def send_reminder_email(self, student):
        """
        Send a payment reminder to a student who hasn't paid after 7 days.
        """
        first_name = student["first_name"]
        course = student.get("course", "your CPR course")

        subject = f"Reminder: Complete Your CPR Lifeline Registration – {course}"

        html_body = f"""
        <html>
        <body>
            <p>Hi {first_name},</p>

            <p>This is a friendly reminder that your enrollment in <strong>{course}</strong>
            is still pending payment.</p>

            <p>Please visit our locations page to select your training site and
            complete your booking:</p>

            <p><a href="{LOCATIONS_URL}">{LOCATIONS_URL}</a></p>

            <p>If you've already completed this step, please disregard this message.</p>

            <p>Thank you,<br>
            CPR Lifeline Team</p>
        </body>
        </html>
        """

        return self.send_email(student["email"], subject, html_body)