#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "rashid";
const char* password = "12345678";

WebServer server(80);

// TB6612FNG Pins
#define PWMA 13
#define AIN1 14
#define AIN2 12

#define BIN1 26
#define BIN2 25
#define PWMB 33

#define STBY 27

// Command queue
char commandQueue[5];
int queueStart = 0;
int queueEnd = 0;

// -------- MOTOR FUNCTIONS --------

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

// -------- QUEUE FUNCTION --------

void addCommand(char cmd){
  commandQueue[queueEnd] = cmd;
  queueEnd = (queueEnd + 1) % 5;
}

// -------- HTTP FUNCTIONS --------

void led1on(){
  addCommand('F');
  server.send(200,"text/plain","Forward command received");
}

void led2on(){
  addCommand('B');
  server.send(200,"text/plain","Backward command received");
}

void alloff(){
  addCommand('S');
  server.send(200,"text/plain","Stop command received");
}

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

  WiFi.begin(ssid,password);

  while(WiFi.status()!=WL_CONNECTED){
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  server.on("/led1on",led1on);
  server.on("/led2on",led2on);
  server.on("/alloff",alloff);

  server.begin();
}

void loop(){

  server.handleClient();

  // Execute commands in order
  if(queueStart != queueEnd){

    char cmd = commandQueue[queueStart];
    queueStart = (queueStart + 1) % 5;

    if(cmd == 'F'){
      forward();
    }
    else if(cmd == 'B'){
      backward();
    }
    else if(cmd == 'S'){
      stopMotor();
    }
  }

}