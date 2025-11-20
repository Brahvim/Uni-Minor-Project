import cv2
import requests
import numpy as np

print("Please enter the ESP32's IP address...!: ", end="")
s_espUrl = f"http://{input()}:80/sub"
requests.get(s_espUrl)

while True:
    cv2.imshow(
        s_espUrl,
        cv2.imdecode(
            np.frombuffer(
                ,
                np.uint8
            ),
            cv2.IMREAD_COLOR
        )
    )
    cv2.waitKey(1)  # Refresh CV window.

