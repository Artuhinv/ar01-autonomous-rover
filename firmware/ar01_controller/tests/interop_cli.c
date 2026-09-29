#include "ar01_link.h"

#include <stdio.h>
#include <string.h>

static int nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    size_t hex_length = strlen(argv[1]);
    if (hex_length % 2 || hex_length / 2 > AR01_MAX_WIRE) return 2;
    uint8_t wire[AR01_MAX_WIRE];
    for (size_t i = 0; i < hex_length / 2; ++i) {
        int hi = nibble(argv[1][2 * i]);
        int lo = nibble(argv[1][2 * i + 1]);
        if (hi < 0 || lo < 0) return 2;
        wire[i] = (uint8_t)((hi << 4) | lo);
    }
    ar01_frame_t frame;
    if (ar01_decode(wire, hex_length / 2, &frame)) return 1;
    size_t length = 0;
    if (ar01_encode(&frame, wire, sizeof(wire), &length)) return 1;
    for (size_t i = 0; i < length; ++i) printf("%02x", wire[i]);
    puts("");
    return 0;
}
