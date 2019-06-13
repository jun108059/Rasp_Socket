#include <SPI.h>
#include <MFRC522.h>

#define RST_PIN 9
#define SS_PIN 10

MFRC522 mfrc(SS_PIN, RST_PIN);

void setup(){
  Serial.begin(9600);
  SPI.begin();
  mfrc.PCD_Init();

}
void loop(){
  if(!mfrc.PICC_IsNewCardPresent() || !mfrc.PICC_ReadCardSerial()){
    delay(500);
    return;
  }
  if(mfrc.uid.uidByte[0]==73 && mfrc.uid.uidByte[1] == 197 && mfrc.uid.uidByte[2] == 160 && mfrc.uid.uidByte[3] ==99){
    Serial.println("1");
  }
  if(mfrc.uid.uidByte[0]==65 && mfrc.uid.uidByte[1] == 144 && mfrc.uid.uidByte[2] == 138 && mfrc.uid.uidByte[3] ==32){
    Serial.println("2");
  }
  if(mfrc.uid.uidByte[0]==89 && mfrc.uid.uidByte[1] == 24 && mfrc.uid.uidByte[2] == 155 && mfrc.uid.uidByte[3] ==99){
    Serial.println("3");
  }
  if(mfrc.uid.uidByte[0]==179 && mfrc.uid.uidByte[1] == 40 && mfrc.uid.uidByte[2] == 9 && mfrc.uid.uidByte[3] ==26){
    Serial.println("4");
  }
}
