import cv2
import socket
import threading
import time
from queue import Queue
from ultralytics import YOLO

# -------------------------
# CONFIGURATION
# -------------------------
UDP_IP_ESP32 = "10.196.229.251" # ESP32 IP
UDP_PORT_ESP32 = 8888           # Port ESP32 listens on
UDP_PORT_LAPTOP = 5005          # Port Laptop listens on

CAM1_URL = "http://10.243.104.133:8080/video"
CAM2_URL = "http://10.243.104.39:8080/video"

model = YOLO("models/best.pt").to("cuda")

# -------------------------
# GLOBAL STATE
# -------------------------
frame_queue = Queue(maxsize=1)
active_cam = 1
cam_start_time = None
led_state = False 

# -------------------------
# UDP SETUP
# -------------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", UDP_PORT_LAPTOP))

def send_udp(cmd):
    """Sends command to ESP32 over UDP."""
    sock.sendto(cmd.encode(), (UDP_IP_ESP32, UDP_PORT_ESP32))

def listen_esp32():
    global active_cam
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            cmd = data.decode().strip()
            if cmd in ["1", "2"]:
                active_cam = int(cmd)
                print(f"Switching to Camera {active_cam}")
        except: pass

threading.Thread(target=listen_esp32, daemon=True).start()

# -------------------------
# CAMERA THREADS
# -------------------------
def camera_worker(url, cam_id):
    cap = cv2.VideoCapture(url)
    while True:
        ret, frame = cap.read()
        if not ret: continue
        
        # Only queue if it's the active camera to prevent lag
        if cam_id == active_cam:
            if not frame_queue.empty():
                try: frame_queue.get_nowait()
                except: pass
            frame_queue.put(frame)

threading.Thread(target=camera_worker, args=(CAM1_URL, 1), daemon=True).start()
threading.Thread(target=camera_worker, args=(CAM2_URL, 2), daemon=True).start()

# -------------------------
# MAIN LOOP (YOLO + UI)
# -------------------------
print("System Running...")
while True:
    if frame_queue.empty():
        continue

    frame = frame_queue.get()
    results = model(frame, conf=0.4, device="cuda", verbose=False)[0]
    
    detect = False
    for box in results.boxes:
        cls = int(box.cls)
        conf = float(box.conf)
        if 0.4 <= conf <= 0.9 and model.names[cls] == "human":
            detect = True
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Logic for Motors
    if detect:
        if cam_start_time is None:
            cam_start_time = time.time()
        elif time.time() - cam_start_time >= 3 and not led_state:
            cmd = "led1on" if active_cam == 1 else "led2on"
            send_udp(cmd)
            led_state = True
    else:
        cam_start_time = None
        if led_state:
            send_udp("alloff")
            led_state = False

    cv2.imshow("Robot Vision", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
