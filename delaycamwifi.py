import cv2
import threading
import requests
import time
from ultralytics import YOLO

model = YOLO("models/best.pt")
model.to("cuda")

ESP32_IP = "http://10.196.229.251"

frame1 = None
frame2 = None

led1_state = False
led2_state = False

cam1_start = None
cam2_start = None

check1 = False
check2 = False


# -------- NON BLOCKING HTTP -------- #

def send_http(url):
    try:
        requests.get(url, timeout=0.2)
    except:
        pass

def send_http_async(url):
    threading.Thread(target=send_http, args=(url,), daemon=True).start()


# -------- CAMERA THREADS -------- #

def cam1_thread():
    global frame1
    cap = cv2.VideoCapture("http://10.196.229.101:81/stream")

    while True:
        ret, f = cap.read()
        if ret:
            frame1 = f


def cam2_thread():
    global frame2
    cap = cv2.VideoCapture("http://10.196.229.153:81/stream")

    while True:
        ret, f = cap.read()
        if ret:
            frame2 = f


threading.Thread(target=cam1_thread, daemon=True).start()
threading.Thread(target=cam2_thread, daemon=True).start()


# -------- MAIN LOOP -------- #

while True:

    if frame1 is None or frame2 is None:
        continue

    frames = [frame1.copy(), frame2.copy()]

    results = model(frames, conf=0.4, device="cuda")

    f1 = frames[0]
    f2 = frames[1]

    r1 = results[0]
    r2 = results[1]

    check1 = False
    check2 = False

    # -------- CAMERA 1 -------- #

    for box in r1.boxes:

        conf = float(box.conf)
        cls = int(box.cls)

        if 0.4 <= conf <= 0.9 and model.names[cls] == "human":
            check1 = True

        x1,y1,x2,y2 = map(int, box.xyxy[0])
        label = f"{model.names[cls]} {conf:.2f}"

        cv2.rectangle(f1,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(f1,label,(x1,y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)


    # -------- CAMERA 2 -------- #

    for box in r2.boxes:

        conf = float(box.conf)
        cls = int(box.cls)

        if 0.4 <= conf <= 0.9 and model.names[cls] == "human":
            check2 = True

        x1,y1,x2,y2 = map(int, box.xyxy[0])
        label = f"{model.names[cls]} {conf:.2f}"

        cv2.rectangle(f2,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(f2,label,(x1,y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,0),2)


    cv2.imshow("Camera 1", f1)
    cv2.imshow("Camera 2", f2)


# -------- TIMER LOGIC -------- #

    # CAMERA 1 TIMER
    if check1:
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


    # CAMERA 2 TIMER
    if check2:
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


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cv2.destroyAllWindows()