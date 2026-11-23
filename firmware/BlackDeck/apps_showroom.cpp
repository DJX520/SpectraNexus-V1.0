/*
 * BLACKDECK SHOWROOM / Cardputer-Adv, 240x135 ST7789V2.
 * These animations are for user interaction and presentation ONLY.
 * They do not spoof network/radio observations or transmit packets.
 * No bitmaps, extra external libraries, heap buffers or model edits.
 */
#include "BlackDeck.h"
#include <math.h>

#define LCD M5Cardputer.Display

static void banner(const char* title, const char* note) {
    LCD.fillScreen(gTheme.bg);
    LCD.fillRect(0, 0, 240, 18, gTheme.panel);
    LCD.drawFastHLine(0, 17, 240, gTheme.accent);
    LCD.setTextColor(gTheme.accent); LCD.setTextSize(1);
    LCD.setCursor(5, 5); LCD.print(title);
    LCD.setTextColor(gTheme.muted);
    LCD.setCursor(5, 118); LCD.print(note);
    LCD.drawFastHLine(4, 115, 232, gTheme.panel);
}

void uiBootShow() {
    LCD.fillScreen(gTheme.bg);
    LCD.setTextSize(2); LCD.setTextColor(gTheme.accent);
    LCD.setCursor(18, 24); LCD.print("BLACKDECK");
    LCD.setTextSize(1); LCD.setTextColor(gTheme.accent2);
    LCD.setCursor(19, 51); LCD.print("FULL AI / LABOS 5 / SHOWCASE");
    LCD.drawRect(18, 80, 204, 10, gTheme.muted);
    for (int i=0;i<=40;i++) {
        LCD.fillRect(20, 82, i*5, 6, gTheme.accent);
        LCD.fillRect(18, 99, 204, 11, gTheme.bg);
        LCD.setCursor(18, 101); LCD.setTextColor(gTheme.muted);
        LCD.printf("INIT  %02d%%  %s", i*100/40, i<30 ? "HW / LINK" : "READY");
        delay(17);
    }
    inputBeep(1280, 28);
    delay(110);
}

static void matrixRain() {
    const int columns = 30;
    int16_t drop[columns];
    for (int i=0;i<columns;i++) drop[i] = random(0, 12)*8;
    banner("MATRIX RAIN", "DEMO / key to return");
    uint32_t last=0;
    const char chars[] = "01ABCDEF{}+-*";
    while (true) {
        if (inputPoll().any) break;
        if (millis()-last<45) {delay(3);continue;}
        last=millis();
        for (int i=0;i<columns;i++) {
            int x=i*8;
            int y=drop[i];
            if (y >= 19 && y <= 105) {
                LCD.fillRect(x, y, 8, 8, gTheme.bg);
                LCD.setTextColor((i%5==0) ? gTheme.accent2 : gTheme.accent);
                LCD.setTextSize(1); LCD.setCursor(x,y);
                LCD.print(chars[random(0,sizeof(chars)-1)]);
                if (y>23) LCD.drawPixel(x+3,y-4,gTheme.panel);
            }
            drop[i]+=8;
            if (drop[i]>110) drop[i]=19-random(0,80);
        }
    }
}

static void radarTheater() {
    // Polar points are synthetic decorative visual elements.
    // Angular positions do NOT represent antenna direction or estimated location.
    const int cx=120,cy=68,r=46;
    uint32_t frame=0;
    while (true) {
        if (inputPoll().any) break;
        banner("NEON RADAR / VISUAL", "DEMO ONLY / no RF sampling");
        LCD.drawCircle(cx,cy,r,gTheme.accent);
        LCD.drawCircle(cx,cy,30,gTheme.muted);
        LCD.drawCircle(cx,cy,14,gTheme.panel);
        LCD.drawFastHLine(cx-r-6,cy,2*r+12,gTheme.panel);
        LCD.drawFastVLine(cx,cy-r-5,2*r+11,gTheme.panel);
        float angle = float(frame % 120)*6.2831853f/120.0f;
        int bx=cx+int(cosf(angle)*r);
        int by=cy+int(sinf(angle)*r);
        LCD.drawLine(cx,cy,bx,by,gTheme.accent2);
        for (int i=0;i<6;i++) {
            const float a=(i*59.0f+26.0f)*0.017453293f;
            const float rr=float(12+(i*13)%31);
            int x=cx+int(cosf(a)*rr), y=cy+int(sinf(a)*rr);
            LCD.fillCircle(x,y,(i+frame/14)%3==0?3:2,gTheme.ok);
        }
        LCD.setTextSize(1); LCD.setTextColor(gTheme.muted);
        LCD.setCursor(4,26);LCD.print("SWEEP");
        LCD.setCursor(5,36);LCD.printf("%03u",(unsigned)((frame*3)%360));
        LCD.setCursor(188,26);LCD.print("ARCADE");
        frame++;
        delay(65);
    }
}

