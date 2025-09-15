import os
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Optional
from datetime import datetime
from .ai_engine import AIEngine

class EmailAgent:
    """
    Simple IMAP email agent to fetch recent emails, summarize, and draft replies.
    Requires environment variables: IMAP_HOST, IMAP_PORT, IMAP_USERNAME, IMAP_PASSWORD, IMAP_SSL (optional, default true).
    """

    def __init__(self):
        self.host = os.getenv('IMAP_HOST')
        self.port = int(os.getenv('IMAP_PORT', '993'))
        self.username = os.getenv('IMAP_USERNAME')
        self.password = os.getenv('IMAP_PASSWORD')
        self.use_ssl = os.getenv('IMAP_SSL', 'true').lower() != 'false'
        self.mailbox = os.getenv('IMAP_MAILBOX', 'INBOX')
        self.engine = AIEngine()

    def _connect(self):
        if not all([self.host, self.username, self.password]):
            raise ValueError('IMAP credentials are not fully configured')
        M = imaplib.IMAP4_SSL(self.host, self.port) if self.use_ssl else imaplib.IMAP4(self.host, self.port)
        M.login(self.username, self.password)
        M.select(self.mailbox)
        return M

    def fetch_recent_emails(self, limit: int = 5) -> List[Dict]:
        """Fetch recent emails (headers + plain text body where possible)."""
        M = self._connect()
        try:
            typ, data = M.search(None, 'ALL')
            if typ != 'OK':
                return []
            ids = data[0].split()
            ids = ids[-limit:][::-1]
            results = []
            for msg_id in ids:
                typ, msg_data = M.fetch(msg_id, '(RFC822)')
                if typ != 'OK':
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header(msg.get('Subject', ''))
                from_ = self._decode_header(msg.get('From', ''))
                date_ = msg.get('Date', '')
                body_text = self._extract_text(msg)
                results.append({
                    'id': msg_id.decode('utf-8', errors='ignore'),
                    'from': from_,
                    'subject': subject,
                    'date': date_,
                    'snippet': (body_text or '')[:1000]
                })
            return results
        finally:
            try:
                M.close()
            except Exception:
                pass
            M.logout()

    def fetch_new_since(self, since_internaldate: Optional[str]) -> List[Dict]:
        """Fetch emails newer than an IMAP INTERNALDATE literal (e.g., 01-Jan-2025). If None, returns last 5."""
        if not since_internaldate:
            return self.fetch_recent_emails(limit=5)
        M = self._connect()
        try:
            typ, data = M.search(None, f'(SINCE "{since_internaldate}")')
            if typ != 'OK':
                return []
            ids = data[0].split()
            ids = ids[::-1]
            results = []
            for msg_id in ids:
                typ, msg_data = M.fetch(msg_id, '(RFC822 INTERNALDATE)')
                if typ != 'OK':
                    continue
                msg = email.message_from_bytes(msg_data[0][1])
                subject = self._decode_header(msg.get('Subject', ''))
                from_ = self._decode_header(msg.get('From', ''))
                date_ = msg.get('Date', '')
                body_text = self._extract_text(msg)
                results.append({
                    'id': msg_id.decode('utf-8', errors='ignore'),
                    'from': from_,
                    'subject': subject,
                    'date': date_,
                    'snippet': (body_text or '')[:1000]
                })
            return results
        finally:
            try:
                M.close()
            except Exception:
                pass
            M.logout()

    @staticmethod
    def to_imap_since(dt: datetime) -> str:
        """Convert datetime to IMAP SINCE date literal (e.g., 01-Jan-2025)."""
        return dt.strftime('%d-%b-%Y')

    def summarize_emails(self, emails: List[Dict]) -> str:
        if not emails:
            return 'No recent emails found.'
        bullets = []
        for e in emails:
            bullets.append(f"From: {e['from']} | Subject: {e['subject']} | Date: {e['date']}")
        prompt = (
            "Summarize the following recent emails for Badmus Qudus Ayomide in 5-8 bullets. "
            "Group related threads, note urgent items, and suggest next actions.\n\n" + "\n".join(bullets)
        )
        return self.engine.generate_response(prompt)

    def draft_reply(self, email_context: str, instructions: str) -> str:
        prompt = (
            "You are Jarvis drafting an email reply for Badmus Qudus Ayomide. "
            "Given the email context below, write a concise, polite reply that follows the instructions.\n\n"
            f"Email context:\n{email_context}\n\nInstructions:\n{instructions}\n\nDraft reply:"
        )
        return self.engine.generate_response(prompt)

    def _decode_header(self, value: str) -> str:
        try:
            parts = decode_header(value)
            decoded = []
            for text, enc in parts:
                if isinstance(text, bytes):
                    decoded.append(text.decode(enc or 'utf-8', errors='ignore'))
                else:
                    decoded.append(text)
            return ''.join(decoded)
        except Exception:
            return value or ''

    def _extract_text(self, msg) -> Optional[str]:
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    ctype = part.get_content_type()
                    disp = part.get('Content-Disposition', '')
                    if ctype == 'text/plain' and 'attachment' not in (disp or '').lower():
                        charset = part.get_content_charset() or 'utf-8'
                        return part.get_payload(decode=True).decode(charset, errors='ignore')
                # fallback to first text/html converted to text
                for part in msg.walk():
                    if part.get_content_type() == 'text/html':
                        charset = part.get_content_charset() or 'utf-8'
                        html = part.get_payload(decode=True).decode(charset, errors='ignore')
                        try:
                            import re
                            return re.sub('<[^<]+?>', '', html)
                        except Exception:
                            return html
            else:
                if msg.get_content_type() == 'text/plain':
                    charset = msg.get_content_charset() or 'utf-8'
                    return msg.get_payload(decode=True).decode(charset, errors='ignore')
            return None
        except Exception:
            return None


