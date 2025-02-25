#include <Wire.h>

#define I2C_ADDRESS 0x20

struct DataPacket {
  char val1;
  char val2;
};

void receiveEvent(int bytesReceived) {
  if (bytesReceived < sizeof(DataPacket)) {
    return; // Ignore incomplete packets
  }

  DataPacket packet;
  packet.val1 = Wire.read();
  packet.val2 = Wire.read();

  Serial.printf("Received values: %d, %d\n", packet.val1, packet.val2);
}

void setup() {
  Serial.begin(115200);
  Serial.printf("i2c monitor on 0x20 running...\n");
  Wire.begin(I2C_ADDRESS); // ESP8266 as an I2C slave
  Wire.onReceive(receiveEvent);
}

void loop() {
  delay(10); // Small delay to prevent watchdog resets
}
