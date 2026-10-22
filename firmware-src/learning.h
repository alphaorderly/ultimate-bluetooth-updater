#ifndef SWITCH2_LEARNING_H
#define SWITCH2_LEARNING_H
#include <stdint.h>
uint32_t learn_checksum(const uint8_t *bytes, uint32_t length);
uint32_t learn_parse_advertisement(const uint8_t *adv, uint32_t length,
                                  const uint8_t *expected_host,
                                  uint32_t *wake_offset);
uint32_t learn_record_valid(const uint8_t *record);
uint32_t learn_hardware_read(void *descriptor);
uint32_t learn_event_peek(void);
void learn_init_tail(void);
void learn_wake(const void *peer, const void *key);
void learn_peer_save(const void *record, int index);
#endif
