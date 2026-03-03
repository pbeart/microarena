#include "harness.h"
#include <stdio.h>

//int __attribute__ ((noinline)) sub(int a) {
//    return a+1;
//}

int main() {
    //asm ("mv sp, %0" : : "r" (0x69));
    //mmio_rw->a = 0x69;
    //int c = mmio_r->b;
    //char a[10] = "Hello eve";
    //for (int i=0; i<10; i++) {
    //    mmio_rw->stdout_buffer[i] = a[i];
    //};
    //mmio_rw->stdout_go = 0xff;
    //char a = mmio_r->b;
    log_string("Logging!");

    int timer = 300;

    double desired_angle = 0.75;
    
    while (1) {
        double desired_rate = 0.0;

        timer -= 1;

        if (timer == 0) {
            desired_angle = 2.25;
            log_string("2");
        }

        if (timer <= -300) {
            desired_angle = 0.75;
            log_string("0");
            timer = 300;
        }

        if (mmio_r->angle < desired_angle) {
            desired_rate = 1;
        } else {
            desired_rate = -1;
        }

        if (mmio_r->angle_rate > desired_rate) {
            mmio_rw->turn = TURN_LEFT;
            log_string("l");
        } else {
            mmio_rw->turn = TURN_RIGHT;
            log_string("r");
        };
        
    }
    /*int p = 1;
    int n = 1;
    for (int i=0; i<10; i++) {
        int t = n;
        n = n + p;
        p = t;

        mmio_rw->a = n;
        if (n % 2 == 0) {
            log_string("Even! ");
            log_int(n);
            log_string("\n");
        } else {
            log_string("Odd! ");
            log_int(n);
            log_string("\n");

        }
    }*/

    /*for (int i=0; i<10; i++) {
        log_string("Hello!\n");
        log_int(3);
    }*/
    
    //_write(0, a, 10);
    //printf("Hi!\n");
    //int x = sub(5);
}