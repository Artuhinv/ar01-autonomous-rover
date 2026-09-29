#include "ar01_link.h"

/* Internal helpers. A wire frame is COBS bytes followed by one 0x00. */
int ar01_cobs_encode(const uint8_t *input, size_t length, uint8_t *output,
                     size_t capacity, size_t *written)
{
    if (!input || !output || !written || capacity == 0) return -1;
    size_t code_index = 0;
    size_t out = 1;
    uint8_t code = 1;
    for (size_t i = 0; i < length; ++i) {
        if (input[i] == 0) {
            output[code_index] = code;
            if (out >= capacity) return -1;
            code_index = out++;
            code = 1;
        } else {
            if (out >= capacity) return -1;
            output[out++] = input[i];
            ++code;
            if (code == 0xFFu) {
                output[code_index] = code;
                if (out >= capacity) return -1;
                code_index = out++;
                code = 1;
            }
        }
    }
    output[code_index] = code;
    *written = out;
    return 0;
}

int ar01_cobs_decode(const uint8_t *input, size_t length, uint8_t *output,
                     size_t capacity, size_t *written)
{
    if (!input || !output || !written || length == 0) return -1;
    size_t in = 0;
    size_t out = 0;
    while (in < length) {
        uint8_t code = input[in++];
        if (code == 0 || (size_t)(code - 1u) > length - in) return -1;
        for (unsigned i = 1; i < code; ++i) {
            if (input[in] == 0 || out >= capacity) return -1;
            output[out++] = input[in++];
        }
        if (code != 0xFFu && in < length) {
            if (out >= capacity) return -1;
            output[out++] = 0;
        }
    }
    *written = out;
    return 0;
}
