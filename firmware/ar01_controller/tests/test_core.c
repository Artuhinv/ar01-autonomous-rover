#include "ar01_core.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static ar01_config_t bench_test_config(void)
{
    /* Synthetic test fixtures, explicitly NOT motor settings. */
    ar01_config_t c = {0};
    c.minimum_bus_mv = 6000;
    c.current_trip_ma = 4000;
    c.jam_current_ma = 1000;
    c.jam_target_mrad_s = 1000;
    c.jam_min_ticks_per_tick = 2;
    c.jam_ticks_to_fault = 3;
    c.no_motion_ticks_to_fault = 5;
    c.max_encoder_ticks_per_tick = 500;
    c.kp_q10 = 64;
    c.ki_q10 = 1;
    c.left_encoder_sign = 1;
    c.right_encoder_sign = 1;
    return c;
}

static ar01_inputs_t healthy_inputs(void)
{
    ar01_inputs_t i = {0};
    i.left_current_ma = 0xFFFFu;
    i.right_current_ma = 0xFFFFu;
    i.bus_mv = 12000;
    i.estop_closed = true;
    i.left_diag_ok = true;
    i.right_diag_ok = true;
    return i;
}

static ar01_frame_t command(uint8_t type, uint16_t sequence)
{
    ar01_frame_t frame = {0};
    frame.type = type;
    frame.sequence = sequence;
    return frame;
}

static void test_protocol(void)
{
    const uint8_t text[] = "123456789";
    assert(ar01_crc16(text, 9) == 0x29B1u);
    ar01_frame_t frame = command(AR01_SET_WHEEL_SPEED, 65535);
    frame.length = 8;
    ar01_put_u32(frame.payload, (uint32_t)-15000);
    ar01_put_u32(frame.payload + 4, 15000);
    uint8_t wire[AR01_MAX_WIRE];
    size_t size = 0;
    assert(ar01_encode(&frame, wire, sizeof(wire), &size) == 0);
    const uint8_t python_vector[] = {
        0x04, 0xa1, 0x01, 0x01, 0x0a, 0xff, 0xff, 0x08,
        0x68, 0xc5, 0xff, 0xff, 0x98, 0x3a, 0x01, 0x03,
        0x33, 0x39, 0x00
    };
    assert(size == sizeof(python_vector));
    assert(memcmp(wire, python_vector, size) == 0);
    ar01_frame_t parsed = {0};
    assert(ar01_decode(wire, size, &parsed) == 0);
    assert(parsed.type == frame.type && parsed.sequence == frame.sequence);
    assert(memcmp(parsed.payload, frame.payload, 8) == 0);
    wire[4] ^= 1;
    assert(ar01_decode(wire, size, &parsed) != 0);
    assert(ar01_decode(python_vector, size - 1, &parsed) != 0);
}

static void test_timeout_and_rearm(void)
{
    ar01_config_t config = bench_test_config();
    ar01_core_t core;
    ar01_core_init(&core, 0);
    ar01_inputs_t inputs = healthy_inputs();
    ar01_core_tick(&core, &inputs, 0);
    ar01_frame_t arm = command(AR01_ARM, 1);
    assert(!ar01_core_command(&core, &arm, 0));
    ar01_core_init(&core, &config);
    ar01_core_tick(&core, &inputs, 0);
    assert(ar01_core_command(&core, &arm, 0));
    assert(core.state == AR01_ARMED && core.left_pwm_permille == 0);
    ar01_frame_t speed = command(AR01_SET_WHEEL_SPEED, 2);
    speed.length = 8;
    ar01_put_u32(speed.payload, 3000);
    ar01_put_u32(speed.payload + 4, 3000);
    assert(ar01_core_command(&core, &speed, 10));
    assert(!ar01_core_command(&core, &speed, 10));
    ar01_core_tick(&core, &inputs, 20);
    assert(core.left_pwm_permille > 0 && core.right_pwm_permille > 0);
    ar01_core_tick(&core, &inputs, 210);
    assert(core.state == AR01_FAULT);
    assert(core.faults & AR01_COMMAND_TIMEOUT);
    assert(core.left_pwm_permille == 0 && core.right_pwm_permille == 0);
    ar01_frame_t clear = command(AR01_CLEAR_FAULT, 3);
    assert(ar01_core_command(&core, &clear, 212));
    assert(core.state == AR01_DISARMED);
}

