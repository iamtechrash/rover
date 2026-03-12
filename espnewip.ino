#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <MFRC522.h>

// -------- WIFI --------
const char* ssid = "rashid";
const char* password = "12345678";

WebServer server(80);

// Python PC address
String pythonServer = "http://10.196.229.135:5000";

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

// -------- RFID UID --------
byte post1UID[4] = {0xE3, 0xB2, 0x8A, 0x04};
byte post2UID[4] = {0x7E, 0x70, 0xD5, 0x05};

// -------- STATE --------
int targetPost = 0;


// -------- SEND MESSAGE TO PYTHON --------
void sendToPython(String msg)
{
  HTTPClient http;

  String url = pythonServer + "/" + msg;

  Serial.print("Sending: ");
  Serial.println(url);

  http.begin(url);
  http.GET();
  http.end();
}


// -------- MOTOR CONTROL --------

void forward()
{
  digitalWrite(AIN1, HIGH);
  digitalWrite(AIN2, LOW);

  digitalWrite(BIN1, HIGH);
  digitalWrite(BIN2, LOW);

  ledcWrite(PWMA, 200);
  ledcWrite(PWMB, 200);

  Serial.println("Moving Forward");
}

void backward()
{
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, HIGH);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, HIGH);

  ledcWrite(PWMA, 200);
  ledcWrite(PWMB, 200);

  Serial.println("Moving Backward");
}

void stopMotor()
{
  ledcWrite(PWMA, 0);
  ledcWrite(PWMB, 0);

  Serial.println("Motor Stopped");
}


// -------- UID CHECK --------
bool compareUID(byte *uid, byte *knownUID)
{
  for(byte i=0;i<4;i++)
  {
    if(uid[i]!=knownUID[i]) return false;
  }

  return true;
}


// -------- HTTP COMMANDS --------

void led1on()
{
  Serial.println("Camera1 request");

  targetPost = 1;

  forward();

  server.send(200,"text/plain","Going to Post1");
}

void led2on()
{
  Serial.println("Camera2 request");

  targetPost = 2;

  backward();

  server.send(200,"text/plain","Going to Post2");
}

void alloff()
{
  stopMotor();

  targetPost = 0;

  server.send(200,"text/plain","Stopped");
}


// -------- SETUP --------

void setup()
{
  Serial.begin(115200);

  pinMode(AIN1,OUTPUT);
  pinMode(AIN2,OUTPUT);

  pinMode(BIN1,OUTPUT);
  pinMode(BIN2,OUTPUT);

  pinMode(STBY,OUTPUT);
  digitalWrite(STBY,HIGH);

  // PWM (ESP32 Core v3 style)
  ledcAttach(PWMA,1000,8);
  ledcAttach(PWMB,1000,8);

  // RFID
  SPI.begin(SCK_PIN,MISO_PIN,MOSI_PIN,SS_PIN);
  rfid.PCD_Init();

  // WIFI
  WiFi.begin(ssid,password);

  Serial.print("Connecting WiFi");

  while(WiFi.status()!=WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  // HTTP routes
  server.on("/led1on",led1on);
  server.on("/led2on",led2on);
  server.on("/alloff",alloff);

  server.begin();
}


// -------- LOOP --------

void loop()
{
  server.handleClient();

  if(!rfid.PICC_IsNewCardPresent()) return;

  if(!rfid.PICC_ReadCardSerial()) return;

  Serial.print("RFID UID: ");

  for(byte i=0;i<rfid.uid.size;i++)
  {
    Serial.print(rfid.uid.uidByte[i],HEX);
    Serial.print(" ");
  }

  Serial.println();


  // -------- POST1 --------
  if(compareUID(rfid.uid.uidByte,post1UID))
  {
    Serial.println("Post1 detected");

    if(targetPost==1)
    {
      stopMotor();

      targetPost=0;

      sendToPython("post1");
    }
  }

  // -------- POST2 --------
  if(compareUID(rfid.uid.uidByte,post2UID))
  {
    Serial.println("Post2 detected");

    if(targetPost==2)
    {
      stopMotor();

      targetPost=0;

      sendToPython("post2");
    }
  }

  rfid.PICC_HaltA();
}
