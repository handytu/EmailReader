from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urlencode, urlparse, parse_qs

import requests
import time
from threading import Event

from app.models.account import EmailAccount
from app.models.message import MailMessage

DEFAULT_CLIENT_ID = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
REDIRECT_URI = "https://localhost"
SCOPE = "offline_access Mail.ReadWrite"


class MicrosoftAuthError(RuntimeError):
    pass


class MicrosoftGraphClient:
    """Microsoft consumer mail client.

    Preferred path: refresh_token -> Microsoft Graph.
    Compatibility path: username/password web OAuth flow, matching the
    user's previous readmailv3.py behavior. This path can still be blocked
    by MFA, CAPTCHA, identity confirmation, or Microsoft policy.
    """

    def __init__(self, account: EmailAccount, timeout: int = 20, device_login_callback=None, force_device: bool = False, cancel_event=None):
        self.account = account
        self.timeout = timeout
        self.access_token = ""
        self.device_login_callback = device_login_callback
        self.force_device = force_device
        self.cancel_event = cancel_event if cancel_event is not None else Event()
        self.session = requests.Session()
        self.session.headers.update({
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Thunderbird/128.2.3",
        })
        if account.proxy:
            self.session.proxies.update({"http": account.proxy, "https": account.proxy})

    @property
    def client_id(self) -> str:
        return self.account.client_id or DEFAULT_CLIENT_ID

    def connect(self):
        """Authenticate with the least disruptive path first.

        1) Existing refresh token
        2) Legacy password web OAuth flow (kept for compatibility)
        3) Microsoft Device Code flow as an interactive fallback

        Device login is intentionally a fallback so accounts that already work
        exactly like older EmailReader versions keep using the same path.
        """
        if self.force_device:
            self._login_with_device_code()
            return self

        last_error = None
        if self.account.refresh_token:
            try:
                self._refresh_access_token()
                return self
            except MicrosoftAuthError as exc:
                last_error = exc

        if self.account.password:
            try:
                self._login_with_password_webflow()
                return self
            except MicrosoftAuthError as exc:
                last_error = exc

        # The password HTML flow is increasingly blocked by MFA/CAPTCHA or
        # account confirmation. Device Code flow is the supported interactive
        # fallback and does not require the password to be typed into EmailReader.
        try:
            self._login_with_device_code()
            return self
        except MicrosoftAuthError as exc:
            if last_error:
                raise MicrosoftAuthError(f"{last_error}; device login failed: {exc}") from exc
            raise

    def _login_with_device_code(self):
        """Authenticate with Microsoft's OAuth 2.0 Device Authorization Grant.

        This uses the official Microsoft endpoints directly so EmailReader does
        not need an additional authentication dependency. The call runs on the
        existing background worker thread while the UI shows the user code.
        """
        device_resp = self.session.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode",
            data={
                "client_id": self.client_id,
                "scope": SCOPE,
            },
            timeout=self.timeout,
        )
        if not device_resp.ok:
            raise MicrosoftAuthError(f"Unable to start Microsoft device login: {self._safe_oauth_error(device_resp)}")

        flow = device_resp.json()
        device_code = flow.get("device_code", "")
        user_code = flow.get("user_code", "")
        verification_uri = flow.get("verification_uri") or "https://www.microsoft.com/link"
        message = flow.get("message", "")
        if not device_code or not user_code:
            raise MicrosoftAuthError("Microsoft device login response did not include a device code")

        if self.device_login_callback:
            self.device_login_callback(verification_uri, user_code, message)
        else:
            print(message or f"Open {verification_uri} and enter code {user_code}")

        interval = max(int(flow.get("interval", 5) or 5), 1)
        expires_in = max(int(flow.get("expires_in", 900) or 900), 30)
        deadline = time.monotonic() + expires_in
        token_url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"

        while time.monotonic() < deadline:
            if self.cancel_event.wait(interval):
                raise MicrosoftAuthError("Sign-in cancelled")
            token_resp = self.session.post(
                token_url,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "client_id": self.client_id,
                    "device_code": device_code,
                },
                timeout=self.timeout,
            )
            try:
                data = token_resp.json()
            except Exception:
                data = {}

            if token_resp.ok and data.get("access_token"):
                self.access_token = data["access_token"]
                if data.get("refresh_token"):
                    self.account.refresh_token = data["refresh_token"]
                return

            error = data.get("error", "")
            if error == "authorization_pending":
                continue
            if error == "slow_down":
                interval += 5
                continue
            if error in {"authorization_declined", "expired_token", "bad_verification_code"}:
                detail = data.get("error_description") or error
                raise MicrosoftAuthError(detail)
            if token_resp.status_code >= 400:
                detail = data.get("error_description") or error or f"HTTP {token_resp.status_code}"
                raise MicrosoftAuthError(detail)

        raise MicrosoftAuthError("Microsoft device login timed out before authentication was completed")

    def _refresh_access_token(self):
        resp = self.session.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self.account.refresh_token,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE,
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            detail = self._safe_oauth_error(resp)
            raise MicrosoftAuthError(f"OAuth refresh failed: {detail}")
        data = resp.json()
        self.access_token = data.get("access_token", "")
        if not self.access_token:
            raise MicrosoftAuthError("OAuth refresh returned no access_token")
        # Rotate refresh token in-memory when Microsoft returns a newer one.
        if data.get("refresh_token"):
            self.account.refresh_token = data["refresh_token"]

    def _login_with_password_webflow(self):
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "login_hint": self.account.email,
        }
        auth_url = "https://login.live.com/oauth20_authorize.srf?" + urlencode(params)
        resp = self.session.get(auth_url, allow_redirects=True, timeout=self.timeout)
        resp.raise_for_status()
        html = resp.text

        post_match = re.search(r'post\.srf\?([^"\'\\]+)', html)
        if not post_match:
            raise MicrosoftAuthError("Microsoft login form changed or identity confirmation is required")
        post_url = "https://login.live.com/ppsecure/post.srf?" + post_match.group(1)

        ppft_match = (
            re.search(r'PPFT.*?value=\\?"(.*?)\\?"', html, re.S)
            or re.search(r'name="PPFT"[^>]+value="([^"]+)"', html, re.S)
        )
        if not ppft_match:
            raise MicrosoftAuthError("Cannot obtain Microsoft PPFT login token")

        login_data = {
            "ps": "2",
            "PPFT": ppft_match.group(1),
            "PPSX": "Passp",
            "NewUser": "1",
            "login": self.account.email,
            "loginfmt": self.account.email,
            "passwd": self.account.password,
            "type": "11",
            "LoginOptions": "1",
            "i13": "1",
        }
        login_resp = self.session.post(
            post_url,
            data=login_data,
            headers={"content-type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
            timeout=self.timeout,
        )

        redirect_url = login_resp.headers.get("Location", "")
        if not redirect_url:
            raise MicrosoftAuthError(
                "Microsoft did not return an OAuth code (wrong password, MFA/CAPTCHA, or account confirmation may be required)"
            )
        code = (parse_qs(urlparse(redirect_url).query).get("code") or [""])[0]
        if not code:
            # Some flows make one more redirect before reaching localhost.
            follow = self.session.get(redirect_url, allow_redirects=False, timeout=self.timeout)
            redirect_url = follow.headers.get("Location", redirect_url)
            code = (parse_qs(urlparse(redirect_url).query).get("code") or [""])[0]
        if not code:
            raise MicrosoftAuthError("Microsoft login succeeded partially but no authorization code was returned")

        token_resp = self.session.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "code": code,
                "client_id": self.client_id,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
                "scope": SCOPE,
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        if not token_resp.ok:
            raise MicrosoftAuthError(f"OAuth code exchange failed: {self._safe_oauth_error(token_resp)}")
        data = token_resp.json()
        self.access_token = data.get("access_token", "")
        if not self.access_token:
            raise MicrosoftAuthError("OAuth code exchange returned no access_token")
        if data.get("refresh_token"):
            self.account.refresh_token = data["refresh_token"]

    @staticmethod
    def _safe_oauth_error(resp: requests.Response) -> str:
        try:
            data = resp.json()
            return data.get("error_description") or data.get("error") or f"HTTP {resp.status_code}"
        except Exception:
            return f"HTTP {resp.status_code}"

    def close(self):
        self.session.close()

    def fetch_inbox(self, limit: int = 50):
        if not self.access_token:
            self.connect()
        resp = self.session.get(
            "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={
                "$top": limit,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,replyTo,toRecipients,ccRecipients,receivedDateTime,bodyPreview,body,isRead,flag",
            },
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"Microsoft Graph Inbox failed: HTTP {resp.status_code}")

        out = []
        for item in resp.json().get("value", []):
            sender = (item.get("from") or {}).get("emailAddress") or {}
            body = item.get("body") or {}
            raw_date = item.get("receivedDateTime")
            try:
                dt = datetime.fromisoformat(raw_date.replace("Z", "+00:00")) if raw_date else None
            except Exception:
                dt = None
            is_html = body.get("contentType", "").lower() == "html"
            to_addrs = [((x.get("emailAddress") or {}).get("address") or "") for x in item.get("toRecipients", [])]
            cc_addrs = [((x.get("emailAddress") or {}).get("address") or "") for x in item.get("ccRecipients", [])]
            reply_to = item.get("replyTo") or []
            reply_to_addr = (((reply_to[0].get("emailAddress") or {}).get("address")) if reply_to else "") or ""
            out.append(MailMessage(
                uid=item.get("id", ""),
                sender_name=sender.get("name", ""),
                sender_addr=sender.get("address", ""),
                subject=item.get("subject") or "(No subject)",
                preview=item.get("bodyPreview", ""),
                date=dt,
                is_read=bool(item.get("isRead")),
                is_starred=((item.get("flag") or {}).get("flagStatus") == "flagged"),
                body_html=body.get("content", "") if is_html else "",
                body_text=body.get("content", "") if not is_html else "",
                to_addrs=[x for x in to_addrs if x], cc_addrs=[x for x in cc_addrs if x],
                reply_to_addr=reply_to_addr,
            ))
        return out

    def _graph_headers(self):
        if not self.access_token:
            self.connect()
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def set_starred(self, uid: str, value: bool):
        resp = self.session.patch(
            f"https://graph.microsoft.com/v1.0/me/messages/{uid}",
            headers=self._graph_headers(),
            json={"flag": {"flagStatus": "flagged" if value else "notFlagged"}},
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"Microsoft Graph star failed: HTTP {resp.status_code}")
        return value

    def set_read(self, uid: str, value: bool):
        resp = self.session.patch(
            f"https://graph.microsoft.com/v1.0/me/messages/{uid}",
            headers=self._graph_headers(),
            json={"isRead": bool(value)},
            timeout=self.timeout,
        )
        if not resp.ok:
            raise RuntimeError(f"Microsoft Graph read-state update failed: HTTP {resp.status_code}")
        return value

    def delete_message(self, uid: str):
        resp = self.session.delete(
            f"https://graph.microsoft.com/v1.0/me/messages/{uid}",
            headers=self._graph_headers(), timeout=self.timeout,
        )
        if resp.status_code not in (202, 204):
            raise RuntimeError(f"Microsoft Graph delete failed: HTTP {resp.status_code}")
        return True

    def send_message(self, *, to: list[str], cc: list[str], subject: str, body: str):
        if not to and not cc:
            raise RuntimeError("At least one recipient is required")
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body or ""},
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
                "ccRecipients": [{"emailAddress": {"address": addr}} for addr in cc],
            },
            "saveToSentItems": True,
        }
        resp = self.session.post(
            "https://graph.microsoft.com/v1.0/me/sendMail",
            headers=self._graph_headers(), json=payload, timeout=self.timeout,
        )
        if resp.status_code not in (200, 202):
            if resp.status_code == 403:
                raise RuntimeError("Sending is not authorized for this Microsoft session. Inbox login remains on Mail.ReadWrite for compatibility. Use a separate OAuth consent flow with Mail.Send if you want sending enabled.")
            raise RuntimeError(f"Microsoft Graph send failed: HTTP {resp.status_code}")
        return True
