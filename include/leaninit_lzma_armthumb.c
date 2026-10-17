/*
 * leaninit "lzma-armthumb" decoder: ARM-Thumb BCJ inverse filter over a raw LZMA1 stream,
 * decoded by the 7-Zip SDK (lzma/LzmaDec.c, included below as a unity build).
 *
 * This runs from load memory before .text, .rodata, .data and .bss exist, so it is
 * self-contained:
 *   - no libc: memcpy/memset are redirected to byte loops defined here. Build with
 *     -ffreestanding -fno-builtin -fno-tree-loop-distribute-patterns so the compiler does
 *     not synthesise calls to the real ones; `nm -u` of the object must list nothing but
 *     symbols you provide (none, when leaninit_fail is left to its default).
 *   - no globals, no constant tables: the LZMA probability model is a stack array (about
 *     10 KiB with the default lc=1 lp=1) and the destination buffer is the dictionary.
 *   - the linker script must keep every .text* and .rodata* input section of this object
 *     in load memory, next to .leaninit_func (the SDK functions carry no section attribute).
 *
 * Entry payload, written by leaninit/lzma_armthumb.py (all fields little endian):
 *   u32 compressed_len | u32 uncompressed_len | u8 props[5] | u8 zero[3] | raw LZMA1 stream
 * The props must match the parameters this file was compiled for (LEANINIT_LZMA_*); the
 * decoder refuses anything else rather than guess, since a mismatch changes the size of
 * the probability model.
 */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef LEANINIT_FUNC
#define LEANINIT_FUNC __attribute__((section(".leaninit_func")))
#endif

#ifndef LEANINIT_LZMA_LC
#define LEANINIT_LZMA_LC 1
#endif
#ifndef LEANINIT_LZMA_LP
#define LEANINIT_LZMA_LP 1
#endif
#ifndef LEANINIT_LZMA_PB
#define LEANINIT_LZMA_PB 1
#endif
#ifndef LEANINIT_LZMA_DICT_SIZE
#define LEANINIT_LZMA_DICT_SIZE (256u * 1024u)
#endif

/* Failure codes passed to leaninit_fail(); the LZMA result code is or-ed into the high byte. */
#define LEANINIT_FAIL_LZMA_HEADER   0x01u /* props or reserved bytes differ from this build */
#define LEANINIT_FAIL_LZMA_DECODE   0x02u /* LzmaDecode returned an error (SRes << 8) */
#define LEANINIT_FAIL_LZMA_LENGTH   0x03u /* decoded or consumed length differs from the header */
#define LEANINIT_FAIL_LZMA_STATUS   0x04u /* stream did not finish where the header said */

static LEANINIT_FUNC __attribute__((unused)) void *leaninit_lzma_memcpy(void *dst, const void *src, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    const uint8_t *s = (const uint8_t *)src;
    while (n--) {
        *d++ = *s++;
    }
    return dst;
}

static LEANINIT_FUNC __attribute__((unused)) void *leaninit_lzma_memset(void *dst, int c, size_t n)
{
    uint8_t *d = (uint8_t *)dst;
    while (n--) {
        *d++ = (uint8_t)c;
    }
    return dst;
}

#define memcpy leaninit_lzma_memcpy
#define memset leaninit_lzma_memset

#include "lzma/LzmaDec.c"

#ifdef Z7_LZMA_PROB32
#error "Z7_LZMA_PROB32 doubles the stack buffer; keep it undefined (see lzma/README.md)"
#endif

enum {
    LEANINIT_LZMA_HEADER_SIZE = 16,
    LEANINIT_LZMA_PROPS0 = (LEANINIT_LZMA_PB * 5 + LEANINIT_LZMA_LP) * 9 + LEANINIT_LZMA_LC,
    LEANINIT_LZMA_NUM_PROBS = NUM_BASE_PROBS + (LZMA_LIT_SIZE << (LEANINIT_LZMA_LC + LEANINIT_LZMA_LP)),
};
_Static_assert(LEANINIT_LZMA_LC + LEANINIT_LZMA_LP <= 4, "lc + lp must not exceed 4");
_Static_assert(sizeof(CLzmaProb) == 2, "probabilities are expected to be 16-bit");

