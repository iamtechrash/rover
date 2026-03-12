#include <WiFi.h>
#include <WebServer.h>
#include <WiFiUdp.h>
#include <SPI.h>
#include <MFRC522.h>

// ---------------- WIFI ----------------
const char* ssid = "S";
const char* password = "12345678";

const char* laptopIP = "10.243.104.204";
const int udpPort = 5005;

WiFiUDP udp;
WebServer server(80);

// ---------------- MOTOR PINS ----------------

#define PWMA 13
#define AIN1 14
#define AIN2 12

#define BIN1 26
#define BIN2 25
#define PWMB 33

#define STBY 27

// ---------------- RFID ----------------

#define SS_PIN 5
#define RST_PIN 23
#define SCK_PIN 18
#define MOSI_PIN 19
#define MISO_PIN 21

MFRC522 rfid(SS_PIN, RST_PIN);

// RFID UID
byte post1UID[4] = {0xE3, 0xB2, 0x8A, 0x04};
byte post2UID[4] = {0x7E, 0x70, 0xD5, 0x05};

// ---------------- MOTOR FUNCTIONS ----------------

void forward() {

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);

  analogWrite(PWMA, 200);
  analogWrite(PWMB, 200);

  Serial.println("Forward");
}

void backward() {

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);

  analogWrite(PWMA, 200);
  analogWrite(PWMB, 200);

  Serial.println("Backward");
}

void stopMotor() {

  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);

  Serial.println("Stop");
}

// ---------------- HTTP COMMANDS ----------------

void led1on() {
  Serial.println("Command: Post1");
  forward();
  server.send(200,"text/plain","Forward");
}

void led2on() {
  Serial.println("Command: Post2");
  backward();
  server.send(200,"text/plain","Backward");
}

void alloff() {
  stopMotor();
  server.send(200,"text/plain","Stopped");
}

// ---------------- UID CHECK ----------------

bool compareUID(byte *uid, byte *knownUID) {

  for(byte i=0;i<4;i++) {
    if(uid[i] != knownUID[i]) return false;
  }

  return true;
}

// ---------------- SETUP ----------------

void setup() {

  Serial.begin(115200);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);

  // RFID
  SPI.begin(SCK_PIN, MISO_PIN, MOSI_PIN, SS_PIN);
  rfid.PCD_Init();

  // WIFI
  WiFi.begin(ssid,password);

  while(WiFi.status()!=WL_CONNECTED){
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // HTTP ROUTES
  server.on("/led1on",led1on);
  server.on("/led2on",led2on);
  server.on("/alloff",alloff);

  server.begin();
}

// ---------------- LOOP ----------------

void loop() {

  server.handleClient();

  // -------- RFID CHECK --------

  if(!rfid.PICC_IsNewCardPresent()) return;
  if(!rfid.PICC_ReadCardSerial()) return;

  Serial.print("Card UID: ");

  for(byte i=0;i<rfid.uid.size;i++){
    Serial.print(rfid.uid.uidByte[i],HEX);
    Serial.print(" ");
  }

  Serial.println();

  // -------- POST1 --------

  if(compareUID(rfid.uid.uidByte,post1UID)) {

    Serial.println("RFID Post1");

    udp.beginPacket(laptopIP, udpPort);
    udp.write("1");
    udp.endPacket();

    stopMotor();
  }

  // -------- POST2 --------

  else if(compareUID(rfid.uid.uidByte,post2UID)) {

    Serial.println("RFID Post2");

    udp.beginPacket(laptopIP, udpPort);
    udp.write("2");
    udp.endPacket();

    stopMotor();
  }

  rfid.PICC_HaltA();
}
