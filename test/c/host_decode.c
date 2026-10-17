/* Host harness for leaninit_lzma_armthumb.c: decode one entry file, write the result.
 * usage: host_decode ENTRY OUT   -> prints the number of bytes consumed, exit 0
 *        exit 2 with "leaninit_fail(0x..)" on stderr when the decoder refuses the entry */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

const uint8_t *leaninit_lzma_armthumb_decode(void *dst, const uint8_t *src);

__attribute__((noreturn)) void leaninit_fail(uint32_t code)
{
    fprintf(stderr, "leaninit_fail(0x%x)\n", (unsigned)code);
    exit(2);
}

int main(int argc, char **argv)
{
    if (argc != 3) {
        return 64;
    }
    FILE *f = fopen(argv[1], "rb");
    if (!f) {
        return 66;
    }
    fseek(f, 0, SEEK_END);
    long n = ftell(f);
    fseek(f, 0, SEEK_SET);
    uint8_t *src = malloc((size_t)n + 16);
    if (fread(src, 1, (size_t)n, f) != (size_t)n) {
        return 66;
    }
    fclose(f);
    uint32_t uncomp = (uint32_t)src[4] | ((uint32_t)src[5] << 8) | ((uint32_t)src[6] << 16) | ((uint32_t)src[7] << 24);
    uint8_t *dst = malloc(uncomp + 1);
    const uint8_t *end = leaninit_lzma_armthumb_decode(dst, src);
    FILE *o = fopen(argv[2], "wb");
    if (!o || fwrite(dst, 1, uncomp, o) != uncomp) {
        return 73;
    }
    fclose(o);
    printf("%ld\n", (long)(end - src));
    return 0;
}
