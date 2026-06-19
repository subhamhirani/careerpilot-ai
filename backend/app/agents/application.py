"""
CareerPilot AI — Agent 6: Application Agent
============================================
Automates job submissions using Playwright, with fallback to
manual_required mode for non-automatable portals.

Approval flow:
  1. Pre-approval screen shows job details, tailored resume, cover letter.
  2. User approves (dashboard or Telegram ``/approve <id>``).
  3. Agent attempts Playwright automation.
  4. If automatable → submit + screenshot confirmation.
  5. If NOT automatable → mark as ``manual_required``, provide direct link.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application Submitter
# ---------------------------------------------------------------------------

class ApplicationSubmitter:
    """Agent 6: Attempt automated application via Playwright.

    Usage::

        submitter = ApplicationSubmitter()
        result = await submitter.submit(
            application_url="https://jobs.example.com/apply/123",
            resume_path="/app/storage/resumes/tailored_abc.pdf",
            user_profile={...},
            cover_letter="Dear ...",
            application_id="app-001",
        )
    """

    def __init__(self, storage_path: str = "/app/storage") -> None:
        self.storage_path = storage_path
        self.screenshots_dir = os.path.join(storage_path, "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)

    # -- Main entry point --------------------------------------------------

    async def submit(
        self,
        application_url: str,
        resume_path: str,
        user_profile: Dict[str, Any],
        cover_letter: str,
        application_id: str,
    ) -> Dict[str, Any]:
        """Submit application using Playwright browser automation.

        Args:
            application_url: Direct URL to the application form.
            resume_path: Absolute path to the tailored resume PDF/docx.
            user_profile: Dict with ``full_name``, ``contact.email``,
                ``contact.phone`` etc.
            cover_letter: Generated cover letter text.
            application_id: Unique ID for this application (used for
                screenshot filenames and logging).

        Returns:
            Dict with keys:
                method ("automated" | "manual_required")
                screenshot_before (path or None)
                screenshot_after (path or None)
                status ("submitted" | "manual_required" | "failed")
                confirmation_id (str or None)
                error (str or None)
        """
        screenshot_before: Optional[str] = None
        screenshot_after: Optional[str] = None

        try:
            from playwright.async_api import async_playwright  # type: ignore[import-untyped]
        except ImportError:
            logger.error("playwright is not installed — marking as manual_required")
            return self._manual_result(
                application_id,
                "playwright package not installed",
            )

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(application_url, timeout=30_000)

                # Screenshot before filling
                screenshot_before = os.path.join(
                    self.screenshots_dir, f"{application_id}_before.png"
                )
                await page.screenshot(path=screenshot_before)

                # -- Attempt form filling ----------------------------------
                form_ok = await self._fill_form(
                    page=page,
                    resume_path=resume_path,
                    user_profile=user_profile,
                    cover_letter=cover_letter,
                )

                # Screenshot after filling (before submit)
                screenshot_after = os.path.join(
                    self.screenshots_dir, f"{application_id}_after_fill.png"
                )
                await page.screenshot(path=screenshot_after)

                if not form_ok:
                    logger.warning(
                        "Could not locate form fields on %s — "
                        "marking manual_required",
                        application_url,
                    )
                    return {
                        "method": "manual_required",
                        "screenshot_before": screenshot_before,
                        "screenshot_after": screenshot_after,
                        "status": "manual_required",
                        "confirmation_id": None,
                        "error": (
                            "Could not locate expected form fields. "
                            "Portal likely uses a non-standard layout."
                        ),
                    }

                # -- Attempt submit -----------------------------------------
                submitted = await self._click_submit(page)

                if submitted:
                    await page.wait_for_timeout(3000)
                    # Take post-submit screenshot
                    screenshot_post = os.path.join(
                        self.screenshots_dir, f"{application_id}_after_submit.png"
                    )
                    await page.screenshot(path=screenshot_post)

                    logger.info(
                        "Application %s submitted successfully via "
                        "Playwright automation",
                        application_id,
                    )
                    return {
                        "method": "automated",
                        "screenshot_before": screenshot_before,
                        "screenshot_after": screenshot_post,
                        "status": "submitted",
                        "confirmation_id": None,
                        "error": None,
                    }

                logger.warning(
                    "Submit button not found on %s — "
                    "marking manual_required",
                    application_url,
                )
                return {
                    "method": "manual_required",
                    "screenshot_before": screenshot_before,
                    "screenshot_after": screenshot_after,
                    "status": "manual_required",
                    "confirmation_id": None,
                    "error": "Submit button not found on page.",
                }

            except Exception as exc:
                logger.error(
                    "Playwright automation failed for %s: %s",
                    application_id, exc,
                )
                return {
                    "method": "manual_required",
                    "screenshot_before": screenshot_before,
                    "screenshot_after": screenshot_after,
                    "status": "manual_required",
                    "confirmation_id": None,
                    "error": str(exc),
                }
            finally:
                await browser.close()

    # -- Form filling helpers ----------------------------------------------

    async def _fill_form(
        self,
        page: Any,  # playwright Page
        resume_path: str,
        user_profile: Dict[str, Any],
        cover_letter: str,
    ) -> bool:
        """Attempt to fill common form fields.

        Returns ``True`` if at least one field was filled (not necessarily
        all — we're best-effort).
        """
        fields_filled = False

        # Resolve file path
        resume_abs = str(Path(resume_path).resolve())

        # File upload
        try:
            file_input = await page.query_selector(
                'input[type="file"]'
            )
            if file_input:
                await file_input.set_input_files(resume_abs)
                fields_filled = True
                logger.debug("Resume file uploaded: %s", resume_abs)
        except Exception:
            logger.debug("File upload field not found or not interactable")

        # Resume/CV upload (alternative selectors)
        for sel in (
            'input[accept*="pdf"]',
            'input[accept*="doc"]',
            'input[id*="resume"]',
            'input[name*="resume"]',
            'input[class*="resume"]',
        ):
            try:
                el = await page.query_selector(sel)
                if el:
                    await el.set_input_files(resume_abs)
                    fields_filled = True
            except Exception:
                continue

        # Name
        name = user_profile.get("full_name", "")
        if name:
            await self._fill_field(page, 'input[name*="name"]', name)
            await self._fill_field(
                page, 'input[id*="name"i]', name
            )

        # Email
        email = (
            user_profile.get("contact", {})
            .get("email", "")
        )
        if email:
            await self._fill_field(
                page, 'input[type="email"]', email
            )

        # Phone
        phone = (
            user_profile.get("contact", {})
            .get("phone", "")
        )
        if phone:
            await self._fill_field(
                page, 'input[type="tel"]', phone
            )

        # Cover letter textarea
        if cover_letter:
            await self._fill_field(
                page,
                'textarea[name*="cover"], textarea[id*="cover"], '
                'textarea[name*="letter"], textarea[id*="letter"], '
                'textarea[class*="cover"]',
                cover_letter,
            )

        return fields_filled

    @staticmethod
    async def _fill_field(
        page: Any, selector: str, value: str
    ) -> None:
        """Fill a form field identified by *selector* if it exists."""
        if not value:
            return
        try:
            element = await page.query_selector(selector)
            if element:
                await element.fill(value)
        except Exception:
            pass

    @staticmethod
    async def _click_submit(page: Any) -> bool:
        """Attempt to locate and click a submit button.

        Returns ``True`` if a button was clicked.
        """
        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Submit")',
            'button:has-text("Apply")',
            'button:has-text("Send")',
            'button:has-text("Continue")',
            'input[type="submit"]',
            'a:has-text("Apply")',
        ]
        for sel in submit_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    return True
            except Exception:
                continue
        return False

    # -- Helpers -----------------------------------------------------------

    @staticmethod
    def _manual_result(
        application_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "method": "manual_required",
            "screenshot_before": None,
            "screenshot_after": None,
            "status": "manual_required",
            "confirmation_id": None,
            "error": reason,
        }

    @staticmethod
    def build_application_data(
        application_id: str,
        job_posting_id: str,
        user_id: str,
        resume_version_id: str,
        cover_letter_id: Optional[str],
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build a dict suitable for inserting into the ``applications``
        table after a submission attempt.

        Example::

            result = await submitter.submit(...)
            data = submitter.build_application_data(
                app_id, job_id, user_id, resume_ver_id, cl_id, result
            )
            await db.execute(applications.insert().values(**data))
        """
        return {
            "id": application_id,
            "job_posting_id": job_posting_id,
            "user_id": user_id,
            "resume_version_id": resume_version_id,
            "cover_letter_id": cover_letter_id,
            "status": result.get("status", "manual_required"),
            "method": result.get("method", "manual_required"),
            "screenshot_before": result.get("screenshot_before"),
            "screenshot_after": result.get("screenshot_after"),
            "confirmation_id": result.get("confirmation_id"),
            "error_message": result.get("error"),
            "created_at": None,
        }


# ---------------------------------------------------------------------------
# Pending Approval helpers
# ---------------------------------------------------------------------------

class PendingApproval:
    """Lightweight model helpers for the approval flow.

    The actual DB model is expected to have columns:
        id, job_posting_id, user_id, resume_version_id,
        cover_letter_id, match_score, status (pending/approved/rejected),
        created_at, decided_at
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    @staticmethod
    def build_pending_approval_data(
        job_posting_id: str,
        user_id: str,
        resume_version_id: str,
        cover_letter_id: Optional[str],
        match_score: Optional[int] = None,
        extra_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a dict for inserting into ``pending_approvals``."""
        return {
            "job_posting_id": job_posting_id,
            "user_id": user_id,
            "resume_version_id": resume_version_id,
            "cover_letter_id": cover_letter_id,
            "match_score": match_score,
            "status": PendingApproval.STATUS_PENDING,
            "extra_data": json.dumps(extra_data) if extra_data else None,
            "created_at": None,
        }


# ---------------------------------------------------------------------------
# Convenience entrypoint
# ---------------------------------------------------------------------------

async def run_application_submission(
    application_url: str,
    resume_path: str,
    user_profile: Dict[str, Any],
    cover_letter: str,
    application_id: str,
    storage_path: str = "/app/storage",
) -> Dict[str, Any]:
    """High-level helper: submit an application and return the result.

    Designed for use from a Celery task or FastAPI endpoint.
    """
    submitter = ApplicationSubmitter(storage_path=storage_path)
    result = await submitter.submit(
        application_url=application_url,
        resume_path=resume_path,
        user_profile=user_profile,
        cover_letter=cover_letter,
        application_id=application_id,
    )
    return result
