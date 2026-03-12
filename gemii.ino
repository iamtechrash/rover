#include <WiFi.h>
#include <WiFiUdp.h>
#include <SPI.h>
#include <MFRC522.h>

// WiFi Config
const char* ssid = "S";
const char* password = "12345678";
const char* laptopIP = "10.243.104.204";
const int laptopPort = 5005;
const int localPort = 8888;

WiFiUDP udp;
char packetBuffer[255];

// Motor Pins
#define PWMA 13
#define AIN1 14
#define AIN2 12
#define BIN1 26
#define BIN2 25
#define PWMB 33
#define STBY 27

// RFID Pins
#define SS_PIN 5
#define RST_PIN 23
MFRC522 rfid(SS_PIN, RST_PIN);

byte post1UID[4] = {0xE3, 0xB2, 0x8A, 0x04};
byte post2UID[4] = {0x7E, 0x70, 0xD5, 0x05};

void move(bool forward_dir, int speed) {
  digitalWrite(AIN1, forward_dir);
  digitalWrite(AIN2, !forward_dir);
  digitalWrite(BIN1, forward_dir);
  digitalWrite(BIN2, !forward_dir);
  analogWrite(PWMA, speed);
  analogWrite(PWMB, speed);
}

void stopMotor() {
  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(PWMA, OUTPUT); pinMode(AIN1, OUTPUT); pinMode(AIN2, OUTPUT);
  pinMode(PWMB, OUTPUT); pinMode(BIN1, OUTPUT); pinMode(BIN2, OUTPUT);
  pinMode(STBY, OUTPUT); digitalWrite(STBY, HIGH);

  SPI.begin();
  rfid.PCD_Init();

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  
  udp.begin(localPort);
  Serial.println("\nUDP Listening on port 8888");
}

void loop() {
  // 1. Receive Commands from Laptop
  int packetSize = udp.parsePacket();
  if (packetSize) {
    int len = udp.read(packetBuffer, 255);
    if (len > 0) packetBuffer[len] = 0;
    String cmd = String(packetBuffer);

    if (cmd == "led1on") move(true, 200);      // Forward
    else if (cmd == "led2on") move(false, 200); // Backward
    else if (cmd == "alloff") stopMotor();
  }

  // 2. Check RFID (Non-blocking)
  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    String msg = "";
    if (memcmp(rfid.uid.uidByte, post1UID, 4) == 0) msg = "1";
    else if (memcmp(rfid.uid.uidByte, post2UID, 4) == 0) msg = "2";

    if (msg != "") {
      udp.beginPacket(laptopIP, laptopPort);
      udp.print(msg);
      udp.endPacket();
      stopMotor();
      Serial.println("Sent to Laptop: " + msg);
    }
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();
  }
}
