"""Report generation tasks — LOW queue.

Handles AI insight reports, daily summaries, and newsletter sending.
"""
import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.report_tasks.generate_ai_insight_report")
def generate_ai_insight_report(client_id: str, period: str) -> dict:
    """Generate AI-powered insight report for a client.

    Steps:
        1. Query analytics data for the period
        2. LLM generates 3-line summary + detailed analysis + strategy recommendations
        3. Generate PDF and upload to S3
        4. Send notification: report ready

    Returns:
        dict with report_url and summary
    """
    # Placeholder: actual implementation in STEP 19+
    logger.info("Generating AI insight report for client %s, period %s", client_id, period)
    return {
        "client_id": client_id,
        "period": period,
        "summary": "Report generation placeholder - will be implemented with LLM integration",
        "report_url": None,
    }


@celery_app.task(name="app.tasks.report_tasks.generate_daily_report")
def generate_daily_report():
    """Periodic task (daily at 08:00 KST): generate daily summary for all active clients."""
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models.client import Client
    import asyncio

    async def _generate():
        async with async_session_factory() as db:
            result = await db.execute(
                select(Client).where(Client.status == "active")
            )
            clients = result.scalars().all()

            for client in clients:
                try:
                    generate_ai_insight_report.delay(str(client.id), "1d")
                    logger.info("Queued daily report for client %s", client.name)
                except Exception:
                    logger.exception("Failed to queue daily report for client %s", client.id)

            logger.info("Daily report generation queued for %d clients", len(clients))

    try:
        asyncio.get_event_loop().run_until_complete(_generate())
    except RuntimeError:
        asyncio.run(_generate())


@celery_app.task(name="app.tasks.report_tasks.send_newsletter")
def send_newsletter(client_id: str, report_url: str):
    """Send report newsletter via email.

    Placeholder: actual email integration to be added.
    """
    logger.info("Would send newsletter for client %s with report: %s", client_id, report_url)
    return {"status": "sent", "client_id": client_id}
