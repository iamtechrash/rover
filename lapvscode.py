import cv2
import threading
import requests
import time
from ultralytics import YOLO
from flask import Flask

# ---------------- SETTINGS ----------------

ESP32_IP = "http://10.196.229.251"

CAM1_STREAM = "http://10.196.229.101:81/stream"
CAM2_STREAM = "http://10.196.229.153:81/stream"

DETECT_CLASS = "human"
DETECT_TIME = 4

# ---------------- MODEL ----------------

model = YOLO("models/best.pt")
model.to("cuda")

print("Model classes:", model.names)

# ---------------- STATE MACHINE ----------------

ACTIVE_CAM = 1

cam1_start = None
cam2_start = None

led1_sent = False
led2_sent = False

# ---------------- FLASK SERVER ----------------

app = Flask(__name__)

@app.route("/post1")
def post1():
    global ACTIVE_CAM, led1_sent, cam1_start

    print("POST1 reached")

    ACTIVE_CAM = 2
    led1_sent = False
    cam1_start = None

    return "ok"

@app.route("/post2")
def post2():
    global ACTIVE_CAM, led2_sent, cam2_start

    print("POST2 reached")

    ACTIVE_CAM = 1
    led2_sent = False
    cam2_start = None

    return "ok"


def run_server():
    app.run(host="0.0.0.0", port=5000)


threading.Thread(target=run_server, daemon=True).start()

# ---------------- HTTP ----------------

def send_http(url):
    try:
        requests.get(url, timeout=0.2)
    except:
        pass

def send_http_async(url):
    threading.Thread(target=send_http, args=(url,), daemon=True).start()

# ---------------- CAMERA THREADS ----------------

frame1 = None
frame2 = None


def cam1_thread():
    global frame1

    cap = cv2.VideoCapture(CAM1_STREAM)

    while True:
        ret, f = cap.read()
        if ret:
            frame1 = f


def cam2_thread():
    global frame2

    cap = cv2.VideoCapture(CAM2_STREAM)

    while True:
        ret, f = cap.read()
        if ret:
            frame2 = f


threading.Thread(target=cam1_thread, daemon=True).start()
threading.Thread(target=cam2_thread, daemon=True).start()

# ---------------- MAIN LOOP ----------------

while True:

    if frame1 is None or frame2 is None:
        continue

    # ---------------- CAMERA 1 ACTIVE ----------------

    if ACTIVE_CAM == 1:

        frame = frame1.copy()

        results = model(frame, conf=0.4, device="cuda")

        check = False

        for box in results[0].boxes:

            conf = float(box.conf)
            cls = int(box.cls)

            label_name = model.names[cls]

            if conf > 0.4 and label_name == DETECT_CLASS:
                check = True

            x1,y1,x2,y2 = map(int,box.xyxy[0])

            label = f"{label_name} {conf:.2f}"

            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,label,(x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

        cv2.imshow("Camera1", frame)

        if check:

            if cam1_start is None:
                cam1_start = time.time()

            elif time.time() - cam1_start >= DETECT_TIME and not led1_sent:

                print("Sending /led1on")

                send_http_async(f"{ESP32_IP}/led1on")

                led1_sent = True

        else:
            cam1_start = None

    # ---------------- CAMERA 2 ACTIVE ----------------

    elif ACTIVE_CAM == 2:

        frame = frame2.copy()

        results = model(frame, conf=0.4, device="cuda")

        check = False

        for box in results[0].boxes:

            conf = float(box.conf)
            cls = int(box.cls)

            label_name = model.names[cls]

            if conf > 0.4 and label_name == DETECT_CLASS:
                check = True

            x1,y1,x2,y2 = map(int,box.xyxy[0])

            label = f"{label_name} {conf:.2f}"

            cv2.rectangle(frame,(x1,y1),(x2,y2),(0,255,0),2)
            cv2.putText(frame,label,(x1,y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)

        cv2.imshow("Camera2", frame)

        if check:

            if cam2_start is None:
                cam2_start = time.time()

            elif time.time() - cam2_start >= DETECT_TIME and not led2_sent:

                print("Sending /led2on")

                send_http_async(f"{ESP32_IP}/led2on")

                led2_sent = True

        else:
            cam2_start = None

    if cv2.waitKey(1) == 27:
        break

cv2.destroyAllWindows()
