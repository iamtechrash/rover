#include <WiFi.h>
#include <WebServer.h>
#include <SPI.h>
#include <MFRC522.h>

const char* ssid = "rashid";
const char* password = "12345678";

WebServer server(80);

// -------- MOTOR PINS --------
#define PWMA 13
#define AIN1 14
#define AIN2 12

#define BIN1 26
#define BIN2 25
#define PWMB 33

#define STBY 27

// -------- RFID PINS --------
#define SS_PIN 5
#define RST_PIN 23

#define SCK_PIN 18
#define MOSI_PIN 19
#define MISO_PIN 21

MFRC522 rfid(SS_PIN, RST_PIN);

// -------- PIR + SOUND --------
#define PIR_PIN 4
#define SOUND_PIN 2
#define RESOLUTION 8

// -------- RFID UID --------
byte post1UID[4] = {0xE3, 0xB2, 0x8A, 0x04};
byte post2UID[4] = {0x7E, 0x70, 0xD5, 0x05};

// -------- SYSTEM STATE --------
int currentPost = 0;
int targetPost = 0;

// -------- MOTOR FUNCTIONS --------

void forward() {

  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);

  analogWrite(PWMA, 200);
  analogWrite(PWMB, 200);

  Serial.println("Moving Forward");
}

void backward() {

  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);

  analogWrite(PWMA, 200);
  analogWrite(PWMB, 200);

  Serial.println("Moving Backward");
}

void stopMotor() {

  analogWrite(PWMA, 0);
  analogWrite(PWMB, 0);

  Serial.println("Motor Stopped");
}

// -------- SOUND FUNCTION --------

void ambulanceSound() {

  for(int f = 800; f <= 1500; f += 10){
    ledcAttach(SOUND_PIN, f, RESOLUTION);
    ledcWrite(SOUND_PIN, 120);
    delay(5);
  }

  for(int f = 1500; f >= 800; f -= 10){
    ledcAttach(SOUND_PIN, f, RESOLUTION);
    ledcWrite(SOUND_PIN, 120);
    delay(5);
  }
}

// -------- UID CHECK --------

bool compareUID(byte *uid, byte *knownUID) {

  for (byte i = 0; i < 4; i++) {
    if (uid[i] != knownUID[i]) return false;
  }
  return true;
}

// -------- HTTP COMMANDS --------

void led1on(){

  Serial.println("Camera 1 Request");

  if(currentPost == 1){
    Serial.println("Already at Post 1");
    server.send(200,"text/plain","Already at Post 1");
    return;
  }

  targetPost = 1;
  forward();

  server.send(200,"text/plain","Moving to Post 1");
}

void led2on(){

  Serial.println("Camera 2 Request");

  if(currentPost == 2){
    Serial.println("Already at Post 2");
    server.send(200,"text/plain","Already at Post 2");
    return;
  }

  targetPost = 2;
  backward();

  server.send(200,"text/plain","Moving to Post 2");
}

void alloff(){

  stopMotor();
  targetPost = 0;

  server.send(200,"text/plain","Stopped");
}

// -------- SETUP --------

void setup(){

  Serial.begin(115200);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);

  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  pinMode(STBY, OUTPUT);
  digitalWrite(STBY, HIGH);

  pinMode(PIR_PIN, INPUT);

  // SOUND PWM start
  ledcAttach(SOUND_PIN, 1000, RESOLUTION);

  // RFID start
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

  server.on("/led1on",led1on);
  server.on("/led2on",led2on);
  server.on("/alloff",alloff);

  server.begin();
}

// -------- LOOP --------

void loop(){

  server.handleClient();

  // -------- PIR MOTION --------
  int pirState = digitalRead(PIR_PIN);

  if (pirState == HIGH) {

    Serial.println("Motion Detected - Sound ON");
    ambulanceSound();
  }
  else {

    ledcWrite(SOUND_PIN, 0);
  }

  // -------- RFID CHECK --------

  if (!rfid.PICC_IsNewCardPresent()) return;
  if (!rfid.PICC_ReadCardSerial()) return;

  Serial.print("Card UID: ");

  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i], HEX);
    Serial.print(" ");
  }

  Serial.println();

  // POST 1
  if(compareUID(rfid.uid.uidByte, post1UID)){

    Serial.println("Post 1 Detected");

    currentPost = 1;

    if(targetPost == 1){
      stopMotor();
      targetPost = 0;
    }
  }

  // POST 2
  else if(compareUID(rfid.uid.uidByte, post2UID)){

    Serial.println("Post 2 Detected");

    currentPost = 2;

    if(targetPost == 2){
      stopMotor();
      targetPost = 0;
    }
  }

  rfid.PICC_HaltA();
}