static void test_estop_jam_and_wrap(void)
{
    ar01_config_t config = bench_test_config();
    ar01_core_t core;
    ar01_core_init(&core, &config);
    ar01_inputs_t inputs = healthy_inputs();
    inputs.left_counter = UINT32_MAX - 1u;
    inputs.right_counter = UINT16_MAX - 1u;
    ar01_core_tick(&core, &inputs, 0);
    inputs.left_counter = 1;
    inputs.right_counter = 1;
    ar01_core_tick(&core, &inputs, 10);
    assert(core.left_ticks == 3 && core.right_ticks == 3);
    inputs.estop_closed = false;
    ar01_core_tick(&core, &inputs, 20);
    assert(core.state == AR01_FAULT && (core.faults & AR01_ESTOP_OPEN));
    ar01_frame_t clear = command(AR01_CLEAR_FAULT, 1);
    assert(!ar01_core_command(&core, &clear, 20));
    inputs.estop_closed = true;
    ar01_core_tick(&core, &inputs, 30);
    assert(ar01_core_command(&core, &clear, 30));
    ar01_frame_t arm = command(AR01_ARM, 2);
    assert(ar01_core_command(&core, &arm, 30));
    ar01_frame_t speed = command(AR01_SET_WHEEL_SPEED, 3);
    speed.length = 8;
    ar01_put_u32(speed.payload, 3000);
    ar01_put_u32(speed.payload + 4, 0);
    assert(ar01_core_command(&core, &speed, 30));
    inputs.left_current_ma = 1200;
    for (uint32_t time = 40; time <= 70; time += 10)
        ar01_core_tick(&core, &inputs, time);
    assert(core.state == AR01_FAULT && (core.faults & AR01_LEFT_JAM));
    ar01_frame_t status;
    assert(ar01_core_status(&core, 70, 9, &status) == 0);
    assert(status.length == 31 && status.payload[28] == AR01_FAULT);
    uint8_t wire[AR01_MAX_WIRE];
    size_t length = 0;
    assert(ar01_encode(&status, wire, sizeof(wire), &length) == 0);
    ar01_frame_t parsed;
    assert(ar01_decode(wire, length, &parsed) == 0);
    assert(memcmp(parsed.payload, status.payload, 31) == 0);
}

static void test_sequence_rollover_and_overcurrent(void)
{
    ar01_config_t config = bench_test_config();
    ar01_core_t core;
    ar01_core_init(&core, &config);
    ar01_inputs_t inputs = healthy_inputs();
    ar01_core_tick(&core, &inputs, 0);
    ar01_frame_t arm = command(AR01_ARM, 65535);
    assert(ar01_core_command(&core, &arm, 0));
    ar01_frame_t speed = command(AR01_SET_WHEEL_SPEED, 0);
    speed.length = 8;
    ar01_put_u32(speed.payload, (uint32_t)-3000);
    ar01_put_u32(speed.payload + 4, 3000);
    assert(ar01_core_command(&core, &speed, 10));
    assert(core.left_target_mrad_s == -3000);
    assert(!ar01_core_command(&core, &arm, 11));
    ar01_core_tick(&core, &inputs, 20);
    assert(core.left_pwm_permille < 0 && core.right_pwm_permille > 0);
    inputs.right_current_ma = config.current_trip_ma;
    ar01_core_tick(&core, &inputs, 30);
    assert(core.state == AR01_FAULT && (core.faults & AR01_RIGHT_JAM));
    assert(core.left_pwm_permille == 0 && core.right_pwm_permille == 0);
    ar01_frame_t clear = command(AR01_CLEAR_FAULT, 1);
    assert(!ar01_core_command(&core, &clear, 31));
}

static void test_no_motion_with_unavailable_current(void)
{
    ar01_config_t config = bench_test_config();
    ar01_core_t core;
    ar01_core_init(&core, &config);
    ar01_inputs_t inputs = healthy_inputs();
    ar01_core_tick(&core, &inputs, 0);
    ar01_frame_t arm = command(AR01_ARM, 1);
    assert(ar01_core_command(&core, &arm, 0));
    ar01_frame_t speed = command(AR01_SET_WHEEL_SPEED, 2);
    speed.length = 8;
    ar01_put_u32(speed.payload, 3000);
    ar01_put_u32(speed.payload + 4, 0);
    assert(ar01_core_command(&core, &speed, 0));
    for (uint32_t time = 10; time <= 50; time += 10)
        ar01_core_tick(&core, &inputs, time);
    assert(core.state == AR01_ARMED);
    ar01_core_tick(&core, &inputs, 60);
    assert(core.state == AR01_FAULT && (core.faults & AR01_LEFT_JAM));
    assert(core.left_pwm_permille == 0 && core.right_pwm_permille == 0);
}

int main(void)
{
    test_protocol();
    test_timeout_and_rearm();
    test_estop_jam_and_wrap();
    test_sequence_rollover_and_overcurrent();
    test_no_motion_with_unavailable_current();
    puts("AR-01 protocol/core host tests: PASS");
    return 0;
}