static void systemPulse() {
    uint32_t history[53]={};
    uint8_t cursor=0;
    unsigned long last=0;
    while (true) {
        if (inputPoll().any) break;
        if (millis()-last<180){delay(4);continue;}
        last=millis();
        const uint32_t heap=ESP.getFreeHeap();
        const uint32_t minHeap=ESP.getMinFreeHeap();
        const int battery=constrain(M5Cardputer.Power.getBatteryLevel(),0,100);
        history[cursor]=heap;
        cursor=(cursor+1)%53;
        banner("SYSTEM PULSE / REAL", "REAL local metrics / key exits");
        LCD.setTextSize(2); LCD.setTextColor(gTheme.accent);
        LCD.setCursor(8,28);LCD.printf("%4u KB",(unsigned)(heap/1024));
        LCD.setTextSize(1);LCD.setTextColor(gTheme.muted);
        LCD.setCursor(155,31);LCD.print("FREE HEAP");
        LCD.setCursor(9,59);LCD.printf("LOW:%u KB",(unsigned)(minHeap/1024));
        LCD.setCursor(130,59);LCD.printf("BATT:%d%%",battery);
        LCD.fillRect(10,72,220,5,gTheme.panel);
        LCD.fillRect(10,72,220*battery/100,5,gTheme.ok);
        LCD.drawFastHLine(6,108,228,gTheme.muted);
        for(int i=1;i<53;i++){
            const uint32_t a=history[(cursor+i-1)%53];
            const uint32_t b=history[(cursor+i)%53];
            if(!a||!b)continue;
            // Visualized in a fixed 40KB rolling window around current heap.
            int ya=106-constrain(int((int64_t(a)-int64_t(heap)+20000)/1000),0,24);
            int yb=106-constrain(int((int64_t(b)-int64_t(heap)+20000)/1000),0,24);
            LCD.drawLine(10+(i-1)*4,ya,10+i*4,yb,gTheme.accent2);
        }
    }
}

static void signalCatcher() {
    const int targetX=207;
    int score=0, combo=0, misses=0;
    float dotX=12.0f, speed=2.7f;
    uint32_t start=millis();
    uint32_t last=0;
    banner("SIGNAL CATCHER", "ARCADE / ENTER=catch  `=exit");
    while(millis()-start<30000) {
        InputEvent e=inputPoll();
        if(e.esc||e.del)break;
        if(e.enter) {
            int delta=abs(int(dotX)-targetX);
            if(delta<19) {
                ++score; ++combo; inputBeep(850+combo*80,45);
                speed=constrain(speed+0.19f,2.7f,6.0f);dotX=12;
            } else {combo=0;misses++;inputBeep(350,35);}
        }
        if(millis()-last<35){delay(4);continue;}
        last=millis();
        dotX+=speed;
        if(dotX>233) {dotX=12;combo=0;misses++;}
        LCD.fillRect(0,18,240,95,gTheme.bg);
        LCD.setTextColor(gTheme.accent); LCD.setTextSize(2);
        LCD.setCursor(12,28);LCD.printf("SCORE %02d",score);
        LCD.setTextSize(1);LCD.setTextColor(gTheme.muted);
        LCD.setCursor(12,51);LCD.printf("COMBO %d  MISS %d",combo,misses);
        const uint32_t elapsed=millis()-start;
        const uint32_t remaining=elapsed<30000U?30000U-elapsed:0U;
        LCD.setCursor(168,51);LCD.printf("%02lus",(unsigned long)(remaining/1000));
        LCD.drawFastHLine(8,91,224,gTheme.panel);
        LCD.drawCircle(targetX,90,15,gTheme.accent2);
        LCD.drawCircle(targetX,90,18,gTheme.muted);
        LCD.fillCircle(int(dotX),90,6,gTheme.ok);
    }
    char result[42];
    snprintf(result,sizeof(result),"Score %d  /  Miss %d",score,misses);
    uiMessage("GAME OVER",result,2200);
}

void appShowroom() {
    static const char* labels[]={
        "Neon Radar (demo)",
        "Matrix Rain", 
        "System Pulse (real)",
        "Signal Catcher (game)",
        "Return"
    };
    int selected=0;
    for(;;) {
        int i=uiMenu("BLACKDECK / SHOWROOM",labels,5,selected,"rmpgb");
        if(i<0||i==4)return;
        selected=i;
        if(i==0)radarTheater();
        if(i==1)matrixRain();
        if(i==2)systemPulse();
        if(i==3)signalCatcher();
    }
}
