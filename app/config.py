import sys
import os
from dotenv import find_dotenv, load_dotenv, get_key
import logging


def load_configurations(app):
    # path = find_dotenv()            # necessary for flask
    # print(f"Arquivo .env encontrado em: {path}")
    # load_dotenv(path)
    app.config["ACCESS_TOKEN"] = get_key('.env', "ACCESS_TOKEN")
    app.config["APP_ID"] = get_key('.env', "APP_ID")
    app.config["APP_SECRET"] = get_key('.env', "APP_SECRET")
    app.config["VERSION"] = get_key('.env', "VERSION")
    app.config["PHONE_NUMBER_ID"] = get_key('.env', "PHONE_NUMBER_ID")
    app.config["VERIFY_TOKEN"] = get_key('.env', "VERIFY_TOKEN")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )
