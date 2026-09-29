#include "ar01_core.h"

#include <limits.h>
#define AR01_TIMEOUT_MS 200u
#define AR01_MAX_TARGET_MRAD_S 20000

static int32_t clamp_pwm(int64_t value)
{
    if (value > 1000) return 1000;
    if (value < -1000) return -1000;
    return (int32_t)value;
}

static int32_t abs_i32(int32_t value)
{
    return value == INT32_MIN ? INT32_MAX : (value < 0 ? -value : value);
}

static int32_t signed_from_u32(uint32_t value)
{
    return value <= INT32_MAX ? (int32_t)value :
           (int32_t)((int64_t)value - 4294967296LL);
}

static void stop_output(ar01_core_t *core)
{
    core->left_target_mrad_s = 0;
    core->right_target_mrad_s = 0;
    core->left_pwm_permille = 0;
    core->right_pwm_permille = 0;
    core->left_integral = 0;
    core->right_integral = 0;
    core->left_jam_ticks = 0;
    core->right_jam_ticks = 0;
}

bool ar01_config_complete(const ar01_config_t *c)
{
    return c && c->minimum_bus_mv > 0 && c->current_trip_ma > 0 &&
           c->jam_current_ma > 0 && c->jam_current_ma < c->current_trip_ma &&
           c->jam_target_mrad_s > 0 && c->jam_min_ticks_per_tick > 0 &&
           c->jam_ticks_to_fault > 0 && c->no_motion_ticks_to_fault > 0 &&
           c->max_encoder_ticks_per_tick > 0 &&
           c->kp_q10 > 0 &&
           (c->left_encoder_sign == 1 || c->left_encoder_sign == -1) &&
           (c->right_encoder_sign == 1 || c->right_encoder_sign == -1);
}

void ar01_core_init(ar01_core_t *core, const ar01_config_t *config)
{
    *core = (ar01_core_t){0};
    if (config) core->config = *config;
    core->state = AR01_DISARMED;
    core->left_current_ma = 0xFFFFu;
    core->right_current_ma = 0xFFFFu;
}

static int32_t encoder_delta32(uint32_t now, uint32_t previous)
{
    uint32_t d = now - previous;
    return d <= INT32_MAX ? (int32_t)d : (int32_t)((int64_t)d - 4294967296LL);
}

static int32_t encoder_delta16(uint16_t now, uint16_t previous)
{
    uint16_t d = (uint16_t)(now - previous);
    return d < 32768u ? (int32_t)d : (int32_t)d - 65536;
}

static int32_t speed_from_delta(int32_t delta)
{
    /* 2*pi rad/rev, 4480 x4 counts/rev, 100 Hz, mrad/s. */
    int64_t value = (int64_t)delta * 628319LL / 4480LL;
    if (value > INT32_MAX) return INT32_MAX;
    if (value < INT32_MIN) return INT32_MIN;
    return (int32_t)value;
}

static int32_t pi_step(int32_t target, int32_t observed, int32_t *integral,
                       const ar01_config_t *config)
{
    if (target == 0) {
        *integral = 0;
        return 0;
    }
    int64_t error = (int64_t)target - observed;
    int64_t proportional = error * config->kp_q10 / 1024;
    int32_t candidate = clamp_pwm((int64_t)*integral +
                                   error * config->ki_q10 / 1024);
    int64_t unbounded = proportional + candidate;
    if (!((unbounded > 1000 && error > 0) ||
          (unbounded < -1000 && error < 0))) *integral = candidate;
    return clamp_pwm(proportional + *integral);
}

static void monitor_jam(uint16_t *counter, int32_t target, int32_t delta,
                        uint16_t current_ma, uint16_t fault_bit,
                        ar01_core_t *core)
{
    const ar01_config_t *c = &core->config;
    if (abs_i32(target) >= c->jam_target_mrad_s &&
        abs_i32(delta) < c->jam_min_ticks_per_tick) {
        uint16_t threshold = current_ma != 0xFFFFu &&
                             current_ma >= c->jam_current_ma ?
                             c->jam_ticks_to_fault :
                             c->no_motion_ticks_to_fault;
        if (*counter < threshold) ++*counter;
        if (*counter >= threshold) core->faults |= fault_bit;
    } else {
        *counter = 0;
    }
}

