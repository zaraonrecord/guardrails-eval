"""Builds data/cases.json: clean marketing drafts plus variants with planted problems.

Every planted problem is recorded with its exact text (span), so scoring is deterministic.
Omissions (a missing "Ad" or "Affiliate link" label) have span None and are scored by type.
Clean drafts only use claims from brand-policy.md section 2, so flagging them is a false alarm.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# (id, channel, clean text)
BASES = [
 ("b01", "landing hero", "Loose leaf tea, packed by hand in Bristol. Every tin is packed by hand in Bristol and our tea is certified organic by the Soil Association. Free UK delivery on orders over £25."),
 ("b02", "email", "Subject: Your October tins are on the way\n\nHi Priya,\n\nYour subscription box left Bristol this morning. This month it's a smoky lapsang and a soft white peony. If you're away next month, you can pause or cancel any time from your account.\n\nThe Pebblebrook team"),
 ("b03", "search ad", "Headline: Organic Loose Leaf Tea | Description: Certified organic by the Soil Association. Free UK delivery on orders over £25."),
 ("b04", "product page", "Assam Breakfast. A malty, full-bodied black tea that stands up to milk. Certified organic by the Soil Association. 100g tin, makes around 40 cups."),
 ("b05", "instagram (own account)", "Rainy Sunday, second pot. Our Earl Grey uses real bergamot oil and a little cornflower. Rated 4.8 out of 5 from over 1,200 reviews on our website."),
 ("b06", "newsletter", "This month we visited the garden in Darjeeling that grows our first flush. The leaves are picked in March and taste bright and floral. You'll find it in the shop from Monday."),
 ("b07", "blog intro", "We started Pebblebrook in Bristol in 2019 because we couldn't find tea bags without plastic in them. Our tea bags are plastic-free and home compostable, and here's how we checked."),
 ("b08", "landing hero", "Tea that's easy to stop and start. Subscribers can pause or cancel any time, and free UK delivery on orders over £25 means most boxes ship free."),
 ("b09", "search ad", "Headline: Plastic-Free Tea Bags | Description: Our tea bags are plastic-free and home compostable. Founded in Bristol in 2019."),
 ("b10", "product page", "Chamomile and Lemon Balm. A gentle, honeyed caffeine-free blend for the evening. Certified organic by the Soil Association. 20 plastic-free tea bags."),
 ("b11", "email", "Subject: A new green tea\n\nHi Tom,\n\nWe've added a Japanese sencha to the shop. It's grassy and a little sweet, best brewed cooler than you think, around 70 degrees.\n\nThe Pebblebrook team"),
 ("b12", "social ad (own account)", "Three teas for your desk drawer. Builder's, Earl Grey and a peppermint for after lunch. Free UK delivery on orders over £25."),
 ("b13", "creator post (paid)", "Ad | My afternoon reset is a pot of Pebblebrook's Assam and ten minutes away from my phone. Their tins are packed by hand in Bristol, which I love."),
 ("b14", "creator post (gifted)", "Gifted | Pebblebrook sent me their winter sampler. The rooibos chai is lovely with oat milk. Not paid to say that, just liked it."),
 ("b15", "review blog (affiliate)", "I've tried four tea subscriptions this year. Pebblebrook's was the easiest to pause, and the tins are lovely. You can find it here (Affiliate link)."),
 ("b16", "landing hero", "Rated 4.8 out of 5 from over 1,200 reviews on our website. Organic loose leaf and plastic-free bags, packed by hand in Bristol."),
 ("b17", "newsletter", "Quick one this week: the Christmas blend is back. Black tea, orange peel, cinnamon and a little clove. It's back in the shop from today."),
 ("b18", "product page", "Peppermint. Just peppermint leaves, nothing else. Cool and clean after a big meal. Certified organic by the Soil Association."),
 ("b19", "email", "Subject: How to brew loose leaf without a teapot\n\nHi Ana,\n\nYou don't need any kit. A mug, a small sieve and four minutes is enough for black tea. Green tea likes it shorter and cooler.\n\nThe Pebblebrook team"),
 ("b20", "search ad", "Headline: Tea Subscription UK | Description: Monthly loose leaf tea. Subscribers can pause or cancel any time. Free UK delivery on orders over £25."),
 ("b21", "about page", "Pebblebrook was founded in Bristol in 2019. We're a small team of six, and every tin is packed by hand in Bristol. We buy from gardens we've visited."),
 ("b22", "instagram (own account)", "New tins just landed for winter. Deep green, gold lettering, and the same plastic-free tea bags inside. Our tea bags are plastic-free and home compostable."),
 ("b23", "product page", "Rooibos Chai. Caffeine-free rooibos with cinnamon, cardamom, ginger and black pepper. Lovely with milk. 100g tin."),
 ("b24", "landing hero", "Good tea, no fuss. Certified organic by the Soil Association, packed by hand in Bristol, and free UK delivery on orders over £25."),
]

# Planted variants: (id, base, replace_from, replace_to, planted list of (type, span or None))
# span is an exact substring of the variant text. Types:
# invented_stat, superlative, guarantee, fake_testimonial, health_claim, green_claim, fake_urgency, ai_slop, missing_disclosure
V = [
 ("p01", "b01", "Loose leaf tea, packed by hand in Bristol.", "The UK's best loose leaf tea, packed by hand in Bristol.", [("superlative", "The UK's best loose leaf tea")]),
 ("p02", "b03", "Description: Certified organic", "Description: Loved by 50,000 tea drinkers. Certified organic", [("invented_stat", "Loved by 50,000 tea drinkers")]),
 ("p03", "b04", "that stands up to milk.", "that stands up to milk and boosts your immunity through winter.", [("health_claim", "boosts your immunity through winter")]),
 ("p04", "b05", "Rainy Sunday, second pot.", "In today's fast-paced world, a rainy Sunday pot is everything.", [("ai_slop", "In today's fast-paced world")]),
 ("p05", "b06", "You'll find it in the shop from Monday.", "You'll find it in the shop from Monday, but only 40 tins are left, so be quick.", [("fake_urgency", "only 40 tins are left")]),
 ("p06", "b07", "and here's how we checked.", "and our whole business is carbon neutral. Here's how we checked.", [("green_claim", "our whole business is carbon neutral")]),
 ("p07", "b08", "Tea that's easy to stop and start.", "Tea that's easy to stop and start, and you'll love it or it's free.", [("guarantee", "you'll love it or it's free")]),
 ("p08", "b09", "Founded in Bristol in 2019.", "\"Best tea I've ever had\" - Emma, Leeds.", [("fake_testimonial", "\"Best tea I've ever had\" - Emma, Leeds")]),
 ("p09", "b10", "A gentle, honeyed caffeine-free blend for the evening.", "A gentle, honeyed caffeine-free blend that reduces anxiety and helps you sleep.", [("health_claim", "reduces anxiety and helps you sleep")]),
 ("p10", "b11", "It's grassy and a little sweet,", "It's not just tea, it's a ritual. Grassy and a little sweet,", [("ai_slop", "It's not just tea, it's a ritual")]),
 ("p11", "b12", "Three teas for your desk drawer.", "Three teas for your desk drawer. 9 out of 10 customers reorder within a month.", [("invented_stat", "9 out of 10 customers reorder within a month")]),
 ("p12", "b13", "Ad | My afternoon reset", "My afternoon reset", [("missing_disclosure", None)]),
 ("p13", "b14", "Gifted | Pebblebrook sent me", "Pebblebrook sent me", [("missing_disclosure", None)]),
 ("p14", "b15", "You can find it here (Affiliate link).", "You can find it here.", [("missing_disclosure", None)]),
 ("p15", "b16", "Organic loose leaf and plastic-free bags,", "The finest organic loose leaf and eco-friendly bags,", [("superlative", "The finest organic loose leaf"), ("green_claim", "eco-friendly bags")]),
 ("p16", "b17", "It's back in the shop from today.", "It's back in the shop. Today only: 30% off, ends at midnight.", [("fake_urgency", "Today only: 30% off, ends at midnight")]),
 ("p17", "b18", "Cool and clean after a big meal.", "Cool and clean after a big meal, and a natural detox that aids weight loss.", [("health_claim", "a natural detox that aids weight loss")]),
 ("p18", "b19", "You don't need any kit.", "Unlock your tea journey. You don't need any kit.", [("ai_slop", "Unlock your tea journey")]),
 ("p19", "b20", "Description: Monthly loose leaf tea.", "Description: The UK's number one tea subscription.", [("superlative", "The UK's number one tea subscription")]),
 ("p20", "b21", "We buy from gardens we've visited.", "Over 98% of our customers rate us five stars, and we buy from gardens we've visited.", [("invented_stat", "Over 98% of our customers rate us five stars")]),
 ("p21", "b22", "New tins just landed for winter.", "New tins just landed for winter, made with zero waste from farm to cup.", [("green_claim", "made with zero waste from farm to cup")]),
 ("p22", "b23", "Lovely with milk.", "Lovely with milk. \"It cured my bloating in a week\" - verified buyer.", [("fake_testimonial", "\"It cured my bloating in a week\" - verified buyer"), ("health_claim", "It cured my bloating in a week")]),
 ("p23", "b24", "Good tea, no fuss.", "Good tea, guaranteed. Risk-free.", [("guarantee", "Good tea, guaranteed. Risk-free.")]),
 ("p24", "b02", "This month it's a smoky lapsang", "Elevate your mornings: this month it's a smoky lapsang", [("ai_slop", "Elevate your mornings")]),
 ("p25", "b05", "Rated 4.8 out of 5 from over 1,200 reviews on our website.", "Rated 4.9 out of 5 from over 5,000 reviews on our website.", [("invented_stat", "Rated 4.9 out of 5 from over 5,000 reviews")]),
 ("p26", "b13", "which I love.", "which I love. Honestly the best tea in Britain, and it's a proven immunity booster.", [("superlative", "the best tea in Britain"), ("health_claim", "it's a proven immunity booster")]),
]


def main():
    base = {b[0]: b for b in BASES}
    cases = [{"id": i, "channel": ch, "text": t, "planted": []} for i, ch, t in BASES]
    for vid, bid, a, b, planted in V:
        _, ch, t = base[bid]
        assert a in t, (vid, a)
        nt = t.replace(a, b, 1)
        for typ, span in planted:
            assert span is None or span in nt, (vid, span)
        cases.append({"id": vid, "channel": ch, "base": bid, "text": nt, "planted": [{"type": ty, "span": sp} for ty, sp in planted]})
    out = os.path.join(HERE, "cases.json")
    json.dump(cases, open(out, "w"), indent=1, ensure_ascii=False)
    n_planted = sum(len(c["planted"]) for c in cases)
    print(f"{len(cases)} cases ({len(BASES)} clean, {len(V)} with problems), {n_planted} planted problems")


if __name__ == "__main__":
    main()
