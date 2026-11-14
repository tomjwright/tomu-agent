---
name: meeting-planner
description: Schedule a meeting with people in other cities or countries.
---
When the user wants to find a time to meet people in other places:

1. Work out where everyone is. Use what you remember about the user's city, and
   ask about anyone whose city you don't know.
2. Call get_current_time for each city's time zone, so you know how far apart they are.
3. Suggest two or three slots that fall between 09:00 and 18:00 for everyone.
   If there are none, say so and suggest the least inconvenient slot.
4. Show the slots as a small table with one column per city, in local time.
