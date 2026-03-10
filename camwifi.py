import cv2
import threading
import requests
from ultralytics import YOLO

# Load YOLO model
model = YOLO("models/best.pt")
model.to("cuda")

ESP32_IP = "http://10.196.229.251"

frame1 = None
frame2 = None

led1_state = False
led2_state = False


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


# Start camera threads
threading.Thread(target=cam1_thread, daemon=True).start()
threading.Thread(target=cam2_thread, daemon=True).start()


# -------- MAIN LOOP -------- #

while True:

    if frame1 is None or frame2 is None:
        continue

    frames = [frame1.copy(), frame2.copy()]

    # GPU inference
    results = model(frames, conf=0.8, device="cuda")

    cam1_detect = False
    cam2_detect = False

    f1 = frames[0]
    f2 = frames[1]

    r1 = results[0]
    r2 = results[1]

    # -------- CAMERA 1 -------- #

    for box in r1.boxes:

        cls = int(box.cls)

        if model.names[cls] == "human":
            cam1_detect = True

        x1,y1,x2,y2 = map(int, box.xyxy[0])
        conf = float(box.conf)

        label = f"{model.names[cls]} {conf:.2f}"

        cv2.rectangle(f1,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(
            f1,
            label,
            (x1,y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            2
        )

    # -------- CAMERA 2 -------- #

    for box in r2.boxes:

        cls = int(box.cls)

        if model.names[cls] == "human":
            cam2_detect = True

        x1,y1,x2,y2 = map(int, box.xyxy[0])
        conf = float(box.conf)

        label = f"{model.names[cls]} {conf:.2f}"

        cv2.rectangle(f2,(x1,y1),(x2,y2),(0,255,0),2)
        cv2.putText(
            f2,
            label,
            (x1,y1-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0,255,0),
            2
        )

    cv2.imshow("Camera 1", f1)
    cv2.imshow("Camera 2", f2)


    # -------- LED CONTROL -------- #

    # Camera 1 → LED1
# -------- LED CONTROL -------- #

# BOTH cameras detect human
    if cam1_detect and cam2_detect:
        send_http_async(f"{ESP32_IP}/led1on")
        send_http_async(f"{ESP32_IP}/led2on")
        led1_state = True
        led2_state = True

# Only Camera 1
    elif cam1_detect:
        if not led1_state:
            send_http_async(f"{ESP32_IP}/led1on")
            led1_state = True
        if led2_state:
            send_http_async(f"{ESP32_IP}/alloff")
            led2_state = False

# Only Camera 2
    elif cam2_detect:
        if not led2_state:
            send_http_async(f"{ESP32_IP}/led2on")
            led2_state = True
        if led1_state:
            send_http_async(f"{ESP32_IP}/alloff")
            led1_state = False

# No detection
    else:
        if led1_state or led2_state:
            send_http_async(f"{ESP32_IP}/alloff")
            led1_state = False
            led2_state = False


    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cv2.destroyAllWindows()