void ar01_core_tick(ar01_core_t *core, const ar01_inputs_t *inputs,
                    uint32_t now_ms)
{
    if (!core || !inputs) return;
    int32_t left_delta = 0;
    int32_t right_delta = 0;
    bool encoder_sample_plausible = true;
    if (core->have_sample) {
        int32_t raw_left = encoder_delta32(inputs->left_counter,
                                           core->last_left_counter);
        int32_t raw_right = encoder_delta16(inputs->right_counter,
                                            core->last_right_counter);
        if (abs_i32(raw_left) > core->config.max_encoder_ticks_per_tick ||
            abs_i32(raw_right) > core->config.max_encoder_ticks_per_tick) {
            encoder_sample_plausible = false;
            core->faults |= AR01_ENCODER_IMPLAUSIBLE;
        } else {
            left_delta = raw_left * core->config.left_encoder_sign;
            right_delta = raw_right * core->config.right_encoder_sign;
            core->left_ticks += left_delta;
            core->right_ticks += right_delta;
            core->left_speed_mrad_s = speed_from_delta(left_delta);
            core->right_speed_mrad_s = speed_from_delta(right_delta);
        }
    }
    core->last_left_counter = inputs->left_counter;
    core->last_right_counter = inputs->right_counter;
    core->have_sample = true;
    core->left_current_ma = inputs->left_current_ma;
    core->right_current_ma = inputs->right_current_ma;
    core->bus_mv = inputs->bus_mv;
    core->inputs_healthy = inputs->estop_closed && inputs->left_diag_ok &&
                           inputs->right_diag_ok &&
                           inputs->bus_mv >= core->config.minimum_bus_mv &&
                           (inputs->left_current_ma == 0xFFFFu ||
                            inputs->left_current_ma < core->config.current_trip_ma) &&
                           (inputs->right_current_ma == 0xFFFFu ||
                            inputs->right_current_ma < core->config.current_trip_ma) &&
                           encoder_sample_plausible;
    if (!inputs->estop_closed) core->faults |= AR01_ESTOP_OPEN;
    if (!inputs->left_diag_ok || !inputs->right_diag_ok)
        core->faults |= AR01_DRIVER_FAULT;
    if (inputs->bus_mv < core->config.minimum_bus_mv)
        core->faults |= AR01_BUS_UNDERVOLTAGE;

    if (core->state == AR01_ARMED) {
        if ((uint32_t)(now_ms - core->last_command_ms) >= AR01_TIMEOUT_MS)
            core->faults |= AR01_COMMAND_TIMEOUT;
        if (inputs->left_current_ma != 0xFFFFu &&
            inputs->left_current_ma >= core->config.current_trip_ma)
            core->faults |= AR01_LEFT_JAM;
        if (inputs->right_current_ma != 0xFFFFu &&
            inputs->right_current_ma >= core->config.current_trip_ma)
            core->faults |= AR01_RIGHT_JAM;
        if (core->left_pwm_permille != 0)
            monitor_jam(&core->left_jam_ticks, core->left_target_mrad_s,
                        left_delta, inputs->left_current_ma, AR01_LEFT_JAM, core);
        else core->left_jam_ticks = 0;
        if (core->right_pwm_permille != 0)
            monitor_jam(&core->right_jam_ticks, core->right_target_mrad_s,
                        right_delta, inputs->right_current_ma, AR01_RIGHT_JAM, core);
        else core->right_jam_ticks = 0;
    }

    if (core->faults) {
        core->state = AR01_FAULT;
        stop_output(core);
    } else if (core->state == AR01_ARMED) {
        core->left_pwm_permille = pi_step(core->left_target_mrad_s,
                                          core->left_speed_mrad_s,
                                          &core->left_integral, &core->config);
        core->right_pwm_permille = pi_step(core->right_target_mrad_s,
                                           core->right_speed_mrad_s,
                                           &core->right_integral, &core->config);
    } else {
        stop_output(core);
    }
}

bool ar01_core_command(ar01_core_t *core, const ar01_frame_t *frame,
                       uint32_t now_ms)
{
    if (!core || !frame) return false;
    if (frame->type == AR01_DISARM && frame->length == 0) {
        stop_output(core);
        if (!core->faults) core->state = AR01_DISARMED;
        core->have_sequence = false;
        return true;
    }
    if (core->have_sequence &&
        (int16_t)(uint16_t)(frame->sequence - core->accepted_sequence) <= 0)
        return false;

    if (frame->type == AR01_ARM && frame->length == 0 &&
        core->state == AR01_DISARMED && !core->faults &&
        core->have_sample && core->inputs_healthy &&
        ar01_config_complete(&core->config)) {
        core->state = AR01_ARMED;
        core->last_command_ms = now_ms;
    } else if (frame->type == AR01_SET_WHEEL_SPEED && frame->length == 8 &&
               core->state == AR01_ARMED) {
        int32_t left = signed_from_u32(ar01_get_u32(frame->payload));
        int32_t right = signed_from_u32(ar01_get_u32(frame->payload + 4));
        if (abs_i32(left) > AR01_MAX_TARGET_MRAD_S ||
            abs_i32(right) > AR01_MAX_TARGET_MRAD_S) return false;
        core->left_target_mrad_s = left;
        core->right_target_mrad_s = right;
        core->last_command_ms = now_ms;
    } else if (frame->type == AR01_CLEAR_FAULT && frame->length == 0 &&
               core->state == AR01_FAULT && core->inputs_healthy &&
               core->left_target_mrad_s == 0 &&
               core->right_target_mrad_s == 0) {
        core->faults = 0;
        core->state = AR01_DISARMED;
    } else {
        return false;
    }
    core->accepted_sequence = frame->sequence;
    core->have_sequence = true;
    return true;
}

int ar01_core_status(const ar01_core_t *core, uint32_t now_ms,
                     uint16_t telemetry_sequence, ar01_frame_t *frame)
{
    if (!core || !frame) return -1;
    frame->type = AR01_STATUS;
    frame->sequence = telemetry_sequence;
    frame->length = 31;
    ar01_put_u32(frame->payload, now_ms);
    ar01_put_u64(frame->payload + 4, (uint64_t)core->left_ticks);
    ar01_put_u64(frame->payload + 12, (uint64_t)core->right_ticks);
    ar01_put_u16(frame->payload + 20, core->left_current_ma);
    ar01_put_u16(frame->payload + 22, core->right_current_ma);
    ar01_put_u16(frame->payload + 24, core->bus_mv);
    ar01_put_u16(frame->payload + 26, core->faults);
    frame->payload[28] = (uint8_t)core->state;
    ar01_put_u16(frame->payload + 29, core->accepted_sequence);
    return 0;
}
