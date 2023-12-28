

/* -----------------------------------------------------------------------------
 * Example .ino file for arduino, compiled with CmdMessenger.h and
 * CmdMessenger.cpp in the sketch directory. 
 *----------------------------------------------------------------------------*/


#include <Wire.h>
#include <Adafruit_GFX.h>
#include "Adafruit_LEDBackpack.h"
#include <CmdMessenger.h>

/* Define available CmdMessenger commands */
enum {
    clear_display,
    show_number,
};

/* Initialize CmdMessenger -- this should match PyCmdMessenger instance */
CmdMessenger c = CmdMessenger(Serial,',',';','/');
Adafruit_AlphaNum4 alpha4 = Adafruit_AlphaNum4();

void on_clear_display(void) {
  alpha4.clear();
  alpha4.writeDisplay();
}

void on_show_letter() {
  char n = c.readBinArg<char>();
  alpha4.writeDigitAscii(0, n);
  alpha4.writeDisplay();
}

void on_show_number() {
  int i = c.readBinArg<int>();
  showNumber(i);
}

void showNumber(int i) {
  alpha4.clear();
  int dig = i % 10;
  int ten = (i - dig) / 10;
  alpha4.writeDigitAscii(2, ten+48);
  alpha4.writeDigitAscii(3, dig+48);
  alpha4.writeDisplay();
}

/* Attach callbacks for CmdMessenger commands */
void attach_callbacks(void) {
//    c.attach(start_countdown, on_start_countdown);
    c.attach(clear_display, on_clear_display);
//    c.attach(show_letter, on_show_letter);
    c.attach(show_number, on_show_number);
//    c.attach(auto_countdown, on_auto_countdown);
}

void setup() {
    Serial.begin(115200);          
    // initialize the segment
    alpha4.begin(0x70);
  
    Serial.println("init");
    alpha4.writeDigitAscii(0, 'S');
    alpha4.writeDigitAscii(1, 'R');
    alpha4.writeDigitAscii(2, '2');
    alpha4.writeDisplay();
    attach_callbacks(); 
}

void loop() {
    c.feedinSerialData();
}
