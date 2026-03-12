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


# ---------------- LOAD MODEL ----------------

model = YOLO("models/best.pt")
model.to("cuda")

print("Model classes:", model.names)


# ---------------- FLASK SERVER ----------------

app = Flask(__name__)

cam1_enabled = True
cam2_enabled = False

led1_state = False
led2_state = False

cam1_start = None
cam2_start = None


@app.route('/post1')
def post1():

    global cam1_enabled, cam2_enabled
    global led1_state, cam1_start

    print("POST1 reached → switch to CAM2")

    cam1_enabled = False
    cam2_enabled = True

    led1_state = False
    cam1_start = None

    return "ok"


@app.route('/post2')
def post2():

    global cam1_enabled, cam2_enabled
    global led2_state, cam2_start

    print("POST2 reached → switch to CAM1")

    cam1_enabled = True
    cam2_enabled = False

    led2_state = False
    cam2_start = None

    return "ok"


def run_server():
    app.run(host="0.0.0.0", port=5000)


threading.Thread(target=run_server, daemon=True).start()


# ---------------- HTTP NON BLOCKING ----------------

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

    frames = [frame1.copy(), frame2.copy()]

    results = model(frames, conf=0.4, device="cuda")

    f1 = frames[0]
    f2 = frames[1]

    check1 = False
    check2 = False


    # -------- CAMERA 1 DETECTION --------

    for box in results[0].boxes:

        conf = float(box.conf)
        cls = int(box.cls)

        label_name = model.names[cls]
        label = f"{label_name} {conf:.2f}"

        if conf > 0.4 and label_name == DETECT_CLASS:
            check1 = True

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        cv2.rectangle(f1, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(
            f1,
            label,
            (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            2
        )


    # -------- CAMERA 2 DETECTION --------

    for box in results[1].boxes:

        conf = float(box.conf)
        cls = int(box.cls)

        label_name = model.names[cls]
        label = f"{label_name} {conf:.2f}"

        if conf > 0.4 and label_name == DETECT_CLASS:
            check2 = True

        x1, y1, x2, y2 = map(int, box.xyxy[0])

        cv2.rectangle(f2, (x1,y1), (x2,y2), (0,255,0), 2)
        cv2.putText(
            f2,
            label,
            (x1, y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            2
        )


    cv2.imshow("Camera1", f1)
    cv2.imshow("Camera2", f2)


    # -------- CAMERA 1 CONTROL --------

    if cam1_enabled:

        if check1:

            if cam1_start is None:
                cam1_start = time.time()

            elif time.time() - cam1_start > DETECT_TIME and not led1_state:

                print("Send /led1on")

                send_http_async(f"{ESP32_IP}/led1on")

                led1_state = True

        else:
            cam1_start = None


    # -------- CAMERA 2 CONTROL --------

    if cam2_enabled:

        if check2:

            if cam2_start is None:
                cam2_start = time.time()

            elif time.time() - cam2_start > DETECT_TIME and not led2_state:

                print("Send /led2on")

                send_http_async(f"{ESP32_IP}/led2on")

                led2_state = True

        else:
            cam2_start = None


    if cv2.waitKey(1) == 27:
        break


cv2.destroyAllWindows()
