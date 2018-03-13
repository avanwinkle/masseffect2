#include <Adafruit_GFX.h>
#include <Adafruit_SSD1351.h>
#include <SD.h>
#include <SPI.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_LEDBackpack.h>

#include <CmdMessenger.h>  // CmdMessenger

// If we are using the hardware SPI interface, these are the pins (for future ref)
#define sclk 52  // ORG -> CL (2)
#define mosi 51  // PRP -> SI (1)
#define miso 50  // GRY -> SO (7)
#define SD_CS 53 // WHT -> SC (6)
#define cs   5   // GRN -> OC (5)
#define rst  6   // BRN -> R  (4)
#define dc   3   // BLU -> DC (3)

// Color definitions
#define BLACK           0x0000
#define BLUE            0x001F

enum {
  draw_bmp,
  clear_ledsegment,
  show_ledsegment_letters,
  show_ledsegment_number,
};

// Attach a new CmdMessenger object to the default Serial port
CmdMessenger cmdMessenger = CmdMessenger(Serial);

// the file itself
File bmpFile;

// to draw images from the SD card, we will share the hardware SPI interface
Adafruit_SSD1351 tft = Adafruit_SSD1351(cs, dc, rst);

// Store a connection to our alphanumeric LED segment display
Adafruit_AlphaNum4 alpha4 = Adafruit_AlphaNum4();

// information we extract about the bitmap file
int bmpWidth, bmpHeight;
uint8_t bmpDepth, bmpImageoffset;

void attachCallbacks(void) {
  cmdMessenger.attach(draw_bmp, on_draw_bmp);
  cmdMessenger.attach(clear_ledsegment, on_clear_ledsegment);
  cmdMessenger.attach(show_ledsegment_letters, on_show_ledsegment_letters);
  cmdMessenger.attach(show_ledsegment_number, on_show_ledsegment_number);
}

void on_draw_bmp(void) {
  Serial.println("Drawing bmp!");
  char * filename = cmdMessenger.readStringArg();
  bmpDraw(filename, 0, 0);
}

void on_clear_ledsegment(void) {
  alpha4.clear();
  alpha4.writeDisplay();
}

void on_show_ledsegment_letters() {
  // char n = cmdMessenger.readBinArg<char>();
  char * letters = cmdMessenger.readStringArg();
  showLetters(letters);
}

void showLetters(char *letters) {
  int lettersLen = strlen(letters);
  for (int i=0; i<lettersLen; i++) {
    alpha4.writeDigitAscii(i, letters[i]);
  }
  alpha4.writeDisplay();
}

void on_show_ledsegment_number() {
  int i = cmdMessenger.readBinArg<int>();
  showNumber(i);
}

// Parse an integer and assign the digits to correct LED segment blocks
void showNumber(int i) {
  alpha4.clear();
  int dig = i % 10;
  int ten = (i - dig) / 10 % 10;
  int hun = (i - dig - (10 * ten)) / 100 % 10;
  int tho = (i - dig - (10 * ten) - (100 * hun)) / 1000 % 10;
  alpha4.writeDigitAscii(3, dig+48);
  alpha4.writeDigitAscii(2, ten+48);
  if (hun > 0 || tho > 0) {
    alpha4.writeDigitAscii(1, hun+48);
  }
  if (tho > 0) {
    alpha4.writeDigitAscii(0, tho+48);
  }
  alpha4.writeDisplay();
}


void setup(void) {
  Serial.begin(115200);

  Serial.println("init");
  setup_tft();
  setup_ledsegment();

  attachCallbacks();
}

void setup_tft() {
  pinMode(cs, OUTPUT);
  digitalWrite(cs, HIGH);
  pinMode(      10          , OUTPUT);
  digitalWrite( 10          , HIGH  );

  // initialize the OLED
  tft.begin();


  tft.fillScreen(BLUE);
  delay(500);
  Serial.print("Initializing SD card...");

  if (!SD.begin(SD_CS)) {
    Serial.println("failed!");
  } else {
    Serial.println("SD OK!");
  }

  bmpDraw("n7.bmp", 0, 0);
}

void setup_ledsegment() {
  // initialize the segment
    alpha4.begin(0x70);

    Serial.println("init ledsegment");
    showLetters("SR2");
    // alpha4.writeDigitAscii(0, 'S');
    // alpha4.writeDigitAscii(1, 'R');
    // alpha4.writeDigitAscii(2, '2');
    // alpha4.writeDisplay();
}

void loop() {
  cmdMessenger.feedinSerialData();
}

// This function opens a Windows Bitmap (BMP) file and
// displays it at the given coordinates.  It's sped up
// by reading many pixels worth of data at a time
// (rather than pixel by pixel).  Increasing the buffer
// size takes more of the Arduino's precious RAM but
// makes loading a little faster.  20 pixels seems a
// good balance.

#define BUFFPIXEL 64

