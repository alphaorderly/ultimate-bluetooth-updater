#include "learning.h"

/* Absolute stock symbols are supplied by the patch linker. No mutable globals. */
extern uint32_t stock_hardware_read(void *);
extern uint32_t stock_event_peek(void);
extern uint32_t stock_event_read(void *);
extern void stock_queue_write(const void *, uint32_t);
extern void stock_flag_set(void *, uint32_t);
extern void stock_flag_clear(void *, uint32_t);
extern uint32_t stock_flag_read(void *, uint32_t);
extern void stock_submit(const void *);
extern uint32_t stock_clock(void);
extern uint32_t stock_expired(uint32_t, uint32_t);
extern uint32_t stock_flash_read(uint32_t, void *, uint32_t);
extern uint32_t stock_flash_erase(uint32_t);
extern uint32_t stock_flash_write(uint32_t, const void *, uint32_t);
extern void stock_init_tail(void);
extern uint32_t stock_ble_name(const void *, uint32_t);
extern uint32_t stock_ble_address(const void *);
extern uint32_t stock_features(uint32_t, uint32_t, uint32_t);
extern void stock_rumble(uint32_t, uint32_t, uint32_t);
extern void stock_legacy_wake(const void *, const void *);

#define MEM8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define MEM32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define FLAGS ((void *)(uintptr_t)0x2000cu)
#define SECTOR 0x0107e000u
#define SECTOR_SIZE 4096u
#define SLOT 112u
#define RECORD_SIZE 64u
#define MAGIC 0x20261023u

static uint32_t read32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static void write32(uint8_t *p, uint32_t value)
{
    uint32_t i;
    for (i = 0; i < 4; ++i) p[i] = (uint8_t)(value >> (8 * i));
}
static void copy_bytes(uint8_t *to, const uint8_t *from, uint32_t count)
{
    uint32_t i;
    for (i = 0; i < count; ++i) to[i] = from[i];
}
static uint32_t equal_bytes(const uint8_t *a, const uint8_t *b, uint32_t count)
{
    uint32_t i;
    for (i = 0; i < count; ++i) if (a[i] != b[i]) return 0;
    return 1;
}
static uint32_t all_bytes(const uint8_t *p, uint32_t count, uint8_t value)
{
    uint32_t i;
    for (i = 0; i < count; ++i) if (p[i] != value) return 0;
    return 1;
}
static uint32_t address_valid(const uint8_t *p)
{
    return !all_bytes(p, 6, 0) && !all_bytes(p, 6, 255);
}

uint32_t learn_checksum(const uint8_t *bytes, uint32_t length)
{
    uint32_t hash = 2166136261u, i;
    for (i = 0; i < length; ++i) hash = (hash ^ bytes[i]) * 16777619u;
    return hash;
}

/* The only accepted format is a complete 31-byte legacy advertisement with
 * one 26-byte Nintendo manufacturer payload and one flags AD structure.
 * Manufacturer fields not used for identification are retained verbatim. */
uint32_t learn_parse_advertisement(const uint8_t *adv, uint32_t length,
                                  const uint8_t *expected_host,
                                  uint32_t *wake_offset)
{
    uint32_t offset = 0, found = 0, flags = 0, wake = 0;
    if (!adv || length != 31) return 0;
    while (offset < length) {
        uint32_t size = adv[offset];
        const uint8_t *data;
        if (size < 1 || size > length - offset - 1) return 0;
        if (adv[offset + 1] == 0xff) {
            if (found || size != 27) return 0;
            data = adv + offset + 2;
            if (data[0] != 0x53 || data[1] != 0x05 ||
                data[5] != 0x7e || data[6] != 0x05 ||
                data[7] != 0x66 || data[8] != 0x20 ||
                !address_valid(data + 12)) return 0;
            if (expected_host && !equal_bytes(data + 12, expected_host, 6)) return 0;
            wake = offset + 13;
            found = 1;
        } else if (adv[offset + 1] == 1) {
            if (flags || size != 2) return 0;
            flags = 1;
        } else return 0;
        offset += size + 1;
    }
    if (!found || !flags) return 0;
    if (wake_offset) *wake_offset = wake;
    return 1;
}

uint32_t learn_record_valid(const uint8_t *record)
{
    uint32_t wake;
    if (!record || read32(record) != MAGIC || record[10] != 31 ||
        record[11] != 1 || !address_valid(record + 4) ||
        !address_valid(record + 43) || !all_bytes(record + 49, 11, 0) ||
        read32(record + 60) != learn_checksum(record, 60) ||
        !learn_parse_advertisement(record + 12, 31, 0, &wake)) return 0;
    return record[12 + wake] == 0x81;
}

static uint32_t record_load(uint8_t *record)
{
    return stock_flash_read(SECTOR + SLOT, record, RECORD_SIZE) == 1 &&
           learn_record_valid(record);
}

/* The ROM erase return value has no established success convention. Verify
 * erasure explicitly, then verify every byte of the programmed sector. */
static uint32_t sector_commit(const uint8_t *sector)
{
    uint8_t check[64];
    uint32_t offset;
    (void)stock_flash_erase(SECTOR);
    for (offset = 0; offset < SECTOR_SIZE; offset += sizeof(check)) {
        if (stock_flash_read(SECTOR + offset, check, sizeof(check)) != 1 ||
            !all_bytes(check, sizeof(check), 255)) return 0;
    }
    if (stock_flash_write(SECTOR, sector, SECTOR_SIZE) != 1) return 0;
    for (offset = 0; offset < SECTOR_SIZE; offset += sizeof(check)) {
        if (stock_flash_read(SECTOR + offset, check, sizeof(check)) != 1 ||
            !equal_bytes(check, sector + offset, sizeof(check))) return 0;
    }
    return 1;
}

