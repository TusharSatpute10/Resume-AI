"""
ResumeAI - Interview Email Notification Service
Supports:
1. Interview scheduled
2. Interview rescheduled
3. Interview cancelled
4. Meeting link added
"""

import os
import ssl
import smtplib
import logging

from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from_email": os.getenv("SMTP_FROM_EMAIL", ""),
        "from_name": os.getenv("SMTP_FROM_NAME", "ResumeAI"),
        "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        "use_ssl": os.getenv("SMTP_USE_SSL", "false").lower() == "true",
    }


def get_interview_details(interview):
    application = getattr(interview, "application", None)

    student = getattr(application, "student", None) if application else None
    user = getattr(student, "user", None) if student else None

    job = getattr(application, "job", None) if application else None
    company = getattr(job, "company", None) if job else None

    meeting_link = getattr(interview, "meeting_link", None)
    link_status = getattr(interview, "meeting_link_status", "PENDING")

    interview_type = getattr(interview, "interview_type", "ONLINE")

    if interview_type == "ONLINE":
        location = (
            meeting_link
            if meeting_link and link_status == "AVAILABLE"
            else "Meeting link pending. It will be shared by the recruiter."
        )
    else:
        location = (
            getattr(interview, "venue", None)
            or "Venue to be shared by the recruiter."
        )

    scheduled_at = getattr(interview, "scheduled_at", None)

    formatted_date = (
        scheduled_at.strftime("%A, %d %B %Y at %I:%M %p")
        if scheduled_at
        else "Not specified"
    )

    return {
        "recipient": getattr(user, "email", "") or "",
        "student_name": getattr(student, "full_name", "Candidate"),
        "job_title": getattr(job, "title", "Position"),
        "company_name": getattr(company, "name", "Hiring Company"),
        "round_name": getattr(interview, "round_name", "Interview"),
        "date_time": formatted_date,
        "duration": getattr(interview, "duration_minutes", 30),
        "interview_type": interview_type,
        "location": location,
        "instructions": (
            getattr(interview, "instructions", None)
            or "No additional instructions."
        ),
        "status": getattr(interview, "status", "SCHEDULED"),
    }


def send_interview_notification(interview, event):
    """
    Send interview notification email.

    Events:
        scheduled
        rescheduled
        cancelled
        meeting_link_added

    Returns:
        True  = Email sent successfully
        False = Email failed or SMTP is not configured
    """

    details = get_interview_details(interview)

    if not details["recipient"]:
        logger.warning("Candidate email address not found.")
        return False

    event = event.strip().lower()

    subjects = {
        "scheduled": (
            f"Interview Scheduled - {details['company_name']}"
        ),
        "rescheduled": (
            f"Interview Rescheduled - {details['company_name']}"
        ),
        "cancelled": (
            f"Interview Cancelled - {details['company_name']}"
        ),
        "meeting_link_added": (
            f"Interview Meeting Link - {details['company_name']}"
        ),
    }

    headings = {
        "scheduled": "Your interview has been scheduled.",
        "rescheduled": "Your interview has been rescheduled.",
        "cancelled": "Your interview has been cancelled.",
        "meeting_link_added": "Your meeting link is now available.",
    }

    if event not in subjects:
        logger.error("Invalid interview email event: %s", event)
        return False

    config = get_smtp_config()

    if not config["host"] or not config["from_email"]:
        logger.warning("SMTP is not configured. Email skipped.")
        return False

    lines = [
        f"Position: {details['job_title']}",
        f"Company: {details['company_name']}",
        f"Interview Round: {details['round_name']}",
    ]

    if event == "cancelled":
        lines.append(f"Status: {details['status']}")
    else:
        lines.extend([
            f"Date and Time: {details['date_time']}",
            f"Duration: {details['duration']} minutes",
            f"Mode: {details['interview_type']}",
            f"Meeting Link / Venue: {details['location']}",
            f"Instructions: {details['instructions']}",
        ])

    body = (
        f"Hello {details['student_name']},\n\n"
        f"{headings[event]}\n\n"
        + "\n".join(lines)
        + f"\n\nRegards,\n{config['from_name']}"
    )

    message = EmailMessage()

    message["Subject"] = subjects[event]
    message["From"] = (
        f"{config['from_name']} <{config['from_email']}>"
    )
    message["To"] = details["recipient"]

    message.set_content(body)

    try:
        if config["use_ssl"]:
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(
                config["host"],
                config["port"],
                context=context,
                timeout=20
            ) as server:

                if config["username"]:
                    server.login(
                        config["username"],
                        config["password"]
                    )

                server.send_message(message)

        else:
            with smtplib.SMTP(
                config["host"],
                config["port"],
                timeout=20
            ) as server:

                server.ehlo()

                if config["use_tls"]:
                    server.starttls(
                        context=ssl.create_default_context()
                    )
                    server.ehlo()

                if config["username"]:
                    server.login(
                        config["username"],
                        config["password"]
                    )

                server.send_message(message)

        logger.info(
            "Interview email sent successfully. Event: %s",
            event
        )

        return True

    except Exception:
        logger.exception(
            "Failed to send interview notification."
        )

        return False