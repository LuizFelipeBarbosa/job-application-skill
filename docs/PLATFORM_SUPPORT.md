# Platform support matrix

| Capability | macOS | Windows | Linux |
| --- | --- | --- | --- |
| Tracker and schema tools | Full | Full | Full |
| Gmail read-only verification | Full | Full | Full |
| Local analytics dashboard | Full | Full | Full |
| OS credential vault | Keychain | Credential Locker | Supported secure keyring backends only |
| Guarded clipboard | `pbcopy`/`pbpaste` | `clip.exe`/PowerShell | Wayland or X11 tool pair |
| Chrome control | Full with official integration | Full with official integration | Where the official integration is supported |
| Computer Use | Full | Full | Partial; no parity claim |
| Hosted dashboard | Full | Full | Full |

Full support means the release workflow includes a manual acceptance record for that platform. Linux warnings do not block tracker, Gmail, dashboard, or supported vault use, but verification challenges requiring unavailable Computer Use must be handed to the user.
