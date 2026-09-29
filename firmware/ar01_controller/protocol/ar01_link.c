#include "ar01_link.h"

int ar01_cobs_encode(const uint8_t *, size_t, uint8_t *, size_t, size_t *);
int ar01_cobs_decode(const uint8_t *, size_t, uint8_t *, size_t, size_t *);

void ar01_put_u16(uint8_t *p, uint16_t v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}

void ar01_put_u32(uint8_t *p, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (uint8_t)(v >> (8u * i));
}

void ar01_put_u64(uint8_t *p, uint64_t v)
{
    for (unsigned i = 0; i < 8; ++i) p[i] = (uint8_t)(v >> (8u * i));
}

uint16_t ar01_get_u16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}

uint32_t ar01_get_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int payload_length_is_valid(uint8_t type, uint8_t length)
{
    switch (type) {
    case AR01_SET_WHEEL_SPEED: return length == 8;
    case AR01_ARM:
    case AR01_DISARM:
    case AR01_CLEAR_FAULT: return length == 0;
    case AR01_STATUS: return length == 31;
    default: return 0;
    }
}

int ar01_encode(const ar01_frame_t *frame, uint8_t *wire, size_t capacity,
                size_t *wire_length)
{
    if (!frame || !wire || !wire_length ||
        !payload_length_is_valid(frame->type, frame->length)) return -1;
    uint8_t decoded[AR01_MAX_DECODED];
    decoded[0] = AR01_MAGIC;
    decoded[1] = AR01_VERSION;
    decoded[2] = frame->type;
    decoded[3] = 0;
    ar01_put_u16(decoded + 4, frame->sequence);
    decoded[6] = frame->length;
    for (size_t i = 0; i < frame->length; ++i)
        decoded[7u + i] = frame->payload[i];
    size_t body_length = 7u + frame->length;
    ar01_put_u16(decoded + body_length, ar01_crc16(decoded, body_length));
    size_t encoded_length = 0;
    if (capacity < 2 || ar01_cobs_encode(decoded, body_length + 2u, wire,
                                         capacity - 1u, &encoded_length)) return -1;
    wire[encoded_length] = 0;
    *wire_length = encoded_length + 1u;
    return 0;
}

int ar01_decode(const uint8_t *wire, size_t wire_length, ar01_frame_t *frame)
{
    if (!wire || !frame || wire_length < 2 || wire_length > AR01_MAX_WIRE ||
        wire[wire_length - 1u] != 0) return -1;
    uint8_t decoded[AR01_MAX_DECODED];
    size_t length = 0;
    if (ar01_cobs_decode(wire, wire_length - 1u, decoded, sizeof(decoded),
                         &length)) return -1;
    if (length < 9 || decoded[0] != AR01_MAGIC ||
        decoded[1] != AR01_VERSION || decoded[3] != 0) return -1;
    uint8_t payload_length = decoded[6];
    if (length != 9u + payload_length ||
        !payload_length_is_valid(decoded[2], payload_length)) return -1;
    if (ar01_get_u16(decoded + length - 2u) !=
        ar01_crc16(decoded, length - 2u)) return -1;
    frame->type = decoded[2];
    frame->sequence = ar01_get_u16(decoded + 4);
    frame->length = payload_length;
    for (size_t i = 0; i < payload_length; ++i)
        frame->payload[i] = decoded[7u + i];
    return 0;
}
