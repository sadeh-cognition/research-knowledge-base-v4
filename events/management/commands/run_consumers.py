import time
import djclick as click
from loguru import logger
from django.conf import settings
from events.consumers import process_all_events

@click.command()
@click.option('--interval', default=5, help='Polling interval in seconds')
@click.option('--once', is_flag=True, help='Run consumers once and exit')
def command(interval: int, once: bool):
    """Run event consumers to process background tasks."""
    logger.info("Starting event consumers...")
    
    if once:
        count = process_all_events()
        logger.info(f"Processed {count} events. Exiting.")
        return

    try:
        while True:
            count = process_all_events()
            if count > 0:
                logger.info(f"Processed {count} events in this cycle.")
            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info("Stopping event consumers...")