static uint32_t record_store(const uint8_t *record)
{
    uint8_t sector[SECTOR_SIZE];
    if (stock_flash_read(SECTOR, sector, sizeof(sector)) != 1 ||
        !address_valid(sector + 6) ||
        !equal_bytes(record + 43, sector + 6, 6)) return 0;
    if (!all_bytes(sector + SLOT, RECORD_SIZE, 255) &&
        !learn_record_valid(sector + SLOT)) return 0;
    if (equal_bytes(sector + SLOT, record, RECORD_SIZE)) return 1;
    copy_bytes(sector + SLOT, record, RECORD_SIZE);
    return sector_commit(sector);
}

static uint32_t request(uint8_t opcode, const uint8_t *payload,
                        uint8_t length, uint32_t bit)
{
    uint8_t descriptor[8];
    uint32_t started;
    descriptor[0] = 0;
    descriptor[1] = opcode;
    descriptor[2] = length;
    write32(descriptor + 3, (uint32_t)(uintptr_t)payload);
    descriptor[7] = 0;
    stock_flag_clear(FLAGS, bit);
    stock_submit(descriptor);
    started = stock_clock();
    while (!stock_flag_read(FLAGS, bit)) {
        if (stock_expired(started, 500)) return 0;
    }
    return 1;
}

static uint32_t scan(uint8_t enable)
{
    uint8_t payload[2];
    payload[0] = enable;
    payload[1] = enable ? 0x27 : 0;
    return request(0xa5, payload, 2, 56);
}

uint32_t learn_hardware_read(void *descriptor)
{
    uint8_t *d = (uint8_t *)descriptor;
    uint32_t result = stock_hardware_read(descriptor);
    if (result == 1 && d[0] == 2) {
        const uint8_t *payload = (const uint8_t *)(uintptr_t)read32(d + 3);
        if (d[1] == 6 && d[2] >= 2 && payload[0] == 0xa5 && payload[1] == 0)
            stock_flag_set(FLAGS, 56);
        if (d[1] == 0x2a && d[2] <= 49) {
            uint32_t used = MEM32(0x20f00u), capacity = MEM32(0x20efcu);
            /* Check the complete packet before either non-atomic ring write. */
            if (used <= capacity && (uint32_t)d[2] + 3 <= capacity - used) {
                stock_queue_write(d, 3);
                stock_queue_write(payload, d[2]);
                MEM32(0x2001cu) += 1;
            }
        }
    }
    return result;
}

uint32_t learn_event_peek(void)
{
    uint32_t event = stock_event_peek();
    if (event == 0x2a) {
        uint8_t payload[256], record[RECORD_SIZE], host[6];
        uint32_t length = stock_event_read(payload), wake, i;
        if (MEM8(0x201aau) != 0 || length != 40) return UINT32_MAX;
        /* Stop-scan ACK does not remove advertisements already in the queue.
         * Preserve the first accepted record, including across those events. */
        if (record_load(record)) return UINT32_MAX;
        if (!address_valid(payload + 3) ||
            stock_flash_read(SECTOR + 6, host, sizeof(host)) != 1 ||
            !address_valid(host) ||
            !learn_parse_advertisement(payload + 9, 31, 0, &wake)) return UINT32_MAX;
        for (i = 0; i < RECORD_SIZE; ++i) record[i] = 0;
        write32(record, MAGIC);
        copy_bytes(record + 4, payload + 3, 6);
        record[10] = 31;
        record[11] = 1;
        copy_bytes(record + 12, payload + 9, 31);
        record[12 + wake] = 0x81;
        /* Classic pairing identity binds reuse, not advertisement ownership.
         * The advertised BLE host can legitimately be a different address. */
        copy_bytes(record + 43, host, 6);
        write32(record + 60, learn_checksum(record, 60));
        if (record_store(record)) {
            (void)scan(0);
            stock_rumble(200, 128, 128);
        }
        return UINT32_MAX;
    }
    if (event == 0xb0 && MEM8(0x201aau) == 0) (void)scan(0);
    return event;
}

void learn_init_tail(void)
{
    uint8_t record[RECORD_SIZE];
    stock_init_tail();
    if (MEM8(0x201aau) == 0 && !record_load(record)) (void)scan(1);
}

void learn_wake(const void *peer, const void *key)
{
    static const uint8_t name[4] = {'H', 'H', 0, 0};
    uint8_t record[RECORD_SIZE];
    if (record_load(record) &&
        peer && equal_bytes(record + 43, (const uint8_t *)peer, 6) &&
        scan(0) && stock_ble_name(name, sizeof(name)) == 1 &&
        stock_ble_address(record + 4) == 1 &&
        request(0x34, record + 12, 31, 21) && stock_features(0, 0, 1) == 1) {
        stock_rumble(60, 128, 128);
        return;
    }
    stock_legacy_wake(peer, key);
}

void learn_peer_save(const void *record, int index)
{
    uint8_t sector[SECTOR_SIZE];
    const uint8_t *source = (const uint8_t *)record;
    uint32_t offset, i;
    if (!source || index < 0 || index > 3) return;
    if (stock_flash_read(SECTOR, sector, sizeof(sector)) != 1) return;
    offset = (uint32_t)index * 28;
    if (equal_bytes(sector + offset, source, 28)) return;
    if (index == 0 && !equal_bytes(sector + 6, source + 6, 6) &&
        learn_record_valid(sector + SLOT)) {
        for (i = 0; i < RECORD_SIZE; ++i) sector[SLOT + i] = 255;
    }
    copy_bytes(sector + offset, source, 28);
    (void)sector_commit(sector);
}
