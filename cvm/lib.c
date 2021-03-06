#include "cvm.h"

Timer timer;
Timer utimer;
Ticker ticker;
DigitalOut led1(LED1);
DigitalOut led2(LED2);
DigitalOut led3(LED3);
DigitalOut led4(LED4);
PwmOut fader(p21);
SPI spi(p11, p12, p13);
DigitalOut pin20(p20);

volatile ULONG ticks = 0;
volatile BOOL avail;

/***********************
* library
*/

void handleTick(){
    ticks++;
    avail = pc.readable();
 }

void mwait(ULONG c){
    ULONG endtime = ticks + c;
    while((ticks!=endtime)&&(!avail)){}
}

void primWait(ULONG c){mwait(c*100);}
void uwait(ULONG c){wait_us(c);}

ULONG read_timer(){return timer.read_ms();}
void reset_timer(){timer.reset();}
ULONG read_utimer(){return utimer.read_us();}
void reset_utimer(){utimer.reset();}

void *lmalloc(ULONG n){return malloc(n);}
void lfree(void *n){free(n);}

void print(SLONG c){pc.printf("%d\n", c);}
void prh(SLONG c){pc.printf("%08x\n", c);}
void prhb(SLONG c){pc.printf("%02x\n", c);}
void prs(UBYTE* s){pc.printf("%s", s);}
void prn(char* s,ULONG n){pc.printf(s, n);}

void prf(char *s, SLONG n) {
    for (; *s; s++) {
        if ('%' == *s) {
            s++;
            switch (*s) {
                case 'b':
                    pc.printf("%02x", n);
                break;

                case 'w':
                    pc.printf("%08x", n);
                break;

                case 'd':
                    pc.printf("%d", n);
                break;

                case 0:
                    return;

                default:
                    pc.putc(*s);
                break;
            }
        } else
            pc.putc(*s);
    }
}

void led1on(){led1=1;}
void led1off(){led1=0;}
void led2on(){led2=1;}
void led2off(){led2=0;}
void led3on(){led3=1;}
void led3off(){led3=0;}
void led4on(){led4=1;}
void led4off(){led4=0;}

void alloff(){ led1off();  led2off();  led3off();  led4off();}

ULONG primTime(){
    time_t seconds = time(NULL);
    return (ULONG)localtime(&seconds);
}

void settime(time_t t){set_time(t);}

void spiWrite(UBYTE n){spi.write(n);}
ULONG primTicks(){return ticks;}
void pin20on(){pin20=1;}
void pin20off(){pin20=0;}

void *fcns[] = {
    (void*) 0, (void*) read_utimer,  (void*) 0, (void*) reset_utimer,
    (void*) 1, (void*) primWait, (void*) 1, (void*) mwait, (void*) 1, (void*) uwait,
    (void*) 0, (void*) primTime, (void*) 1, (void*) settime,
    (void*) 1, (void*) lmalloc,  (void*) 0, (void*) lfree,  
    (void*) 1, (void*) print,  (void*) 1, (void*) prh,  
    (void*) 1, (void*) prs,  (void*) 2, (void*) prn,  (void*) 2, (void*) prf,
    (void*) 0, (void*) led1on, (void*) 0, (void*) led1off,
    (void*) 0, (void*) led2on, (void*) 0, (void*) led2off,
    (void*) 0, (void*) led3on, (void*) 0, (void*) led3off,
    (void*) 0, (void*) led4on, (void*) 0, (void*) led4off,
    (void*) 0, (void*) alloff,
    (void*) 1, (void*) spiWrite, (void*) 0, (void*) primTicks,
    (void*) 0, (void*) pin20on, (void*) 0, (void*) pin20off,
    (void*) 0, (void*) read_timer,  (void*) 0, (void*) reset_timer,
    (void*) 1, (void*) prhb,
};

void lib_init(){
    timer.start();
    utimer.start();
    ticker.attach_us(handleTick, 1000);
    fader.period_ms(10);
    fader.pulsewidth_ms(5);
    spi.format(8,0);
    spi.frequency(250000);
    pin20 = 1;
}
