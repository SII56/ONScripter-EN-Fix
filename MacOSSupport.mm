// Modern macOS services for the SDL 1.2 compatibility build.
#include "MacOSSupport.h"
#include <cstdio>
#import <Cocoa/Cocoa.h>
#import <CoreText/CoreText.h>

namespace {
NSString *decode(const char *text, int encoding)
{
    if (!text) return @"";
    NSStringEncoding nativeEncoding = encoding == 2 ?
        CFStringConvertEncodingToNSStringEncoding(kCFStringEncodingGB_18030_2000) :
        encoding == 1 ? NSUTF8StringEncoding : NSShiftJISStringEncoding;
    NSString *result = [NSString stringWithCString:text encoding:nativeEncoding];
    if (!result) result = [NSString stringWithCString:text
        encoding:encoding == 1 ? NSShiftJISStringEncoding : NSUTF8StringEncoding];
    return result ? result : @"(Invalid text encoding)";
}

void activate()
{
    [NSApplication sharedApplication];
    [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];
    [NSApp activateIgnoringOtherApps:YES];
}
}

namespace MacOSSupport {
bool choice(const char *title, const char *message, const char *accept,
            const char *cancel, int encoding)
{
    @autoreleasepool {
        activate();
        NSAlert *dialog = [[[NSAlert alloc] init] autorelease];
        [dialog setMessageText:decode(title, encoding)];
        [dialog setInformativeText:decode(message, encoding)];
        [dialog addButtonWithTitle:decode(accept, true)];
        [dialog addButtonWithTitle:decode(cancel, true)];
        return [dialog runModal] == NSAlertFirstButtonReturn;
    }
}

void alert(const char *title, const char *message, int encoding)
{
    @autoreleasepool {
        activate();
        NSAlert *dialog = [[[NSAlert alloc] init] autorelease];
        [dialog setMessageText:decode(title, encoding)];
        [dialog setInformativeText:decode(message, encoding)];
        [dialog addButtonWithTitle:@"OK"];
        [dialog runModal];
    }
}

std::string saveDirectory(const char *gameid)
{
    @autoreleasepool {
        // Treat gameid as one path component; scripts cannot escape this folder.
        NSString *component = decode(gameid, true);
        component = [component stringByReplacingOccurrencesOfString:@"/" withString:@"_"];
        if (![component length] || [component isEqualToString:@"."] ||
            [component isEqualToString:@".."]) component = @"UnknownGame";
        NSString *base = [NSSearchPathForDirectoriesInDomains(
            NSApplicationSupportDirectory, NSUserDomainMask, YES) firstObject];
        NSString *path = [[base stringByAppendingPathComponent:@"ONScripter-EN"]
            stringByAppendingPathComponent:component];
        NSError *error = nil;
        if (![[NSFileManager defaultManager] createDirectoryAtPath:path
            withIntermediateDirectories:YES attributes:nil error:&error]) {
            fprintf(stderr, "Cannot create save directory: %s\n", [[error description] UTF8String]);
            return std::string();
        }
        return std::string([path fileSystemRepresentation]);
    }
}

bool isAppBundle()
{
    @autoreleasepool {
        return [[[[NSBundle mainBundle] bundlePath] pathExtension] isEqualToString:@"app"];
    }
}

std::string chooseGameDirectory()
{
    @autoreleasepool {
        activate();
        NSOpenPanel *panel = [NSOpenPanel openPanel];
        [panel setCanChooseFiles:NO];
        [panel setCanChooseDirectories:YES];
        [panel setAllowsMultipleSelection:NO];
        [panel setMessage:@"Choose a folder containing an NScripter game."];
        if ([panel runModal] != NSModalResponseOK) return std::string();
        return std::string([[[panel URL] path] fileSystemRepresentation]);
    }
}

std::string adjacentGameDirectory()
{
    @autoreleasepool {
        NSString *directory = [[[NSBundle mainBundle] bundlePath] stringByDeletingLastPathComponent];
        // Match the entry scripts accepted by ScriptHandler::readScript.
        const char *scripts[] = {"0.txt", "00.txt", "0.utf", "00.utf", "0.utf.txt",
            "00.utf.txt", "nscr_sec.dat", "nscript.___", "nscript.dat", "pscript.dat"};
        NSFileManager *manager = [NSFileManager defaultManager];
        for (size_t i = 0; i < sizeof(scripts) / sizeof(scripts[0]); ++i) {
            NSString *path = [directory stringByAppendingPathComponent:
                [NSString stringWithUTF8String:scripts[i]]];
            BOOL isDirectory = NO;
            if ([manager fileExistsAtPath:path isDirectory:&isDirectory] && !isDirectory)
                return std::string([directory fileSystemRepresentation]);
        }
        return std::string();
    }
}

std::string systemFont(bool chinese)
{
    @autoreleasepool {
        if (chinese) {
            NSString *path = @"/System/Library/Fonts/STHeiti Light.ttc";
            if ([[NSFileManager defaultManager] fileExistsAtPath:path])
                return std::string([path fileSystemRepresentation]);
        }
        CTFontRef font = CTFontCreateWithName(CFSTR("HiraginoSans-W3"), 16, NULL);
        CFURLRef url = (CFURLRef)CTFontCopyAttribute(font, kCTFontURLAttribute);
        std::string path;
        if (url) {
            path = [[(NSURL *)url path] fileSystemRepresentation];
            CFRelease(url);
        }
        CFRelease(font);
        return path;
    }
}

void openURL(const char *url, int encoding)
{
    @autoreleasepool {
        NSURL *target = [NSURL URLWithString:decode(url, encoding)];
        if (target) [[NSWorkspace sharedWorkspace] openURL:target];
    }
}
}
