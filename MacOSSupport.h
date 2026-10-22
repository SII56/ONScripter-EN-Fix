// Modern macOS services, independent of the legacy MACOSX Cocoa port.
#ifndef ONS_MACOS_SUPPORT_H
#define ONS_MACOS_SUPPORT_H

#include <string>

namespace MacOSSupport {
bool choice(const char *title, const char *message, const char *accept,
            const char *cancel, int encoding);
void alert(const char *title, const char *message, int encoding);
std::string saveDirectory(const char *gameid);
std::string chooseGameDirectory();
std::string adjacentGameDirectory();
std::string systemFont(bool chinese = false);
std::string bundledFont();
double backingScale();
bool isAppBundle();
void openURL(const char *url, int encoding);
}

#endif
