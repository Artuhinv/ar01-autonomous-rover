#ifndef AR01_LINK_H
#define AR01_LINK_H

#include <stddef.h>
#include <stdint.h>

#define AR01_MAGIC 0xA1u
#define AR01_VERSION 1u
#define AR01_MAX_DECODED 64u
#define AR01_MAX_PAYLOAD (AR01_MAX_DECODED - 9u)
#define AR01_MAX_WIRE 66u

enum ar01_type {
    AR01_SET_WHEEL_SPEED = 0x01,
    AR01_ARM = 0x02,
    AR01_DISARM = 0x03,
    AR01_CLEAR_FAULT = 0x04,
    AR01_STATUS = 0x81
};

typedef struct {
    uint8_t type;
    uint16_t sequence;
    uint8_t length;
    uint8_t payload[AR01_MAX_PAYLOAD];
} ar01_frame_t;

uint16_t ar01_crc16(const uint8_t *data, size_t length);
int ar01_encode(const ar01_frame_t *frame, uint8_t *wire, size_t capacity,
                size_t *wire_length);
int ar01_decode(const uint8_t *wire, size_t wire_length, ar01_frame_t *frame);
void ar01_put_u16(uint8_t *p, uint16_t value);
void ar01_put_u32(uint8_t *p, uint32_t value);
void ar01_put_u64(uint8_t *p, uint64_t value);
uint16_t ar01_get_u16(const uint8_t *p);
uint32_t ar01_get_u32(const uint8_t *p);

#endif
