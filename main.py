# main.py
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv
from gmail_handler import authenticate_gmail, get_unread_emails, send_reply, mark_as_read
from rag_engine import load_knowledge_base, build_faiss_index, search_kb

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.5-flash")

# Load KB and build FAISS index once at startup
print("📚 Loading Knowledge Base...")
docs = load_knowledge_base("knowledge_base")
index, _ = build_faiss_index(docs)
print(f"✅ Loaded {len(docs)} KB chunks into FAISS index.")

# def generate_reply(email_body, context):
#     prompt = f"""You are a helpful customer support assistant.
# Answer the user's question ONLY using the provided context below.
# If the answer is not found in the context, respond with:
# "Thank you for reaching out! I'll get back to you shortly."

# Context from Knowledge Base:
# {context}

# User Email:
# {email_body}

# Write a polite, concise reply:"""
#     response = gemini_model.generate_content(prompt)
#     return response.text

def extract_first_name(sender):
    # Extract name from "Karthika Ramasamy <email@gmail.com>" format
    print("sender:", sender)
    if "<" in sender:
        full_name = sender.split("<")[0].strip()
    else:
        full_name = sender.split("@")[0].strip()
    first_name = full_name.split()[0] if full_name else "there"
    return first_name

def generate_reply(email_body, context, sender_name="there"):
    trimmed_body = " ".join(email_body.split()[:500])

    prompt = f"""You are a professional and friendly customer support representative at AlgoAcademy.

Your job is to write a warm, well-formatted email reply to a prospective student.

Rules:
- Start with: "Dear {sender_name},"
- Answer ONLY using the provided context below
- Use clear paragraphs, no bullet points in the email body
- If the answer is not in the context, write: "Thank you for your interest! Our team will get back to you shortly with more details."
- End EVERY reply with this exact signature:

Warm regards,
AlgoAcademy Support Team
# 📧 support@algoacademy.com
# 🌐 www.algoacademy.com
"Learn by Building. Grow by Doing."

Context from Knowledge Base:
{context}

Student's Email:
{trimmed_body}

Write the full professional email reply now:"""

    for attempt in range(3):
        try:
            response = gemini_model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e):
                wait_time = 60 * (attempt + 1)
                print(f"⏳ Quota hit. Waiting {wait_time}s before retry {attempt+1}/3...")
                time.sleep(wait_time)
            else:
                raise e
    return f"Dear {sender_name},\n\nThank you for reaching out to AlgoAcademy!\nOur team will get back to you shortly.\n\nWarm regards,\nAlgoAcademy Support Team"

# Senders to skip (system/automated emails)
SKIP_SENDERS = [
    "no-reply",
    "noreply",
    "mailer-daemon",
    "accounts.google.com",
    "notifications",
    "support@",
    "alert",
    "do-not-reply"
]

def should_skip(sender):
    sender_lower = sender.lower()
    return any(skip in sender_lower for skip in SKIP_SENDERS)

def run_agent(interval=15):
    service = authenticate_gmail()
    print(f"🤖 Email Agent running. Checking every {interval} seconds...\n")
    while True:
        try:
            emails = get_unread_emails(service)
            if not emails:
                print("📭 No unread emails. Waiting...")
            for email in emails:
                print(f"📨 New email from: {email['sender']} | Subject: {email['subject']}")

                # Skip automated/system emails
                if should_skip(email["sender"]):
                    print(f"⏭️  Skipping automated email from {email['sender']}")
                    mark_as_read(service, email["id"])
                    continue

                # Search KB for relevant context
                context = search_kb(email["body"], docs, index)
                print(f"🔍 KB Context Found:\n{context[:200]}...")

                # Extract sender's first name for personalization
                sender_name = extract_first_name(email["sender"])
                # Generate reply using Gemini
                reply = generate_reply(email["body"], context, sender_name)
                print(f"💬 Generated Reply:\n{reply}\n")

                # Send reply and mark email as read
                send_reply(service, email["sender"], email["subject"], reply)
                mark_as_read(service, email["id"])
                print(f"✅ Reply sent and email marked as read.\n")

        except Exception as e:
            print(f"⚠️ Error occurred: {e}")
            print(f"🔄 Retrying in {interval} seconds...\n")

        time.sleep(interval)

if __name__ == "__main__":
    run_agent(interval=15)