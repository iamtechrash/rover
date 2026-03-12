import cv2
import threading
import requests
import time
from ultralytics import YOLO
from flask import Flask

# ---------------- FLASK SERVER ---------------- #

app = Flask(__name__)

cam1_enabled = True
cam2_enabled = False

@app.route('/post1')
def post1():
    global cam1_enabled, cam2_enabled

    print("POST1 reached")

    cam1_enabled = False
    cam2_enabled = True

    return "ok"

@app.route('/post2')
def post2():
    global cam1_enabled, cam2_enabled

    print("POST2 reached")

    cam1_enabled = True
    cam2_enabled = False

    return "ok"

def run_server():
    app.run(host="0.0.0.0",port=5000)

threading.Thread(target=run_server,daemon=True).start()

# ---------------- YOLO ---------------- #

model = YOLO("models/best.pt")
model.to("cuda")

ESP32_IP = "http://10.196.229.251"

frame1=None
frame2=None

cam1_start=None
cam2_start=None

led1_state=False
led2_state=False

# ---------------- HTTP ---------------- #

def send_http(url):
    try:
        requests.get(url,timeout=0.2)
    except:
        pass

def send_http_async(url):
    threading.Thread(target=send_http,args=(url,),daemon=True).start()

# ---------------- CAMERA THREADS ---------------- #

def cam1_thread():
    global frame1
    cap=cv2.VideoCapture("http://10.196.229.101:81/stream")

    while True:
        ret,f=cap.read()
        if ret:
            frame1=f

def cam2_thread():
    global frame2
    cap=cv2.VideoCapture("http://10.196.229.153:81/stream")

    while True:
        ret,f=cap.read()
        if ret:
            frame2=f

threading.Thread(target=cam1_thread,daemon=True).start()
threading.Thread(target=cam2_thread,daemon=True).start()

# ---------------- MAIN LOOP ---------------- #

while True:

    if frame1 is None or frame2 is None:
        continue

    frames=[frame1.copy(),frame2.copy()]

    results=model(frames,conf=0.4,device="cuda")

    f1=frames[0]
    f2=frames[1]

    check1=False
    check2=False

    # CAMERA1
    for box in results[0].boxes:

        conf=float(box.conf)
        cls=int(box.cls)

        if conf>0.4 and model.names[cls]=="human":
            check1=True

        x1,y1,x2,y2=map(int,box.xyxy[0])

        cv2.rectangle(f1,(x1,y1),(x2,y2),(0,255,0),2)

    # CAMERA2
    for box in results[1].boxes:

        conf=float(box.conf)
        cls=int(box.cls)

        if conf>0.4 and model.names[cls]=="human":
            check2=True

        x1,y1,x2,y2=map(int,box.xyxy[0])

        cv2.rectangle(f2,(x1,y1),(x2,y2),(0,255,0),2)

    cv2.imshow("cam1",f1)
    cv2.imshow("cam2",f2)

    # CAMERA1 LOGIC
    if cam1_enabled and check1:

        if cam1_start is None:
            cam1_start=time.time()

        elif time.time()-cam1_start>3 and not led1_state:

            send_http_async(f"{ESP32_IP}/led1on")
            led1_state=True

    else:
        cam1_start=None


    # CAMERA2 LOGIC
    if cam2_enabled and check2:

        if cam2_start is None:
            cam2_start=time.time()

        elif time.time()-cam2_start>3 and not led2_state:

            send_http_async(f"{ESP32_IP}/led2on")
            led2_state=True

    else:
        cam2_start=None


    if cv2.waitKey(1)==27:
        break

cv2.destroyAllWindows()
