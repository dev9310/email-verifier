import re
import asyncio
import smtplib
import socket
import dns.resolver
from dataclasses import dataclass
from typing import Optional

# =========================
# DATA MODELS
# =========================

@dataclass
class VerifyResult:
    email: str
    status: str
    level: int
    reason: str
    detail: Optional[str] = None
    mx_used: Optional[str] = None
    smtp_code: Optional[int] = None


@dataclass
class SendDecision:
    decision: str
    safe: bool


# =========================
# SYNTAX CHECK
# =========================

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def check_syntax(email):
    return bool(EMAIL_REGEX.match(email))


# =========================
# DNS + MX CHECK
# =========================

def get_mx_records(domain):
    try:
        answers = dns.resolver.resolve(domain, "MX")
        return [str(r.exchange).rstrip('.') for r in answers]
    except:
        return []


# =========================
# SMTP CHECK
# =========================

def smtp_check(email, mx_host):
    try:
        server = smtplib.SMTP(timeout=10)
        server.connect(mx_host, 25)
        server.helo()

        server.mail("test@example.com")
        code, _ = server.rcpt(email)

        server.quit()

        if code == 250:
            return "valid", code
        elif code >= 500:
            return "invalid", code
        else:
            return "risky", code

    except:
        return "risky", None


# =========================
# VERIFY SINGLE EMAIL
# =========================

async def verify_email(email):
    email = email.strip().lower()

    # Level 1: Syntax
    if not check_syntax(email):
        return VerifyResult(email, "invalid", 1, "bad_syntax")

    domain = email.split("@")[1]

    # Level 2: MX
    mx_records = await asyncio.to_thread(get_mx_records, domain)

    if not mx_records:
        return VerifyResult(email, "invalid", 2, "no_mx")

    # Level 3: SMTP
    status, code = await asyncio.to_thread(smtp_check, email, mx_records[0])

    if status == "valid":
        return VerifyResult(email, "valid", 3, "mailbox_exists", smtp_code=code)

    if status == "invalid":
        return VerifyResult(email, "invalid", 3, "mailbox_not_found", smtp_code=code)

    return VerifyResult(email, "risky", 3, "unknown", smtp_code=code)


# =========================
# BATCH VERIFY
# =========================

async def verify_emails_batch(emails, concurrency=5):
    sem = asyncio.Semaphore(concurrency)

    async def worker(e):
        async with sem:
            return await verify_email(e)

    return await asyncio.gather(*[worker(e) for e in emails])


# =========================
# DECISION ENGINE
# =========================

def get_send_decision(result: VerifyResult) -> SendDecision:
    if result.status == "valid":
        return SendDecision("send", True)

    if result.status == "risky":
        return SendDecision("review", True)

    return SendDecision("discard", False)