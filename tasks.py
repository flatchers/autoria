from celery import Celery, shared_task
from celery.schedules import crontab

from main import main

app = Celery("tasks", broker="redis://redis:6379/0", backend="redis://redis:6379/0")
app.conf.timezone = "UTC"


@shared_task
def run_parser():
    main()


@app.on_after_configure.connect
def periodic_task(sender: Celery, **kwargs):
    sender.add_periodic_task(
        crontab(minute=22, hour=8),
        run_parser.s(),
        name="daily parser"
    )