void bmpDraw(char *filename, uint8_t x, uint8_t y) {

  File     bmpFile;
  int      bmpWidth, bmpHeight;   // W+H in pixels
  uint8_t  bmpDepth;              // Bit depth (currently must be 24)
  uint32_t bmpImageoffset;        // Start of image data in file
  uint32_t rowSize;               // Not always = bmpWidth; may have padding
  uint8_t  sdbuffer[3*BUFFPIXEL]; // pixel buffer (R+G+B per pixel)
  uint8_t  buffidx = sizeof(sdbuffer); // Current position in sdbuffer
  boolean  goodBmp = false;       // Set to true on valid header parse
  boolean  flip    = true;        // BMP is stored bottom-to-top
  int      w, h, row, col;
  uint8_t  r, g, b;
  uint32_t pos = 0, startTime = millis();

  if((x >= tft.width()) || (y >= tft.height())) return;

  Serial.println();
  Serial.print("Loading image '");
  Serial.print(filename);
  Serial.println('\'');

  // Open requested file on SD card
  if ((bmpFile = SD.open(filename)) == NULL) {
    Serial.print("File not found");
    return;
  }

  // Parse BMP header
  if(read16(bmpFile) == 0x4D42) { // BMP signature
    Serial.print("File size: "); Serial.println(read32(bmpFile));
    (void)read32(bmpFile); // Read & ignore creator bytes
    bmpImageoffset = read32(bmpFile); // Start of image data
    Serial.print("Image Offset: "); Serial.println(bmpImageoffset, DEC);
    // Read DIB header
    Serial.print("Header size: "); Serial.println(read32(bmpFile));
    bmpWidth  = read32(bmpFile);
    bmpHeight = read32(bmpFile);
    if(read16(bmpFile) == 1) { // # planes -- must be '1'
      bmpDepth = read16(bmpFile); // bits per pixel
      Serial.print("Bit Depth: "); Serial.println(bmpDepth);
      if((bmpDepth == 24) && (read32(bmpFile) == 0)) { // 0 = uncompressed

        goodBmp = true; // Supported BMP format -- proceed!
        Serial.print("Image size: ");
        Serial.print(bmpWidth);
        Serial.print('x');
        Serial.println(bmpHeight);

        // BMP rows are padded (if needed) to 4-byte boundary
        rowSize = (bmpWidth * 3 + 3) & ~3;

        // If bmpHeight is negative, image is in top-down order.
        // This is not canon but has been observed in the wild.
        if(bmpHeight < 0) {
          bmpHeight = -bmpHeight;
          flip      = false;
        }

        // Crop area to be loaded
        w = bmpWidth;
        h = bmpHeight;
        if((x+w-1) >= tft.width())  w = tft.width()  - x;
        if((y+h-1) >= tft.height()) h = tft.height() - y;

        for (row=0; row<h; row++) { // For each scanline...
          tft.goTo(x, y+row);

          // Seek to start of scan line.  It might seem labor-
          // intensive to be doing this on every line, but this
          // method covers a lot of gritty details like cropping
          // and scanline padding.  Also, the seek only takes
          // place if the file position actually needs to change
          // (avoids a lot of cluster math in SD library).
          if(flip) // Bitmap is stored bottom-to-top order (normal BMP)
            pos = bmpImageoffset + (bmpHeight - 1 - row) * rowSize;
          else     // Bitmap is stored top-to-bottom
            pos = bmpImageoffset + row * rowSize;
          if(bmpFile.position() != pos) { // Need seek?
            bmpFile.seek(pos);
            buffidx = sizeof(sdbuffer); // Force buffer reload
          }

          // optimize by setting pins now
          for (col=0; col<w; col++) { // For each pixel...
            // Time to read more pixel data?
            if (buffidx >= sizeof(sdbuffer)) { // Indeed
              bmpFile.read(sdbuffer, sizeof(sdbuffer));
              buffidx = 0; // Set index to beginning
            }

            // Convert pixel from BMP to TFT format, push to display
            b = sdbuffer[buffidx++];
            g = sdbuffer[buffidx++];
            r = sdbuffer[buffidx++];

            tft.drawPixel(x+col, y+row, tft.Color565(r,g,b));
            // optimized!
            //tft.pushColor(tft.Color565(r,g,b));
          } // end pixel
        } // end scanline
        Serial.print("Loaded in ");
        Serial.print(millis() - startTime);
        Serial.println(" ms");
      } // end goodBmp
    }
  }

  bmpFile.close();
  if(!goodBmp) Serial.println("BMP format not recognized.");
}

// These read 16- and 32-bit types from the SD card file.
// BMP data is stored little-endian, Arduino is little-endian too.
// May need to reverse subscript order if porting elsewhere.

uint16_t read16(File f) {
  uint16_t result;
  ((uint8_t *)&result)[0] = f.read(); // LSB
  ((uint8_t *)&result)[1] = f.read(); // MSB
  return result;
}

uint32_t read32(File f) {
  uint32_t result;
  ((uint8_t *)&result)[0] = f.read(); // LSB
  ((uint8_t *)&result)[1] = f.read();
  ((uint8_t *)&result)[2] = f.read();
  ((uint8_t *)&result)[3] = f.read(); // MSB
  return result;
}
