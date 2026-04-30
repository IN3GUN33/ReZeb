import aiosmtplib
from email.message import EmailMessage
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.core.config import get_settings
from app.core.logging import get_logger
from pathlib import Path

logger = get_logger(__name__)
settings = get_settings()

TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "email"
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

async def send_email(subject: str, recipient: str, template_name: str, context: dict):
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("smtp_not_configured", recipient=recipient, template=template_name)
        return

    template = env.get_template(template_name)
    html_content = template.render(**context)

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(html_content, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
        )
        logger.info("email_sent", recipient=recipient, template=template_name)
    except Exception as exc:
        logger.error("email_send_failed", recipient=recipient, error=str(exc))
        raise
