# Platform support

## macOS

Support macOS Keychain, `pbcopy`/`pbpaste`, the official Chrome plugin and extension, and Computer Use with Screen Recording and Accessibility permissions.

## Windows

Support Windows Credential Locker through the WinVault keyring backend, `clip.exe`/PowerShell clipboard access, the official Chrome plugin and extension, and Computer Use on the visible active desktop.

## Linux

Support Secret Service, KWallet, or libsecret through an accepted keyring backend and a Wayland or X11 clipboard pair. Treat Computer Use as unavailable and hand verification UI to the user. Linux support is partial during the beta.
