const int emgPin = 34;

void setup(){
  Serial.begin(115200);

}

void loop(){
  int emg = analogRead(emgPin);

  Serial.println(emg);

  delay(2); 

}