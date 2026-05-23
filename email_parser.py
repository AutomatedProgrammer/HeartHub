# email_parser.py
# ================
# Parses raw email data from AHA Atlas and Acuity Scheduling.
# Takes in email subject + body, returns structured data (dictionaries).
#
# "re" is Python's regex module. Regex = pattern matching on characters.
# Example: re.search(r"Name: (.+)", text) finds "Name: Karissa Shields"
# and captures "Karissa Shields" in group(1).

import re


def parse_aha_enrollment(subject, body):
    """
    Parse an AHA Atlas enrollment notification email.

    What we're looking for in the body:
    "...enrollment requests for BLS Provider Course on 02/09/2026"

    Returns a dict like:
    {"course": "BLS Provider Course", "date": "02/09/2026"}
    or None if we can't parse it.
    """
    if "New Appointment" in subject:
        return None
    result = {}

    # This regex looks for: "requests for <COURSE NAME> on <DATE>"
    # (.+?) = capture any characters (non-greedy, stop as soon as possible)
    # (\d{2}/\d{2}/\d{4}) = capture a date in MM/DD/YYYY format
    #   \d = any digit, {2} = exactly 2 of them
    match = re.search(r"enrollment requests for (.+?) on (\d{2}/\d{2}/\d{4})", body)

    if match:
        result["course"] = match.group(1)  # First captured group = course name
        result["date"] = match.group(2)    # Second captured group = date
        return result

    return None


def parse_acuity_appointment(subject, body):
    """
    Parse an Acuity Scheduling appointment confirmation email.

    Subject looks like:
    "New Appointment: ACLS Skills Check Only (Karissa Shields) on Wednesday,
     February 4, 2026 4:00pm CST with CPR Lifeline, Nashville, Film House"

    Body has labeled fields:
    Name: Karissa Shields
    Phone: +17024805547
    Email: something@gmail.com
    Price: $150.00
    Paid Online: $150.00
    Location
    ----------
    810 Dominican Dr., Suite 116A, Nashville, TN 37226

    Returns a dict with all the parsed fields, or None.
    """
    result = {}

    # --- Parse the subject line first ---
    # Grab the course type and student name from the subject.
    # Pattern: "New Appointment: <COURSE> (<NAME>) on ..."
    subj_match = re.search(r"New Appointment:\s*(.+?)\s*\((.+?)\)\s*on", subject)
    if subj_match:
        result["course"] = subj_match.group(1).strip()
        result["name"] = subj_match.group(2).strip()

    # --- Parse the body for detailed info ---

    # Name: <value>
    name_match = re.search(r"Name:\s*(.+)", body)
    if name_match:
        result["name"] = name_match.group(1).strip()

    # Phone: <value>
    phone_match = re.search(r"Phone:\s*(.+)", body)
    if phone_match:
        result["phone"] = phone_match.group(1).strip()

    # Email: <value>
    email_match = re.search(r"Email:\s*(.+)", body)
    if email_match:
        result["email"] = email_match.group(1).strip()

    # Price: $<value>
    price_match = re.search(r"Price:\s*\$?([\d.]+)", body)
    if price_match:
        result["price"] = price_match.group(1)

    # Paid Online: $<value>
    paid_match = re.search(r"Paid Online:\s*\$?([\d.]+)", body)
    if paid_match:
        result["paid_amount"] = paid_match.group(1)

    # Location is on its own line, followed by dashes, then the address.
    # We look for "Location" then skip the dashes and grab the next line.
    loc_match = re.search(r"Location\s*[-]+\s*(.+)", body, re.DOTALL)
    if loc_match:
        # Take just the first line after the dashes (the actual address)
        location_text = loc_match.group(1).strip().split("\n")[0].strip()
        result["location"] = location_text

    # Only return if we got at least a name and email
    if "name" in result and "email" in result:
        return result

    return None


def identify_email_type(sender, subject):
    """
    Looks at who sent the email and returns what type it is.
    This is how the system knows which parser to use.

    Returns: "aha_enrollment", "acuity_appointment", or "unknown"
    """
    # .lower() converts to lowercase so matching isn't case-sensitive
    sender_lower = sender.lower()

    if "no-eccreply@heart.org" in sender_lower:
        return "aha_enrollment"
    elif "acuityscheduling" in sender_lower:
        return "acuity_appointment"
    else:
        return "unknown"
