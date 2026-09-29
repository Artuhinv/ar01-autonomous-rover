#ifndef AR01_SERVICE_H
#define AR01_SERVICE_H

#include <stdbool.h>
#include <stdint.h>

#include "ar01_core.h"

/* All callbacks are supplied by the board port. None may silently arm motors.
 * apply_pwm must be nonblocking and map zero to both physical PWM pins low;
 * transmit must be nonblocking and return false when its TX buffer is busy. */
typedef struct {
    void *context;
    ar01_inputs_t (*sample)(void *context);
    void (*apply_pwm)(void *context, int32_t left, int32_t right);
    bool (*transmit)(void *context, const uint8_t *bytes, uint16_t length);
    void (*watchdog_refresh)(void *context);
} ar01_port_t;

typedef struct {
    ar01_core_t core;
    ar01_port_t port;
    uint8_t receive[AR01_MAX_WIRE];
    uint16_t receive_length;
    uint16_t telemetry_sequence;
    uint32_t last_status_ms;
    uint32_t rejected_frames;
    uint32_t last_tick_ms;
    bool have_tick;
    bool dropping_frame;
} ar01_service_t;

/* Init commands both channels to zero before any input is read. */
bool ar01_service_init(ar01_service_t *service, const ar01_config_t *config,
                       const ar01_port_t *port);
/* Call from the main loop, not concurrently with service_tick. IRQ should only
 * queue bytes; a board-specific bounded ring buffer is still required. */
void ar01_service_receive_byte(ar01_service_t *service, uint8_t byte,
                               uint32_t now_ms);
/* Call every 10 ms from a timer-driven main-loop schedule. Hardware E-stop
 * must independently remove motor power between ticks. */
void ar01_service_tick(ar01_service_t *service, uint32_t now_ms);

#endif
