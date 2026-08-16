import os
import logging
from threading import Thread
from flask import Flask

log = logging.getLogger("keep_alive")

app = Flask(__name__)

werkzeug_log = logging.getLogger("werkzeug")
werkzeug_log.setLevel(logging.ERROR)


@app.route("/")
def home():
    return "Bot is alive!", 200


@app.route("/ping")
def ping():
    return "pong", 200


@app.route("/health")
def health():
    return {"status": "ok"}, 200


def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    log.info("Keep-alive Flask server started.")
