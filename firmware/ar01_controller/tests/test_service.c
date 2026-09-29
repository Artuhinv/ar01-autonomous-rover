#include "ar01_service.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    ar01_inputs_t inputs;
    int32_t left_pwm;
    int32_t right_pwm;
    uint8_t last_tx[AR01_MAX_WIRE];
    uint16_t last_tx_length;
    unsigned tx_count;
    unsigned watchdog_count;
} fixture_t;

static ar01_inputs_t sample(void *context)
{
    fixture_t *fixture = context;
    return fixture->inputs;
}

static void apply_pwm(void *context, int32_t left, int32_t right)
{
    fixture_t *fixture = context;
    fixture->left_pwm = left;
    fixture->right_pwm = right;
}

static bool transmit(void *context, const uint8_t *bytes, uint16_t length)
{
    fixture_t *fixture = context;
    assert(length <= sizeof(fixture->last_tx));
    memcpy(fixture->last_tx, bytes, length);
    fixture->last_tx_length = length;
    ++fixture->tx_count;
    return true;
}

static void watchdog_refresh(void *context)
{
    fixture_t *fixture = context;
    ++fixture->watchdog_count;
}

static ar01_config_t test_config(void)
{
    /* Synthetic test settings: never flash as hardware calibration. */
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

static void send_frame(ar01_service_t *service, uint8_t type, uint16_t sequence,
                       uint32_t now_ms)
{
    ar01_frame_t frame = {0};
    frame.type = type;
    frame.sequence = sequence;
    if (type == AR01_SET_WHEEL_SPEED) {
        frame.length = 8;
        ar01_put_u32(frame.payload, 3000);
        ar01_put_u32(frame.payload + 4, 3000);
    }
    uint8_t wire[AR01_MAX_WIRE];
    size_t length = 0;
    assert(ar01_encode(&frame, wire, sizeof(wire), &length) == 0);
    for (size_t i = 0; i < length; ++i)
        ar01_service_receive_byte(service, wire[i], now_ms);
}

static void send_corrupt_speed(ar01_service_t *service, uint32_t now_ms)
{
    ar01_frame_t frame = {0};
    frame.type = AR01_SET_WHEEL_SPEED;
    frame.sequence = 6;
    frame.length = 8;
    ar01_put_u32(frame.payload, 3000);
    ar01_put_u32(frame.payload + 4, 3000);
    uint8_t wire[AR01_MAX_WIRE];
    size_t length = 0;
    assert(ar01_encode(&frame, wire, sizeof(wire), &length) == 0);
    wire[5] ^= 1u;
    for (size_t i = 0; i < length; ++i)
        ar01_service_receive_byte(service, wire[i], now_ms);
}

static void test_control_overrun(ar01_port_t *port, ar01_config_t *config,
                                 fixture_t *fixture)
{
    ar01_service_t service;
    assert(ar01_service_init(&service, config, port));
    ar01_service_tick(&service, 0);
    send_frame(&service, AR01_ARM, 1, 0);
    send_frame(&service, AR01_SET_WHEEL_SPEED, 2, 0);
    fixture->inputs.left_counter += 3;
    fixture->inputs.right_counter += 3;
    ar01_service_tick(&service, 10);
    assert(fixture->left_pwm > 0);
    unsigned kicks_before = fixture->watchdog_count;
    ar01_service_tick(&service, 40);
    assert(service.core.state == AR01_FAULT);
    assert(service.core.faults & AR01_CONTROL_OVERRUN);
    assert(fixture->left_pwm == 0 && fixture->right_pwm == 0);
    assert(fixture->watchdog_count == kicks_before);
}

int main(void)
{
    fixture_t fixture = {0};
    fixture.inputs.left_current_ma = 0xFFFFu;
    fixture.inputs.right_current_ma = 0xFFFFu;
    fixture.inputs.bus_mv = 12000;
    fixture.inputs.estop_closed = true;
    fixture.inputs.left_diag_ok = true;
    fixture.inputs.right_diag_ok = true;
    ar01_port_t port = {&fixture, sample, apply_pwm, transmit,
                        watchdog_refresh};
    ar01_service_t service;
    ar01_config_t config = test_config();
    assert(ar01_service_init(&service, &config, &port));
    assert(fixture.left_pwm == 0 && fixture.right_pwm == 0);
    ar01_service_tick(&service, 0);
    send_frame(&service, AR01_ARM, 1, 0);
    send_frame(&service, AR01_SET_WHEEL_SPEED, 2, 10);
    fixture.inputs.left_counter += 3;
    fixture.inputs.right_counter += 3;
    ar01_service_tick(&service, 10);
    assert(fixture.left_pwm > 0 && fixture.right_pwm > 0);
    send_frame(&service, AR01_DISARM, 3, 11);
    assert(fixture.left_pwm == 0 && fixture.right_pwm == 0);
    send_frame(&service, AR01_ARM, 4, 11);
    send_frame(&service, AR01_SET_WHEEL_SPEED, 5, 11);
    for (uint32_t t = 20; t <= 220; t += 10) {
        fixture.inputs.left_counter += 3;
        fixture.inputs.right_counter += 3;
        if (t == 100) send_corrupt_speed(&service, t);
        ar01_service_tick(&service, t);
    }
    assert(service.core.state == AR01_FAULT);
    assert(service.core.faults & AR01_COMMAND_TIMEOUT);
    assert(fixture.left_pwm == 0 && fixture.right_pwm == 0);
    assert(fixture.tx_count == 11);
    assert(fixture.watchdog_count == 23);
    assert(service.rejected_frames == 1u);
    ar01_frame_t status;
    assert(ar01_decode(fixture.last_tx, fixture.last_tx_length, &status) == 0);
    assert(status.type == AR01_STATUS && status.payload[28] == AR01_FAULT);

    uint32_t rejected_before = service.rejected_frames;
    for (unsigned i = 0; i < AR01_MAX_WIRE + 2u; ++i)
        ar01_service_receive_byte(&service, 1, 220);
    ar01_service_receive_byte(&service, 0, 220);
    assert(service.rejected_frames == rejected_before + 1u);
    test_control_overrun(&port, &config, &fixture);
    puts("AR-01 service host tests: PASS");
    return 0;
}
