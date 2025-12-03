from cv2.typing import MatLike
from ultralytics import YOLO
from queue import Queue
import mysql.connector
import numpy as np
import threading
import websocket
import requests
import base64
import time
import json
import cv2
import re

# region Vars.
# These `int`s are Unix timestamps.
s_queueYolo: Queue[tuple[int, MatLike, bytes]] = Queue()
s_queueLlama: Queue[tuple[int, MatLike]] = Queue()
s_queueSave: Queue[tuple[int, bytes]] = Queue()
s_queueEsp: Queue[bytes] = Queue()

with open("secrets.json") as f:
    s_secrets = json.load(f)

s_espIpStr = ""
s_llamaPort = 3000
s_pathJpegs = "./photos"
# Not using a `mysql.connector.pooling.MySQLConnectionPool()` this time...
s_dbSave = mysql.connector.connect(
    database="quickpark",
    user=s_secrets["dbUser"],
    host=s_secrets["dbHost"],
    password=s_secrets["dbPass"],
)
s_dbLlama = mysql.connector.connect(
    database="quickpark",
    user=s_secrets["dbUser"],
    host=s_secrets["dbHost"],
    password=s_secrets["dbPass"],
)
s_llamaUrl = f"http://localhost:{s_llamaPort}"
s_pathYolos = "./yolov11-license-plate-detection"
s_yolo = YOLO(f"{s_pathYolos}/license-plate-finetune-v1n.pt")
# endregion

# region Workers.


def workerThreadLlama():
    """
    Converts cropped `MatLike`s to JPEGs, then Base64,
    then requests the llama.cpp API to provide label.
    """
    cur = s_dbLlama.cursor()
    sql = "UPDATE entries SET plate = %s WHERE tstamp = %s;"
    prompt = "The image may contain a vehicle license plate. If so, respond with *just* said number in full. In case of any issues, respond with just \"NULL\" without the quotes. Some plates may use the format `↑ 01Z 012345A`; make use of the broad arrow."
    while True:
        tstamp, crop = s_queueLlama.get()
        ok, jpeg = cv2.imencode(".jpg", crop)
        if not ok:
            s_queueLlama.task_done()
            continue

        # On my machine with a GTX 1650:
        # nvrun ./llama.cpp/llama-server
        # --port 3000
        # --n-gpu-layers 2
        # -m ./Qwen3VL-2B-Instruct-Q4_K_M.gguf
        # --mmproj ./mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf
        #
        # *One liner!:*
        #
        # nvrun ./llama.cpp/llama-server --port 3000 --n-gpu-layers 2 -m ./Qwen3VL-2B-Instruct-Q4_K_M.gguf --mmproj ./mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf
        #
        # PS *Do* use `-n 32` so the model simply *can't* output more tokens.
        # DEFINITELY also use a grammar...!

        jpegB64 = base64.b64encode(jpeg)
        jpegB64Utf8 = jpegB64.decode("utf-8")

        reqBody = {
            "model": "Qwen3VL-2B-Instruct-Q4_K_M.gguf",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{jpegB64Utf8}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        }
                    ]
                }
            ]
        }

        # print(f"Trying to read plate {tstamp}...")
        resHttp = requests.post(
            f"{s_llamaUrl}/v1/chat/completions",
            json=reqBody,
            timeout=30,
        )

        try:
            resHttp.raise_for_status()
            resJson = resHttp.json()
            plate: str = resJson["choices"][0]["message"]["content"]

            if len(plate) > 32 or plate == "NULL":
                s_queueLlama.task_done()
                return

            print(f"Plate `{plate}` seen.")
            cur.execute(sql, (plate, tstamp))
            s_dbLlama.commit()
        except requests.HTTPError as e:
            print(e)
            pass

        s_queueLlama.task_done()


def workerThreadEsp():
    """
    Converts all ESP32-CAM payloads to `MatLike`s.
    """
    while True:
        p = s_queueEsp.get()

        if p is None:
            s_queueEsp.task_done()
            continue

        int8 = np.frombuffer(p, dtype=np.uint8)
        jpeg = cv2.imdecode(int8, cv2.IMREAD_COLOR)

        if jpeg is None:
            s_queueEsp.task_done()
            continue

        tstamp = int(time.time() * 1000)  # Converts to millis.
        s_queueYolo.put((tstamp, jpeg, p))
        s_queueEsp.task_done()


def workerThreadSave():
    """
    Writes JPEGs to disk and their timestamp to the DB.
    """
    cur = s_dbSave.cursor()
    # These shall NEVER BE F-STRINGS!:
    sql = f"INSERT INTO entries(tstamp) VALUES(%s);"
    # EASIEST way to get injection attacks!
    while True:
        tstamp, payload = s_queueSave.get()

        with open(f"{s_pathJpegs}/{tstamp}.jpg", "wb") as f:
            f.write(payload)

        cur.execute(sql, (tstamp,))
        s_dbSave.commit()
        s_queueSave.task_done()


def workerThreadYolo():
    """
    Runs YOLOv11 inference for LPR and notifies Express.
    """
    while True:
        tstamp, jpeg, payload = s_queueYolo.get()
        rgb = jpeg[:, :, ::-1]  # Bgr2Rgb!
        # results = s_yolo.predict(source=rgb)
        results = s_yolo.predict(source=rgb, verbose=False)

        for r in results:
            for b in r.boxes:
                x1, y1, x2, y2 = map(int, b.xyxy[0].tolist())

                # Clamp validly!:
                x1 = max(0, min(x1, rgb.shape[1]-1))
                x2 = max(0, min(x2, rgb.shape[1]-1))
                y1 = max(0, min(y1, rgb.shape[0]-1))
                y2 = max(0, min(y2, rgb.shape[0]-1))

                # Some are invalid, apparently..!:
                if x2 <= x1 or y2 <= y1:
                    # print("INVALID!")
                    continue

                crop = rgb[y1:y2, x1:x2]

                # ...and others, empty...:
                if crop.size == 0:
                    # print("EMPTY!")
                    continue

                # print("CROPPED!")
                s_queueLlama.put((tstamp, crop))
                s_queueSave.put((tstamp, payload))

        s_queueYolo.task_done()


def cbckWockMsg(p_ws: websocket.WebSocketApp, p_msg):
    s_queueEsp.put(p_msg)


def cbckWockOpen(p_ws: websocket.WebSocketApp):
    print(f"Connected to `{p_ws.url}`!")


# endregion

if __name__ == "__main__":
    # print("Please enter the ESP32's IP address...!: ", end="")
    s_espIpStr = s_secrets["ip"]
    # s_espIpStr = input()

    threading.Thread(target=workerThreadSave, daemon=True).start()
    threading.Thread(target=workerThreadEsp, daemon=True).start()
    threading.Thread(target=workerThreadYolo, daemon=True).start()
    threading.Thread(target=workerThreadLlama, daemon=True).start()

    websocket.WebSocketApp(
        f"ws://{s_espIpStr}:80/stream",
        on_message=cbckWockMsg,
        on_open=cbckWockOpen,
    ).run_forever(),
