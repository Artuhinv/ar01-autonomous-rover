#ifndef AR01_CORE_H
#define AR01_CORE_H

#include <stdbool.h>
#include <stdint.h>

#include "ar01_link.h"

enum ar01_state { AR01_DISARMED = 0, AR01_ARMED = 1, AR01_FAULT = 2 };
enum ar01_fault {
    AR01_ESTOP_OPEN = 1u << 0,
    AR01_DRIVER_FAULT = 1u << 1,
    AR01_LEFT_JAM = 1u << 2,
    AR01_RIGHT_JAM = 1u << 3,
    AR01_BUS_UNDERVOLTAGE = 1u << 4,
    AR01_ENCODER_IMPLAUSIBLE = 1u << 5,
    AR01_COMMAND_TIMEOUT = 1u << 6,
    AR01_WATCHDOG_RESET = 1u << 7
};

/* All thresholds and PI gains require physical bench measurement. Zero disables ARM. */
typedef struct {
    uint16_t minimum_bus_mv;
    uint16_t current_trip_ma;
    uint16_t jam_current_ma;
    uint16_t jam_target_mrad_s;
    uint16_t jam_min_ticks_per_tick;
    uint16_t jam_ticks_to_fault;
    uint16_t no_motion_ticks_to_fault;
    uint16_t max_encoder_ticks_per_tick;
    uint16_t kp_q10;
    uint16_t ki_q10;
    int8_t left_encoder_sign;
    int8_t right_encoder_sign;
} ar01_config_t;

typedef struct {
    uint32_t left_counter;  /* TIM2, 32 bits */
    uint16_t right_counter; /* TIM4, 16 bits */
    uint16_t left_current_ma;  /* 0xFFFF when not in drive window */
    uint16_t right_current_ma; /* 0xFFFF when not in drive window */
    uint16_t bus_mv;
    bool estop_closed;
    bool left_diag_ok;
    bool right_diag_ok;
} ar01_inputs_t;

typedef struct {
    ar01_config_t config;
    enum ar01_state state;
    uint16_t faults;
    uint16_t accepted_sequence;
    bool have_sequence;
    bool have_sample;
    bool inputs_healthy;
    uint32_t last_command_ms;
    uint32_t last_left_counter;
    uint16_t last_right_counter;
    int64_t left_ticks;
    int64_t right_ticks;
    int32_t left_speed_mrad_s;
    int32_t right_speed_mrad_s;
    int32_t left_target_mrad_s;
    int32_t right_target_mrad_s;
    int32_t left_pwm_permille;
    int32_t right_pwm_permille;
    int32_t left_integral;
    int32_t right_integral;
    uint16_t left_jam_ticks;
    uint16_t right_jam_ticks;
    uint16_t left_current_ma;
    uint16_t right_current_ma;
    uint16_t bus_mv;
} ar01_core_t;

void ar01_core_init(ar01_core_t *core, const ar01_config_t *config);
bool ar01_config_complete(const ar01_config_t *config);
/* Call at a timer-driven 10 ms period, not from a best-effort main loop. */
void ar01_core_tick(ar01_core_t *core, const ar01_inputs_t *inputs,
                    uint32_t now_ms);
/* Returns true only for an accepted, sequence-valid command. */
bool ar01_core_command(ar01_core_t *core, const ar01_frame_t *frame,
                       uint32_t now_ms);
int ar01_core_status(const ar01_core_t *core, uint32_t now_ms,
                     uint16_t telemetry_sequence, ar01_frame_t *frame);

#endif
