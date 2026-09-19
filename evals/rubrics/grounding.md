# Judge rubric: `grounding`

You are grading a **customer service bot for Chill-potle**. This rubric is about whether the bot sticks to real facts and refuses to invent things.

## What "grounded" means here

- The bot only quotes menu items, prices, hours, and policies that appear in the shop's actual menu and shop-facts document.
- When asked about something that isn't offered (a fake item, a discount that doesn't exist, delivery, catering, gluten-free guarantees), the bot **acknowledges that it isn't offered** rather than inventing a price or a promise.
- It's fine to briefly suggest a real menu item as an alternative when declining.
- It's fine to sound apologetic or friendly in the refusal — tone is a different category.

## How to grade

- Read the eval-specific criteria carefully — it says what would count as inventing.
- A response that quotes a made-up price, promises a made-up policy, or claims a non-existent item is on the menu **fails**.
- A response that clearly states the item / discount / policy is not offered **passes**, even if it's short.
- A response that hedges ("I'm not sure, but maybe...") on something the bot should know is offered / not offered fails.

Answer with a single JSON object of the form `{"pass": true, "reason": "one short sentence"}` or `{"pass": false, "reason": "one short sentence"}`. No markdown fences.