__attribute__((weak, noreturn)) LEANINIT_FUNC void leaninit_fail(uint32_t code)
{
    (void)code;
    for (;;) {
    }
}

/* The only allocation LzmaDecode() makes is the probability array: serve it from the stack. */
typedef struct {
    ISzAlloc vt; /* first: LzmaDecode() receives a pointer to it */
    uint8_t *buf;
    size_t size;
    size_t used;
} leaninit_lzma_arena_t;

static LEANINIT_FUNC void *leaninit_lzma_alloc(ISzAllocPtr p, size_t size)
{
    leaninit_lzma_arena_t *a = (leaninit_lzma_arena_t *)(uintptr_t)p;
    if (size > a->size - a->used) {
        return NULL;
    }
    void *out = a->buf + a->used;
    a->used += size;
    return out;
}

static LEANINIT_FUNC void leaninit_lzma_free(ISzAllocPtr p, void *address)
{
    (void)p;
    (void)address;
}

static LEANINIT_FUNC uint32_t leaninit_rd_u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

/* Inverse of xz's ARM-Thumb BCJ filter, position base 0 at the start of the entry. */
static LEANINIT_FUNC void leaninit_armthumb_decode(uint8_t *b, uint32_t n)
{
    uint32_t i = 0;
    while (i + 4 <= n) {
        if ((b[i + 1] & 0xF8) == 0xF0 && (b[i + 3] & 0xF8) == 0xF8) {
            uint32_t src = ((uint32_t)(b[i + 1] & 7) << 19) | ((uint32_t)b[i] << 11) |
                           ((uint32_t)(b[i + 3] & 7) << 8) | (uint32_t)b[i + 2];
            src <<= 1;
            uint32_t dest = (src - (i + 4)) >> 1;
            b[i + 1] = (uint8_t)(0xF0 | ((dest >> 19) & 7));
            b[i] = (uint8_t)((dest >> 11) & 0xFF);
            b[i + 3] = (uint8_t)(0xF8 | ((dest >> 8) & 7));
            b[i + 2] = (uint8_t)(dest & 0xFF);
            i += 2;
        }
        i += 2;
    }
}

LEANINIT_FUNC const uint8_t *leaninit_lzma_armthumb_decode(void *dst, const uint8_t *src)
{
    const uint32_t comp_len = leaninit_rd_u32(src);
    const uint32_t uncomp_len = leaninit_rd_u32(src + 4);
    const uint8_t *props = src + 8;
    if (props[0] != LEANINIT_LZMA_PROPS0 || leaninit_rd_u32(props + 1) != LEANINIT_LZMA_DICT_SIZE ||
        (src[13] | src[14] | src[15]) != 0) {
        leaninit_fail(LEANINIT_FAIL_LZMA_HEADER);
    }
    const uint8_t *stream = src + LEANINIT_LZMA_HEADER_SIZE;

    CLzmaProb probs[LEANINIT_LZMA_NUM_PROBS] __attribute__((aligned(8)));
    leaninit_lzma_arena_t arena;
    arena.vt.Alloc = leaninit_lzma_alloc;
    arena.vt.Free = leaninit_lzma_free;
    arena.buf = (uint8_t *)probs;
    arena.size = sizeof(probs);
    arena.used = 0;

    SizeT dest_len = uncomp_len;
    SizeT src_len = comp_len;
    ELzmaStatus status = LZMA_STATUS_NOT_SPECIFIED;
    SRes res = LzmaDecode((Byte *)dst, &dest_len, stream, &src_len, props, LZMA_PROPS_SIZE, LZMA_FINISH_END, &status,
                          &arena.vt);
    if (res != SZ_OK) {
        leaninit_fail(LEANINIT_FAIL_LZMA_DECODE | ((uint32_t)res << 8));
    }
    if (dest_len != uncomp_len || src_len != comp_len) {
        leaninit_fail(LEANINIT_FAIL_LZMA_LENGTH);
    }
    if (status != LZMA_STATUS_FINISHED_WITH_MARK && status != LZMA_STATUS_MAYBE_FINISHED_WITHOUT_MARK) {
        leaninit_fail(LEANINIT_FAIL_LZMA_STATUS | ((uint32_t)status << 8));
    }
    leaninit_armthumb_decode((uint8_t *)dst, uncomp_len);
    return stream + comp_len;
}
