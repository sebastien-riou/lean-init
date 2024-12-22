#pragma once

extern void* __leaninit_table;

//decompress lz4 "legacy" format .i.e. without any optional part
//src shall not include the magic bytes
static const uint8_t* leaninit_decompress(void*dst,const void*const src){
    const uint8_t* in=(const uint8_t*)src;
    uint8_t*out=(uint8_t*)dst;
    // contains the latest decoded data
    uint8_t*const history=(uint8_t*)dst;
    // parse all blocks until blockSize == 0
    do{
        // block size (always on 32 bit little endian no matter target architecture)
        uintptr_t blockSize = (*in++);
        blockSize |= ((uintptr_t)(*in++)) <<  8;
        blockSize |= ((uintptr_t)(*in++)) << 16;
        blockSize |= ((uintptr_t)(*in++)) << 24;
        // stop after last block
        if (blockSize == 0) break;
        // decompress block
        uintptr_t blockOffset = 0;
        while (blockOffset < blockSize){
            // get a token
            uint8_t token = (*in++);
            blockOffset++;
            // determine number of literals
            unsigned int numLiterals = token >> 4;
            if (numLiterals == 15){
                // number of literals length encoded in more than 1 byte
                uint8_t current;
                do{
                    current = (*in++);
                    numLiterals += current;
                    blockOffset++;
                } while (current == 255);
            }
            blockOffset += numLiterals;
            // fast loop
            while (numLiterals-- > 0) (*out++) = (*in++);
            // last token has only literals
            if (blockOffset == blockSize) break;
            // match distance is encoded in two bytes (little endian)
            uint16_t delta = (*in++);
            delta |= ((uint16_t)(*in++)) << 8;
            // zero isn't allowed
            if (delta == 0) {
                //error("invalid offset");
                while(1);//TODO: jump to user provided handler
            }
            blockOffset += 2;
            // match length (always >= 4, therefore length is stored minus 4)
            unsigned int matchLength = 4 + (token & 0x0F);
            if (matchLength == 4 + 0x0F) {
                uint8_t current;
                do {// match length encoded in more than 1 byte
                    current = (*in++);
                    matchLength += current;
                    blockOffset++;
                } while (current == 255);
            }
            // copy match
            uintptr_t referencePos = (out-history) - delta;
            // read/write continuous block (no wrap-around at the end of history[])
            while (matchLength-- > 0){
                (*out++) = history[referencePos++];
            }
        }
    }while(0);
    return in;
}

void leaninit_init(){
	const uint8_t*src = (const uint8_t*)(&__leaninit_table);
	while(1){
        uintptr_t dst = 0;
        unsigned int shift = 0;
        for(unsigned int i=0;i<sizeof(dst);i++){
            dst |= ((uintptr_t)(*src++)) <<  shift;//always little endian
            shift += 8;
        }
        if(&__leaninit_table==(void*)dst) break;
		src = leaninit_decompress((void*)dst,src);
	};
}