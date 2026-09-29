#include "ar01_service.h"

static void apply_output(ar01_service_t *service)
{
    service->port.apply_pwm(service->port.context,
                            service->core.left_pwm_permille,
                            service->core.right_pwm_permille);
}

bool ar01_service_init(ar01_service_t *service, const ar01_config_t *config,
                       const ar01_port_t *port)
{
    if (!service || !port || !port->sample || !port->apply_pwm ||
        !port->transmit || !port->watchdog_refresh) return false;
    service->port = *port;
    service->receive_length = 0;
    service->telemetry_sequence = 0;
    service->last_status_ms = 0;
    service->rejected_frames = 0;
    service->last_tick_ms = 0;
    service->have_tick = false;
    service->dropping_frame = false;
    ar01_core_init(&service->core, config);
    apply_output(service);
    return true;
}

void ar01_service_receive_byte(ar01_service_t *service, uint8_t byte,
                               uint32_t now_ms)
{
    if (!service) return;
    if (byte == 0) {
        if (!service->dropping_frame && service->receive_length > 0) {
            ar01_frame_t frame;
            service->receive[service->receive_length++] = 0;
            if (ar01_decode(service->receive, service->receive_length,
                            &frame) != 0 ||
                !ar01_core_command(&service->core, &frame, now_ms)) {
                ++service->rejected_frames;
            } else {
                apply_output(service);
            }
        }
        service->receive_length = 0;
        service->dropping_frame = false;
        return;
    }
    if (service->dropping_frame) return;
    if (service->receive_length >= AR01_MAX_WIRE - 1u) {
        service->receive_length = 0;
        service->dropping_frame = true;
        ++service->rejected_frames;
        return;
    }
    service->receive[service->receive_length++] = byte;
}

void ar01_service_tick(ar01_service_t *service, uint32_t now_ms)
{
    if (!service) return;
    if (service->have_tick &&
        (uint32_t)(now_ms - service->last_tick_ms) > 20u)
        service->core.faults |= AR01_CONTROL_OVERRUN;
    service->last_tick_ms = now_ms;
    service->have_tick = true;
    ar01_inputs_t inputs = service->port.sample(service->port.context);
    ar01_core_tick(&service->core, &inputs, now_ms);
    apply_output(service);
    if ((uint32_t)(now_ms - service->last_status_ms) >= 20u) {
        ar01_frame_t frame;
        uint8_t wire[AR01_MAX_WIRE];
        size_t length = 0;
        if (ar01_core_status(&service->core, now_ms,
                             service->telemetry_sequence++, &frame) == 0 &&
            ar01_encode(&frame, wire, sizeof(wire), &length) == 0)
            (void)service->port.transmit(service->port.context, wire,
                                         (uint16_t)length);
        service->last_status_ms = now_ms;
    }
    /* Never feed IWDG after a missed control deadline. Hardware period TBD. */
    if (!(service->core.faults & AR01_CONTROL_OVERRUN))
        service->port.watchdog_refresh(service->port.context);
}
