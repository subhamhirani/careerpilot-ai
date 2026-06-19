"""
CareerPilot AI — Telegram Bot
==============================
Provides real-time notifications, approvals, and system management
via Telegram.

Commands:
  /start          — Welcome message
  /status         — Today's discovery run summary
  /jobs           — Top 5 matching jobs today
  /approve <id>   — Approve application ID
  /reject <id>    — Reject application ID
  /pause          — Pause daily scheduler
  /resume         — Resume daily scheduler
  /stats          — Pipeline statistics

Automatic notifications:
  - Excellent match alert (score ≥ 85)
  - Daily digest of new matches
  - Application submitted confirmation
  - Pending approval reminder (every 4 hours for pending items)

Security:
  - All commands check ``ALLOWED_USER_ID`` before processing.
  - Unauthorised users receive a silent "*Unauthorized*" reply.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Celery app import
# ---------------------------------------------------------------------------
from .celery_config import app as celery_app


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USER_ID = os.getenv("TELEGRAM_ALLOWED_USER_ID", "")


def is_authorized(update: Update) -> bool:
    """Check whether the sender is the single authorised user."""
    if not ALLOWED_USER_ID:
        return False
    return str(update.effective_user.id) == ALLOWED_USER_ID


def _unauthorized_reply(update: Update) -> None:
    """Send an unauthorised message (fire-and-forget)."""
    try:
        update.message.reply_text(
            "⛔ Unauthorized. You are not permitted to use this bot."
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome + command overview."""
    if not is_authorized(update):
        _unauthorized_reply(update)
        return
    await update.message.reply_text(
        "🤖 *CareerPilot AI* — your autonomous job search assistant.\n\n"
        "Available commands:\n"
        "• `/status` — Today's job discovery summary\n"
        "• `/jobs` — Top 5 matching jobs\n"
        "• `/approve <id>` — Approve application\n"
        "• `/reject <id>` — Reject application\n"
        "• `/pause` — Pause daily scheduler\n"
        "• `/resume` — Resume daily scheduler\n"
        "• `/stats` — Pipeline statistics\n\n"
        "I will also notify you when excellent matches are found.",
        parse_mode="Markdown",
    )


async def status_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Today's run summary."""
    if not is_authorized(update):
        return
    # In production this would query the DB or Celery results.
    summary = _fetch_today_summary()
    await update.message.reply_text(
        f"📊 *Today's Run*\n\n"
        f"Jobs discovered: {summary['discovered']}\n"
        f"Excellent matches (≥85%): {summary['excellent']}\n"
        f"Good matches (≥70%): {summary['good']}\n"
        f"Pending your review: {summary['pending_review']}\n"
        f"Scheduler: {'🟢 Running' if summary['scheduler_running'] else '🔴 Paused'}",
        parse_mode="Markdown",
    )


