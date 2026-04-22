import asyncio
import json
import os
import httpx
import sys

from email_system import verify_emails_batch, get_send_decision

BATCH_ID      = os.environ["BATCH_ID"]
EMAILS_JSON   = os.environ["EMAILS_JSON"]
FROM_DOMAIN   = os.environ.get("FROM_DOMAIN", "gmail.com")
SERVER_URL    = os.environ["SERVER_URL"]
SERVER_SECRET = os.environ["SERVER_SECRET"]

CHUNK_SIZE = 50


async def main():
    emails_with_data = json.loads(EMAILS_JSON)

    emails_only = [e["email"] for e in emails_with_data]
    data_map    = {e["email"]: e for e in emails_with_data}

    all_results = []

    for i in range(0, len(emails_only), CHUNK_SIZE):
        chunk = emails_only[i:i + CHUNK_SIZE]

        verified = await verify_emails_batch(chunk)

        for v in verified:
            decision  = get_send_decision(v)
            lead_data = data_map.get(v.email, {})

            all_results.append({
                "email": v.email,
                "email_status": v.status,
                "verification_level": v.level,
                "verification_reason": v.reason,
                "decision": decision.decision,
                "name": lead_data.get("name"),
                "phone": lead_data.get("phone"),
                "company": lead_data.get("company"),
            })

    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{SERVER_URL}/api/batches/{BATCH_ID}/import-verified",
            json={"results": all_results},
            headers={"x-secret": SERVER_SECRET}
        )

    if r.status_code != 200:
        sys.exit(1)


asyncio.run(main())