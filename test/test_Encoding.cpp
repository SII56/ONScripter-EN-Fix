#include <cstring>

#include "Encoding.h"

#include "gtest/gtest.h"

namespace {

TEST (TestEncoding, DefaultConstructor) {
  Encoding enc;
  EXPECT_EQ(Encoding::CODE_CP932, enc.getEncoding());
}

TEST (TestEncoding, getEncoding) {
  Encoding enc;
  int code = enc.getEncoding();
  EXPECT_EQ(Encoding::CODE_CP932, code);
}

TEST (TestEncoding, setEncoding) {
  Encoding enc;
  enc.setEncoding(Encoding::CODE_UTF8);
  EXPECT_EQ(Encoding::CODE_UTF8, enc.getEncoding());
}

TEST (TestEncoding, getTextMarker) {
  Encoding enc;
  char marker;

  enc.setEncoding(Encoding::CODE_UTF8);
  marker = enc.getTextMarker();
  EXPECT_TRUE(marker);
  EXPECT_EQ('^', marker);
}

TEST (TestEncoding, getTextMarkerWithCP932) {
  Encoding enc;
  char marker;

  enc.setEncoding(Encoding::CODE_CP932);
  marker = enc.getTextMarker();
  EXPECT_TRUE(marker);
  EXPECT_EQ('`', marker);
}

TEST (TestEncoding, getBytes) {
  Encoding enc;
  int bytes = -1;

  bytes = enc.getBytes('a', Encoding::CODE_UTF8);
  EXPECT_EQ(1, bytes);
  bytes = enc.getBytes(0xC0, Encoding::CODE_UTF8);
  EXPECT_EQ(2, bytes);
  bytes = enc.getBytes(0xE0, Encoding::CODE_UTF8);
  EXPECT_EQ(3, bytes);
  bytes = enc.getBytes(0xF0, Encoding::CODE_UTF8);
  EXPECT_EQ(4, bytes);
}

TEST (TestEncoding, getNum) {
  const char* buf = "abc123";
  Encoding enc;
  int num = enc.getNum((const unsigned char*)buf);
  EXPECT_EQ(6, num);
}

TEST (TestEncoding, getUTF16) {
  Encoding enc;
  std::string text("abc123");
  unsigned short unicode = enc.getUTF16(text.c_str(), Encoding::CODE_UTF8);
  EXPECT_EQ(97, unicode);
}

TEST (TestEncoding, getUTF16WithCP932) {
  Encoding enc;
  char* str = new char[8];
  ::strncpy(str, "abc123", 6);
  unsigned short unicode = enc.getUTF16(str, Encoding::CODE_CP932);
  EXPECT_EQ(97, unicode);
  delete[] str;
  str = new char[2];
  str[0] = 0xA0;
  str[1] = 0x0;
  unicode = enc.getUTF16(str, Encoding::CODE_CP932);
  EXPECT_EQ(65376, unicode);
  delete[] str;
}


TEST (TestEncoding, GBKLeadBytesAndLegacyWidth) {
  Encoding enc;
  enc.setEncoding(Encoding::CODE_GBK);
  EXPECT_EQ(2, enc.getBytes(0xa1));
  EXPECT_EQ(2, enc.getBytes(0xd6));
  EXPECT_EQ(2, enc.getBytes(0xfe));
  EXPECT_EQ(1, enc.getBytes('A'));
  EXPECT_EQ('`', enc.getTextMarker());
  EXPECT_EQ(4, enc.getNum((const unsigned char*)"\xd6\xd0\xce\xc4"));
  // CP932 half-width kana must remain single-byte.
  EXPECT_EQ(1, enc.getBytes(0xa1, Encoding::CODE_CP932));
}

TEST (TestEncoding, GBKUnicodeAndTrailingBackslash) {
  Encoding enc;
  enc.setEncoding(Encoding::CODE_GBK);
  EXPECT_EQ(0x4e2d, enc.getUTF16("\xd6\xd0"));
  EXPECT_EQ(0x6587, enc.getUTF16("\xce\xc4"));
  EXPECT_EQ(0x4e57, enc.getUTF16("\x81\x5c"));
  EXPECT_EQ(0xfffd, enc.getUTF16("\xd6"));
  EXPECT_EQ(0x41, enc.getUTF16("A"));
}

TEST (TestEncoding, LegacyDetectionRequiresEvidence) {
  const std::string chinese("\xbf\xec\xbd\xf8");
  EXPECT_EQ(Encoding::CODE_GBK, Encoding::detectLegacyEncoding(chinese.data(), chinese.size()));
  const std::string japanese("\x82\xa0\x82\xa2");
  EXPECT_EQ(Encoding::CODE_CP932, Encoding::detectLegacyEncoding(japanese.data(), japanese.size()));
  const std::string ambiguous("\xd6\xd0");
  EXPECT_EQ(Encoding::CODE_CP932, Encoding::detectLegacyEncoding(ambiguous.data(), ambiguous.size()));
  EXPECT_EQ(Encoding::CODE_CP932, Encoding::detectLegacyEncoding("ASCII", 5));
}

TEST (TestEncoding, GBKUTF8RoundTripAndInvalidInput) {
  std::string utf8, gbk;
  EXPECT_TRUE(Encoding::convert("\xd6\xd0\xce\xc4", Encoding::CODE_GBK, Encoding::CODE_UTF8, utf8));
  EXPECT_EQ(std::string("\xe4\xb8\xad\xe6\x96\x87"), utf8);
  EXPECT_TRUE(Encoding::convert(utf8, Encoding::CODE_UTF8, Encoding::CODE_GBK, gbk));
  EXPECT_EQ(std::string("\xd6\xd0\xce\xc4"), gbk);
  EXPECT_FALSE(Encoding::convert("\xd6", Encoding::CODE_GBK, Encoding::CODE_UTF8, utf8));
  EXPECT_TRUE(utf8.empty());
}

TEST (TestEncoding, TruncatedMultibyteWidthStopsAtNUL) {
  Encoding enc;
  enc.setEncoding(Encoding::CODE_GBK);
  EXPECT_EQ(2, enc.getNum((const unsigned char*)"\xd6"));
  enc.setEncoding(Encoding::CODE_UTF8);
  EXPECT_EQ(2, enc.getNum((const unsigned char*)"\xe4\xb8"));
}

} // namespace
