from multiprocessing.shared_memory import SharedMemory
from ultralytics import YOLO
from llama_cpp import Llama
from queue import Queue
import numpy as np
import threading
import websocket
import requests
import cv2

# region Vars.
s_queueEspPayloads = Queue()
s_queuePlates = Queue()
s_queueJpegs = Queue()
s_queueFiles = Queue()

s_espIpStr = ""
s_llamaPort = 3000
s_pathJpegs = "./photos"
s_pathYolos = "./yolov11-license-plate-detection"
s_yolo = YOLO(f"{s_pathYolos}/license-plate-finetune-v1n.pt")
# endregion

# region Workers.


def workerThreadJpeg():
    """
    Converts all ESP32-CAM payloads to `MatLike`s.
    """
    while True:
        p: bytes = s_queueEspPayloads.get()
        m = SharedMemory(create=True, size=len(p))

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


def workerThreadDisk():
    """
    Writes JPEGs to disk.
    """
    while True:
        payload = s_queueFiles.get()

        if payload is None:
            s_queueFiles.task_done()
            continue

        with open(f"{s_pathJpegs}/{0}.jpg", "wb") as f:
            f.write(payload)

        s_queueFiles.task_done()


def workerThreadYolo():
    """
    Runs YOLOv11 inference for LPR and notifies Express.
    """
    while True:
        jpeg = s_queueJpegs.get()
        rgb = jpeg[:, :, ::-1]
        results = s_yolo.predict(source=rgb)

        if not hasattr(results, "boxes"):
            s_queueJpegs.task_done()
            continue

        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            confidence = float(box.conf[0])
            cls = int(box.cls[0])
            label = results.names[cls]
            # print(f"Plate number: `{label}`!")

        s_queueJpegs.task_done()


def workerThreadOcr():
    requests.post(f"http://localhost:{s_llamaPort}/")


def cbckWockMsg(p_ws, p_msg):

    s_queueEspPayloads.put(p_msg)


# endregion

if __name__ == "__main__":
    print("Please enter the ESP32's IP address...!: ", end="")
    s_espIpStr = input()

    threading.Thread(target=workerThreadDisk, daemon=True).start()
    threading.Thread(target=workerThreadJpeg, daemon=True).start()
    threading.Thread(target=workerThreadYolo, daemon=True).start()

    websocket.WebSocketApp(
        f"ws://{s_espIpStr}:80/stream",
        on_message=cbckWockMsg
    ).run_forever(),
