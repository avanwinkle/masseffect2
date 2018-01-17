
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1351.h>
#include <SPI.h>

/* -----------------------------------------------------------------------------
 * Example .ino file for arduino, compiled with CmdMessenger.h and
 * CmdMessenger.cpp in the sketch directory. 
 *----------------------------------------------------------------------------*/

#include <CmdMessenger.h>


/* Define available CmdMessenger commands */
enum {
    draw_text,
    error
};

/* Initialize OLED TFT */
// You can use any (4 or) 5 pins 
#define sclk 2
#define mosi 3
#define dc   4
#define cs   5
#define rst  6

// Color definitions
#define BLACK           0x0000
#define BLUE            0x001F
#define RED             0xF800
#define GREEN           0x07E0
#define CYAN            0x07FF
#define MAGENTA         0xF81F
#define YELLOW          0xFFE0  
#define WHITE           0xFFFF


// Option 1: use any pins but a little slower
Adafruit_SSD1351 tft = Adafruit_SSD1351(cs, dc, mosi, sclk, rst);  

/* Initialize CmdMessenger -- this should match PyCmdMessenger instance */
const int32_t BAUD_RATE = 115200;
CmdMessenger c = CmdMessenger(Serial,',',';','/');

/* Create callback functions to deal with incoming messages */

/* callback */
void on_unknown_command(void){
    c.sendCmd(error,"Command without callback.");
}

/* callback */
void on_draw_text(void){
  tft.fillRect(0, 0, 128, 128, BLACK);
  char *text = c.readStringArg();
  tft.setCursor(0,0);
  tft.setTextColor(WHITE);
  tft.setTextSize(2);
  tft.print(text);
}

/* Attach callbacks for CmdMessenger commands */
void attach_callbacks(void) { 
    c.attach(on_unknown_command);
    c.attach(draw_text, on_draw_text);
}

void setup() {
    Serial.begin(BAUD_RATE);
    attach_callbacks();    
    tft.begin();
    tft.fillRect(0, 0, 128, 128, BLACK);
}

void loop() {
    c.feedinSerialData();
}
