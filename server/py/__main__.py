from multiprocessing.shared_memory import SharedMemory
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

# region Vars.
s_queueCrops: Queue[tuple[float, MatLike]] = Queue()
s_queueEspPayloads: Queue[bytes] = Queue()
s_queueJpegs: Queue[MatLike] = Queue()
s_queueFiles: Queue[MatLike] = Queue()

with open("secrets.json") as f:
    s_secrets = json.load(f)

s_espIpStr = ""
s_llamaPort = 3000
s_pathJpegs = "./photos"
s_llamaUrl = f"http://localhost:{s_llamaPort}"
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
    sql = "UPDATE entries SET plate = %s WHERE tstamp = %s; COMMIT;"
    while True:
        tstamp, crop = s_queueCrops.get()

        print("CONNECTING TO LLAMA SERVER!")
        print("CONNECTING TO LLAMA SERVER!")
        print("CONNECTING TO LLAMA SERVER!")

        ok, jpeg = cv2.imencode(".jpg", crop)
        if not ok:
            s_queueCrops.task_done()
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

        b64 = base64.b64encode(jpeg).decode("utf-8")

        payload = {
            "model": "Qwen3VL-2B-Instruct-Q4_K_M.gguf",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "The image may contain a vehicle license plate. If so, respond with *just* said number in full. In case of any issues, respond with just \"NULL\" without the quotes."
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{b64}"
                        }
                    ]
                }
            ]
        }

        resHttp = requests.post(
            f"{s_llamaUrl}/v1/chat/completions",
            json=payload,
            timeout=30,
        )

        try:
            resHttp.raise_for_status()
            resJson = resHttp.json()
            plate: str = resJson["choices"][0]["message"]["content"]

            if len(plate) > 32:
                plate = "NULL"

            cur.execute(sql, (plate, tstamp))
        except requests.HTTPErrore as e:
            print(e)
            pass

        s_queueCrops.task_done()


def workerThreadJpeg():
    """
    Converts all ESP32-CAM payloads to `MatLike`s.
    """
    while True:
        p = s_queueEspPayloads.get()

        if p is None:
            s_queueEspPayloads.task_done()
            continue

        int8 = np.frombuffer(p, dtype=np.uint8)
        jpeg = cv2.imdecode(int8, cv2.IMREAD_COLOR)

        if jpeg is None:
            s_queueEspPayloads.task_done()
            continue

        s_queueFiles.put(p)
        s_queueJpegs.put(jpeg)
        s_queueEspPayloads.task_done()


def workerThreadSave():
    """
    Writes JPEGs to disk and their timestamp to the DB.
    """
    cur = s_dbSave.cursor()
    # These shall NEVER BE F-STRINGS!:
    sql = f"INSERT INTO entries(tstamp) VALUES(%s); COMMIT;"
    # EASIEST way to get injection attacks!
    while True:
        payload = s_queueFiles.get()

        if payload is None:
            s_queueFiles.task_done()
            continue

        tstamp = time.time()
        with open(f"{s_pathJpegs}/{tstamp}.jpg", "wb") as f:
            f.write(payload)

        cur.execute(sql, (tstamp,))
        s_queueFiles.task_done()


def workerThreadYolo():
    """
    Runs YOLOv11 inference for LPR and notifies Express.
    """
    while True:
        jpeg: cv2.MatLike = s_queueJpegs.get()
        rgb = jpeg[:, :, ::-1]
        results = s_yolo.predict(source=rgb)

        if not hasattr(results, "boxes"):
            s_queueJpegs.task_done()
            continue

        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            # confidence = float(box.conf[0])
            # cls = int(box.cls[0])
            # label = results.names[cls]
            crop = jpeg[y1:y2, x1:x2]

            if crop is not None and crop.size != 0:
                s_queueCrops.put(crop)

        s_queueJpegs.task_done()


def cbckWockMsg(p_ws, p_msg):
    s_queueEspPayloads.put(p_msg)


# endregion

if __name__ == "__main__":
    print("Please enter the ESP32's IP address...!: ", end="")
    s_espIpStr = input()

    threading.Thread(target=workerThreadSave, daemon=True).start()
    threading.Thread(target=workerThreadJpeg, daemon=True).start()
    threading.Thread(target=workerThreadYolo, daemon=True).start()
    threading.Thread(target=workerThreadLlama, daemon=True).start()

    websocket.WebSocketApp(
        f"ws://{s_espIpStr}:80/stream",
        on_message=cbckWockMsg
    ).run_forever(),