async def jobs_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Top 5 matching jobs today."""
    if not is_authorized(update):
        return
    jobs = _fetch_top_jobs(limit=5)
    if not jobs:
        await update.message.reply_text(
            "📭 No matching jobs found today. I'll keep looking!"
        )
        return

    lines = ["🏆 *Top Matches Today*\n"]
    for i, job in enumerate(jobs, 1):
        lines.append(
            f"{i}. *{job['title']}* @ {job['company']}\n"
            f"   Score: {job['score']}%  |  {job['location']}\n"
            f"   [{job['url']}]({job['url']})"
        )
    await update.message.reply_text(
        "\n\n".join(lines),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


async def approve_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Approve a pending application.

    Usage: /approve <approval_id>
    """
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/approve <approval_id>`\n"
            "Example: `/approve a1b2c3`",
            parse_mode="Markdown",
        )
        return

    approval_id = context.args[0]
    logger.info("User requested approval of %s", approval_id)

    try:
        # In production: update DB -> trigger ApplicationAgent
        success = _process_approval(approval_id, action="approve")
        if success:
            await update.message.reply_text(
                f"✅ *Approved* — Application `{approval_id}` "
                f"has been queued for submission.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"❌ Could not approve `{approval_id}`. "
                f"It may already have been processed.",
                parse_mode="Markdown",
            )
    except Exception as exc:
        logger.exception("Approval failed for %s", approval_id)
        await update.message.reply_text(
            f"⚠️ Error processing approval: {exc}"
        )


async def reject_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Reject a pending application.

    Usage: /reject <approval_id>
    """
    if not is_authorized(update):
        return
    if not context.args:
        await update.message.reply_text(
            "Usage: `/reject <approval_id>`\n"
            "Example: `/reject a1b2c3`",
            parse_mode="Markdown",
        )
        return

    approval_id = context.args[0]
    logger.info("User requested rejection of %s", approval_id)

    try:
        success = _process_approval(approval_id, action="reject")
        if success:
            await update.message.reply_text(
                f"❌ *Rejected* — Application `{approval_id}` "
                f"has been declined.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"⚠️ Could not reject `{approval_id}`. "
                f"It may already have been processed.",
                parse_mode="Markdown",
            )
    except Exception as exc:
        logger.exception("Rejection failed for %s", approval_id)
        await update.message.reply_text(
            f"⚠️ Error processing rejection: {exc}"
        )


async def pause_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Pause the daily job discovery scheduler."""
    if not is_authorized(update):
        return
    try:
        _set_scheduler_paused(paused=True)
        await update.message.reply_text(
            "⏸️ *Scheduler Paused*\n\n"
            "Job discovery and matching will not run until "
            "you send `/resume`.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("Failed to pause scheduler")
        await update.message.reply_text(f"⚠️ Error pausing scheduler: {exc}")


async def resume_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Resume the daily job discovery scheduler."""
    if not is_authorized(update):
        return
    try:
        _set_scheduler_paused(paused=False)
        await update.message.reply_text(
            "▶️ *Scheduler Resumed*\n\n"
            "Job discovery will run on the next scheduled cycle.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("Failed to resume scheduler")
        await update.message.reply_text(
            f"⚠️ Error resuming scheduler: {exc}"
        )


async def stats_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Overall pipeline statistics."""
    if not is_authorized(update):
        return
    pipeline = _fetch_pipeline_stats()
    await update.message.reply_text(
        "📈 *Pipeline Statistics*\n\n"
        f"Total jobs tracked: {pipeline['total_jobs']}\n"
        f"Pending review: {pipeline['pending_review']}\n"
        f"Approved (queued): {pipeline['approved']}\n"
        f"Submitted: {pipeline['submitted']}\n"
        f"Manual required: {pipeline['manual_required']}\n"
        f"Cover letters generated: {pipeline['cover_letters']}\n"
        f"Resumes tailored: {pipeline['tailored_resumes']}\n\n"
        f"Last run: {pipeline['last_run']}",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Inline keyboard callback (approve/reject from notifications)
# ---------------------------------------------------------------------------

async def approval_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle inline 'Approve' / 'Reject' button presses."""
    query = update.callback_query
    await query.answer()

    if not is_authorized(update):
        await query.edit_message_text(
            "⛔ Unauthorized. You cannot perform this action."
        )
        return

    data = query.data
    # data format: "approve:<approval_id>" or "reject:<approval_id>"
    if ":" not in data:
        logger.warning("Malformed callback data: %s", data)
        return

    action, approval_id = data.split(":", 1)

    if action == "approve":
        _process_approval(approval_id, action="approve")
        await query.edit_message_text(
            f"✅ *Approved* — Application `{approval_id}` "
            f"queued for submission.",
            parse_mode="Markdown",
        )
    elif action == "reject":
        _process_approval(approval_id, action="reject")
        await query.edit_message_text(
            f"❌ *Rejected* — Application `{approval_id}` declined.",
            parse_mode="Markdown",
        )
    else:
        logger.warning("Unknown action in callback: %s", action)


# ---------------------------------------------------------------------------
# Automatic notification builders
# ---------------------------------------------------------------------------

def build_excellent_match_alert(
    job_title: str,
    company: str,
    score: int,
    approval_id: str,
) -> tuple:
    """Build message text + inline keyboard for an excellent match alert.

    Returns ``(message_text, reply_markup)``.
    """
    text = (
        f"🔥 *Excellent Match!*\n\n"
        f"*{job_title}* at *{company}*\n"
        f"Match score: {score}% — this looks like a great fit!\n\n"
        f"Would you like to approve or reject this application?"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Approve", callback_data=f"approve:{approval_id}"
                ),
                InlineKeyboardButton(
                    "❌ Reject", callback_data=f"reject:{approval_id}"
                ),
            ]
        ]
    )
    return text, keyboard


def build_daily_digest(
    new_jobs_count: int,
    excellent_count: int,
    pending_review_count: int,
    top_jobs: List[Dict[str, Any]],
) -> str:
    """Build the daily digest message."""
    lines = [
        "🌅 *CareerPilot Daily Digest*\n",
        f"New jobs found: {new_jobs_count}",
        f"Excellent matches: {excellent_count}",
        f"Pending your review: {pending_review_count}\n",
    ]
    if top_jobs:
        lines.append("*Top picks:*")
        for job in top_jobs[:3]:
            lines.append(
                f"• {job['title']} @ {job['company']} "
                f"({job.get('score', '?')}%)"
            )
    lines.append("\nUse `/jobs` to see all matches.")
    return "\n".join(lines)


def build_application_confirmation(
    job_title: str,
    company: str,
    status: str,
) -> str:
    """Build the application submitted / failed notification."""
    if status == "submitted":
        return (
            f"📨 *Application Submitted!*\n\n"
            f"Your application for *{job_title}* at *{company}* "
            f"has been submitted successfully."
        )
    if status == "manual_required":
        return (
            f"⚠️ *Manual Application Required*\n\n"
            f"Your application for *{job_title}* at *{company}* "
            f"could not be automated.  Please complete it manually.\n"
            f"Check the dashboard for the direct link."
        )
    return (
        f"❌ *Application Failed*\n\n"
        f"Your application for *{job_title}* at *{company}* "
        f"encountered an error.  Check the dashboard for details."
    )


# ---------------------------------------------------------------------------
# Production stubs — replace with actual DB/service calls
# ---------------------------------------------------------------------------

def _fetch_today_summary() -> Dict[str, Any]:
    """Fetch today's job discovery summary from the database.

    Stub — replace with real DB queries.
    """
    return {
        "discovered": 15,
        "excellent": 3,
        "good": 7,
        "pending_review": 4,
        "scheduler_running": True,
    }


def _fetch_top_jobs(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch top matching jobs from the database.

    Stub — replace with real DB queries.
    """
    return [
        {
            "title": "DevOps Engineer",
            "company": "TechCorp",
            "score": 92,
            "location": "Remote",
            "url": "https://example.com/job/1",
        },
        {
            "title": "Platform Engineer",
            "company": "CloudInc",
            "score": 88,
            "location": "Bangalore, India",
            "url": "https://example.com/job/2",
        },
        {
            "title": "SRE",
            "company": "ScaleUp",
            "score": 85,
            "location": "Remote",
            "url": "https://example.com/job/3",
        },
        {
            "title": "Cloud Infrastructure Engineer",
            "company": "FinServ",
            "score": 79,
            "location": "Ahmedabad, India",
            "url": "https://example.com/job/4",
        },
        {
            "title": "Site Reliability Engineer",
            "company": "DataCo",
            "score": 76,
            "location": "Remote",
            "url": "https://example.com/job/5",
        },
    ]


def _process_approval(approval_id: str, action: str) -> bool:
    """Process an approval or rejection in the database.

    Stub — replace with actual DB + ApplicationAgent call.

    Returns ``True`` if the record was found and updated.
    """
    logger.info(
        "Processing %s for approval_id=%s (stub)", action, approval_id
    )
    # TODO: update pending_approvals set status = action where id = approval_id
    # If approved, trigger run_application_submission()
    return True


def _set_scheduler_paused(paused: bool) -> None:
    """Toggle the scheduler pause state.

    Stub — replace with actual Redis/Celery control.
    """
    state = "paused" if paused else "running"
    logger.info("Scheduler toggled to %s (stub)", state)


def _fetch_pipeline_stats() -> Dict[str, Any]:
    """Fetch pipeline statistics from the database.

    Stub — replace with real DB queries.
    """
    return {
        "total_jobs": 142,
        "pending_review": 4,
        "approved": 2,
        "submitted": 1,
        "manual_required": 1,
        "cover_letters": 3,
        "tailored_resumes": 3,
        "last_run": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ---------------------------------------------------------------------------
# Bot runner
# ---------------------------------------------------------------------------

def run_bot() -> None:
    """Start the Telegram bot polling loop.

    Called from ``main()`` or an external entry point.
    """
    if not TOKEN:
        logger.error(
            "TELEGRAM_BOT_TOKEN is not set — bot cannot start"
        )
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

    logger.info("Starting CareerPilot Telegram bot...")
    application = Application.builder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("jobs", jobs_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))
    application.add_handler(CommandHandler("pause", pause_command))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("stats", stats_command))

    # Register inline callback handler
    application.add_handler(
        CallbackQueryHandler(approval_callback, pattern=r"^(approve|reject):")
    )

    logger.info(
        "Bot configured — allowed user: %s",
        ALLOWED_USER_ID or "(not set — all users blocked)",
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def main() -> None:
    """Entry point for standalone execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    run_bot()



# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, acks_late=True, name="app.bot.send_pending_reminder")
def send_pending_reminder(self, cutoff_iso: str) -> dict:
    """Send pending approval reminders for applications older than cutoff."""
    logger.info("Task [send_pending_reminder] started with cutoff: %s", cutoff_iso)
    try:
        # In production: query database for pending applications older than cutoff_iso
        # and send a reminder via Telegram.
        # For now, we just log.
        logger.info("Would send reminder for pending applications older than %s", cutoff_iso)
        # TODO: implement actual reminder sending
        return {"reminded": True, "cutoff": cutoff_iso}
    except Exception as exc:
        logger.exception("Task [send_pending_reminder] failed")
        raise self.retry(exc=exc)

if __name__ == "__main__":
    main()
