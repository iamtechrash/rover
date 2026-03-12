import cv2
import socket
import threading
import requests
import time
from queue import Queue
from ultralytics import YOLO


# -------------------------
# MODEL
# -------------------------

model = YOLO("models/best.pt")
model.to("cuda")


# -------------------------
# CAMERA URL
# -------------------------

CAM1_URL = "http://10.243.104.133:8080/video"
CAM2_URL = "http://10.243.104.39:8080/video"


# -------------------------
# ESP32
# -------------------------

ESP32_IP = "http://10.196.229.251"


# -------------------------
# GLOBAL STATE
# -------------------------

frame_queue = Queue(maxsize=5)

active_cam = 1

cam1_start = None
cam2_start = None

led1_state = False
led2_state = False


# -------------------------
# UDP SERVER
# -------------------------

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))


def listen_esp32():
    global active_cam

    while True:
        data, _ = sock.recvfrom(1024)
        cmd = data.decode().strip()

        print("CMD:", cmd)

        if cmd == "1":
            active_cam = 1

        elif cmd == "2":
            active_cam = 2


threading.Thread(target=listen_esp32, daemon=True).start()


# -------------------------
# NON BLOCKING HTTP
# -------------------------

def send_http(url):
    try:
        requests.get(url, timeout=0.2)
    except:
        pass


def send_http_async(url):
    threading.Thread(target=send_http, args=(url,), daemon=True).start()


# -------------------------
# CAMERA THREAD
# -------------------------

def camera_thread(url, cam_id):

    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        if frame_queue.full():
            frame_queue.get()

        frame_queue.put((cam_id, frame))


threading.Thread(target=camera_thread, args=(CAM1_URL,1), daemon=True).start()
threading.Thread(target=camera_thread, args=(CAM2_URL,2), daemon=True).start()


# -------------------------
# YOLO WORKER
# -------------------------

def yolo_worker():

    global cam1_start, cam2_start
    global led1_state, led2_state

    while True:

        cam_id, frame = frame_queue.get()

        if cam_id != active_cam:
            continue

        results = model(frame, conf=0.4, device="cuda")[0]

        detect = False

        for box in results.boxes:

            conf = float(box.conf)
            cls = int(box.cls)

            if 0.4 <= conf <= 0.9 and model.names[cls] == "human":
                detect = True

            x1,y1,x2,y2 = map(int, box.xyxy[0])

            label = f"{model.names[cls]} {conf:.2f}"

            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,label,(x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)


        # -------- TIMER LOGIC --------

        if cam_id == 1:

            if detect:

                if cam1_start is None:
                    cam1_start = time.time()

                elif time.time() - cam1_start >= 3 and not led1_state:
                    send_http_async(f"{ESP32_IP}/led1on")
                    led1_state = True

            else:

                cam1_start = None

                if led1_state:
                    send_http_async(f"{ESP32_IP}/alloff")
                    led1_state = False


        if cam_id == 2:

            if detect:

                if cam2_start is None:
                    cam2_start = time.time()

                elif time.time() - cam2_start >= 3 and not led2_state:
                    send_http_async(f"{ESP32_IP}/led2on")
                    led2_state = True

            else:

                cam2_start = None

                if led2_state:
                    send_http_async(f"{ESP32_IP}/alloff")
                    led2_state = False


        cv2.imshow("Robot Vision", frame)

        cv2.waitKey(1)


threading.Thread(target=yolo_worker, daemon=True).start()


# -------------------------
# KEEP PROGRAM ALIVE
# -------------------------

while True:
    time.sleep(1)
