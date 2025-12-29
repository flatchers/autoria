import logging
import sys


def get_logging_info():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)8s]:  %(message)s",
        handlers=[
            logging.FileHandler("parser.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_logging_debug():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(levelname)8s]:  %(message)s",
        handlers=[
            logging.FileHandler("parser.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )
