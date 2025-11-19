# from ultralytics import YOLO
from queue import Queue
import netifaces as ni
import numpy as np
import websockets
import subprocess
import ipaddress
import threading
import requests
import asyncio
import json
import sys
import cv2

# region Vars.
s_secrets = {}

with open("./secrets.json") as f:
    s_secrets.update(json.load(f))

s_pathYolos = "./yolov11-license-plate-detection"
s_pathJpegs = "./photos"

s_queueEspPayloads = Queue()
s_queuePlates = Queue()
s_queueJpegs = Queue()

s_espIp = ""
s_espMac = s_secrets["mac"]
# s_yolo = YOLO(f"{s_pathYolos}/license-plate-finetune-v1n.pt")
# endregion

# region Utils.


def utilEspIpPingNets(p_iface: str = "wlo1"):
    """
    [UNUSED!] Force ping everyone on yo' nets!
    """
    for ip in ipaddress.ip_network(ni.ifaddresses(p_iface)[ni.AF_INET][0]["gateway"], strict=False).hosts():
        ipstr = str(ip)
        # print(f"Pinging `{ipstr}`...")
        subprocess.Popen(["ping", "-c", "1", "-W", "1", ipstr])


def utilEspIpNeigh(p_mac: str = s_espMac):
    def doit():
        arp = subprocess.check_output(["ip", "neighbour"], text=True)
        for l in arp.splitlines():
            if p_mac in l.lower():
                return l

    # if not doit():
        # print("ESP32-CAM not in `ip neighbour` logs! Pinging ALL subnets...")
        # utilEspIpPingNets()
    return doit()


def utilEspIpScan(p_mac: str = s_espMac, p_iface: str = "wlo1"):
    p_mac = p_mac.lower()
    request = ARP(pdst="192.168.1.0/24")
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = broadcast / request

    ans = srp(packet, iface=p_iface, timeout=2, verbose=0)[0]

    for _, r in ans:
        if r.hwsrc.lower() == p_mac:
            s_espIp = r.psrc
            return r.psrc

    return None


def utilEspIpFind(p_mac: str = s_espMac):
    p_mac = p_mac.lower()

    with open("/proc/net/arp") as f:
        for line in f.readlines()[1:]:
            cols = line.split()
            ip = cols[0]
            mac = cols[3].lower()
            if mac == p_mac:
                return ip

    return None


# endregion

# region Workers.

def workerThreadDecode():
    while True:
        p = s_queueEspPayloads.get()

        int8 = np.frombuffer(p, dtype=np.uint8)
        jpeg = cv2.imdecode(int8, cv2.IMREAD_COLOR)

        if jpeg is not None:
            s_queueJpegs.put(jpeg)

        s_queueEspPayloads.task_done()


def workerThreadWrite():
    while True:
        jpeg = s_queueJpegs.get()

        with open(f"{s_pathJpegs}/{0}.jpg", "w") as f:
            f.write(jpeg)

        s_queueEspPayloads.task_done()


def workerThreadYolo():
    while True:
        jpeg = s_queueJpegs.get()

        rgb = jpeg[:, :, ::-1]

        # s_yolo.predict(source=rgb)

        s_queueJpegs.task_done()


async def workerWockFetchEsp(p_ip: str):
    # print(sys.argv)
    # ip = sys.argv[0] if len(sys.argv) > 0 else utilEspIpNeigh()
    # utilEspIpFind()
    # utilEspIpScan()

    # if not ip:
    # print("Couldn't see Brahvim's ESP32-CAM in ARP cache just yet, exiting...")
    # sys.exit(1)

    ip = p_ip
    print(f"Attempting to connect to ESP32@`{ip}`...")
    async with websockets.connect(f"ws://{ip}:8000/stream") as wock:
        async for message in wock:
            s_queueEspPayloads.put(message)


# endregion

if __name__ == "__main__":
    print("Please enter the ESP32's IP address...!: ", end="")
    uin = input()

    threading.Thread(target=workerThreadDecode, daemon=True).start()
    threading.Thread(target=workerThreadYolo, daemon=True).start()
    asyncio.run(workerWockFetchEsp(uin))
