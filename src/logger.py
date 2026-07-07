import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
    datefmt="%m-%d-%Y %H:%M:%S",
)
logger = logging.getLogger("DecathlonToCalendar")