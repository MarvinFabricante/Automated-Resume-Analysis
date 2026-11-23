"""Check iProgSMS configuration without sending unless --send-test is supplied."""
import argparse
import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
load_dotenv(BACKEND / ".env")
load_dotenv(BACKEND.parent / ".env")

from app.services.interview_service import (
    _send_sms_with_reason_sync,
    check_iprogsms_credits,
    check_iprogsms_message_status,
    detect_phone_network_iprogsms,
    format_phone_for_iprogsms,
    validate_iprogsms_content,
)

TEST_MESSAGE = "Mariwasa SMS integration test. This is a test message requested by you; no interview has been scheduled."


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phone", help="A test mobile number you control")
    parser.add_argument("--send-test", action="store_true", help="Send ONE test SMS (uses credits); no automatic retries")
    parser.add_argument("--message-id", help="Check a previously queued message without resending")
    args = parser.parse_args()
    if args.send_test and not format_phone_for_iprogsms(args.phone):
        parser.error("--send-test requires a valid Philippine mobile --phone")

    report = {"credits": check_iprogsms_credits()}
    if args.phone:
        report["network"] = detect_phone_network_iprogsms(args.phone)
        report["content"] = validate_iprogsms_content(TEST_MESSAGE)
    if args.send_test:
        if not report["credits"]["ok"] or not report["content"]["passed"]:
            report["send"] = {"queued": False, "error": "Resolve credits/content checks before sending."}
        else:
            accepted, error, message_id = _send_sms_with_reason_sync(args.phone, TEST_MESSAGE)
            report["send"] = {"queued": accepted, "message_id": message_id, "error": error}
            if message_id:
                report["status"] = check_iprogsms_message_status(message_id)
    if args.message_id:
        report["status"] = check_iprogsms_message_status(args.message_id)

    # Request exceptions can contain URLs with the API token; never print it.
    output = json.dumps(report, indent=2)
    token = os.getenv("IPROG_SMS_API_TOKEN", "")
    if token:
        output = output.replace(token, "[REDACTED]")
    print(output)
    return 0 if report["credits"]["ok"] and (not args.send_test or report["send"]["queued"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
