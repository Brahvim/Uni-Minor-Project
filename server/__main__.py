from cv2 import *
from flask import Flask
from sqlalchemy import Connection

app = Flask(__name__)


@app.route("/")
def index():
    app.send_static_file()


@app.route("/new")
def new():
    pass


@app.route("/list")
def list():
    pass


@app.route("/plate/<p_id>")
def plate(p_id):
    pass


if __name__ == "__main__":
    app.run()
