# Dashboard chart map

| Section | Question | Form | Fields | Palette and fallback |
| --- | --- | --- | --- | --- |
| Application cadence | When did tracker activity and confirmed submissions occur? | Grouped vertical bars with adaptive half-day, day, or week buckets | Local-time bucket, tracked count, submitted count | Stone context and cobalt focus; use the exact application table when fewer than two populated buckets exist. |
| Career stage | Where are confirmed applications now? | Horizontal stage bars | Current career stage, application count | Direct stage labels with cobalt, orange, olive, gold, pink, and neutral tones; table remains the exact lookup surface. |
| Automation outcomes | How did tracked attempts end? | Horizontal comparison bars | Automation status, record count | Orange single-root comparison with direct category labels. |
| Source performance | Which sources produced the most submissions? | Ranked horizontal bars | Site, submitted count, tracked count, submission yield | Cobalt bars; tooltip retains tracked volume and yield context. |
| Location mix | Where are confirmed applications concentrated? | Ranked horizontal bars | Location, submitted count | Olive bars; long labels receive a dedicated category axis. |

All charts use zero baselines for absolute counts, explicit titles and subtitles, accessible SVG output, and the surrounding table for exact record lookup.
