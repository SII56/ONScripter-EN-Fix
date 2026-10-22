/* -*- C++ -*-
 * 
 *  Encoding.cpp - Character encoding handler
 *
 *  Copyright (c) 2019-2020 Ogapee. All rights reserved.
 *
 *  ogapee@aqua.dti2.ne.jp
 *
 *  This program is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program; if not, write to the Free Software
 *  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#include "Encoding.h"
#include <iconv.h>
#include <cerrno>

namespace {
const char *encodingName(int code)
{
    return code == Encoding::CODE_GBK ? "GBK" :
           code == Encoding::CODE_UTF8 ? "UTF-8" : "CP932";
}
}

bool Encoding::convert(const std::string &input, int from, int to, std::string &output)
{
    output.clear();
    iconv_t converter = iconv_open(encodingName(to), encodingName(from));
    if (converter == (iconv_t)-1) return false;
    char *source = const_cast<char *>(input.data());
    size_t remaining = input.size();
    bool valid = true;
    while (remaining) {
        char buffer[4096];
        char *dest = buffer;
        size_t available = sizeof(buffer);
        size_t result = iconv(converter, &source, &remaining, &dest, &available);
        output.append(buffer, sizeof(buffer) - available);
        if (result == (size_t)-1 && errno != E2BIG) { valid = false; break; }
    }
    iconv_close(converter);
    if (!valid) output.clear();
    return valid;
}

int Encoding::detectLegacyEncoding(const char *text, size_t length)
{
    // Prefer the original Japanese interpretation whenever both are valid.
    // Only select GBK when it is valid and CP932 is demonstrably invalid.
    std::string input(text, length), output;
    if (convert(input, CODE_CP932, CODE_UTF8, output)) return CODE_CP932;
    if (convert(input, CODE_GBK, CODE_UTF8, output)) return CODE_GBK;
    return CODE_CP932;
}

extern unsigned short convSJIS2UTF16(unsigned short in);
extern unsigned short convUTF8ToUTF16(const char **src);

Encoding::Encoding()
{
    code = CODE_CP932;
}

Encoding::~Encoding()
{
}

void Encoding::setEncoding(int code)
{
    this->code = code;
}

int Encoding::getBytes(unsigned char ch, int code)
{
    if (code == -1) code = this->code;
    
    if (code == CODE_GBK) {
        return ch >= 0x81 && ch <= 0xfe ? 2 : 1;
    }
    if (code == CODE_CP932){
        if ((ch & 0xe0) == 0xe0 || (ch & 0xe0) == 0x80) return 2;
    }
    else{
        if (ch < 0x80) return 1;
        if (0xc0 <= ch && ch < 0xe0) return 2;
        if (0xe0 <= ch && ch < 0xf0) return 3;
        if (0xf0 <= ch && ch < 0xf8) return 4;
    }

    return 1;
}

int Encoding::getNum(const unsigned char *buf)
{
    int n = 0;
    
    while(buf[0] != 0){
        int n2 = getBytes(buf[0]);
        n++;
        if (n2 > 1) n++;
        // Malformed input must not advance beyond the terminating NUL.
        for (int i = 0; i < n2 && *buf; ++i) ++buf;
    }

    return n;
}

char Encoding::getTextMarker()
{
    if (code == CODE_UTF8)
        return '^';
    
    return '`';
}

unsigned short Encoding::getUTF16(const char *text, int code)
{
    unsigned short unicode = 0;

    if (code == -1) code = this->code;
    
    if (code == CODE_GBK) {
        unsigned char ch = (unsigned char)text[0];
        if (ch < 0x80) return ch;
        if (!text[1]) return 0xfffd;
        // Reuse a stateless GBK converter instead of reopening it for each glyph.
        static iconv_t converter = iconv_open("UTF-16LE", "GBK");
        if (converter == (iconv_t)-1) return 0xfffd;
        char *input = const_cast<char *>(text);
        size_t length = 2;
        unsigned char result[4] = {0, 0, 0, 0};
        char *dest = (char *)result;
        size_t available = sizeof(result);
        iconv(converter, NULL, NULL, NULL, NULL);
        if (iconv(converter, &input, &length, &dest, &available) == (size_t)-1) return 0xfffd;
        return result[0] | (result[1] << 8);
    }
    if (code == CODE_CP932){
        if ((text[0] & 0xe0) == 0xe0 || (text[0] & 0xe0) == 0x80){
            unsigned index = ((unsigned char*)text)[0];
            index = index << 8 | ((unsigned char*)text)[1];
            unicode = convSJIS2UTF16(index);
        }
        else{
            if ((text[0] & 0xe0) == 0xa0 || (text[0] & 0xe0) == 0xc0)
                unicode = ((unsigned char*)text)[0] - 0xa0 + 0xff60;
            else
                unicode = text[0];
        }
    }
    else{
        unicode = convUTF8ToUTF16(&text);
    }

    return unicode;
}
