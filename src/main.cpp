#include <Arduino.h>
#include <TFT_eSPI.h>

TFT_eSPI tft = TFT_eSPI();

void setup() {
  Serial.begin(115200);
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.setTextSize(2);
  tft.setCursor(10, 20);
  tft.println("PedalPets");
  tft.setTextColor(TFT_MAGENTA, TFT_BLACK);
  tft.setCursor(10, 50);
  tft.println("hello :)");
  tft.fillCircle(80, 100, 20, TFT_RED);
}

void loop() { delay(1000); }
