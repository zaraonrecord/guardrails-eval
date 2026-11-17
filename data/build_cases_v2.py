"""Round 2: the same 24 clean drafts, plus variants with SUBTLE problems, the kind that slip through review.
Writes data/cases-v2.json. Same format and scoring as round 1."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_cases import BASES

V2 = [
 ("s01", "b05", "from over 1,200 reviews", "from over 2,000 reviews", [("invented_stat", "from over 2,000 reviews")]),
 ("s02", "b08", "Tea that's easy to stop and start.", "Tea that's easy to stop and start. Most subscribers stay with us for over a year.", [("invented_stat", "Most subscribers stay with us for over a year")]),
 ("s03", "b04", "A malty, full-bodied black tea that stands up to milk.", "A malty, full-bodied black tea, noticeably smoother than supermarket tea bags.", [("superlative", "noticeably smoother than supermarket tea bags")]),
 ("s04", "b21", "Pebblebrook was founded in Bristol in 2019.", "Pebblebrook was founded in Bristol in 2019 and has become Bristol's favourite tea.", [("superlative", "Bristol's favourite tea")]),
 ("s05", "b20", "Subscribers can pause or cancel any time.", "If your box isn't right, we'll make it right.", [("guarantee", "If your box isn't right, we'll make it right")]),
 ("s06", "b06", "The leaves are picked in March and taste bright and floral.", "The leaves are picked in March and taste bright and floral. Our customers tell us it's the only tea they drink now.", [("fake_testimonial", "Our customers tell us it's the only tea they drink now")]),
 ("s07", "b10", "A gentle, honeyed caffeine-free blend for the evening.", "A gentle, honeyed caffeine-free blend to help you wind down and sleep better.", [("health_claim", "help you wind down and sleep better")]),
 ("s08", "b11", "It's grassy and a little sweet,", "It's grassy, a little sweet and packed with antioxidants,", [("health_claim", "packed with antioxidants")]),
 ("s09", "b18", "Cool and clean after a big meal.", "Cool, clean and gentle on your stomach after a big meal.", [("health_claim", "gentle on your stomach")]),
 ("s10", "b22", "Deep green, gold lettering, and the same plastic-free tea bags inside.", "Deep green, gold lettering, planet-friendly packaging and the same plastic-free tea bags inside.", [("green_claim", "planet-friendly packaging")]),
 ("s11", "b12", "Free UK delivery on orders over £25.", "Free UK delivery on orders over £25, while stocks last.", [("fake_urgency", "while stocks last")]),
 ("s12", "b17", "It's back in the shop from today.", "It's back in the shop from today and selling fast.", [("fake_urgency", "selling fast")]),
 ("s13", "b13", "Ad | My afternoon reset is a pot of Pebblebrook's Assam and ten minutes away from my phone. Their tins are packed by hand in Bristol, which I love.", "My afternoon reset is a pot of Pebblebrook's Assam and ten minutes away from my phone. Their tins are packed by hand in Bristol, which I love. #tea #teatime #bristol #slowliving #ad #assam #selfcare", [("missing_disclosure", None)]),
 ("s14", "b14", "Gifted | Pebblebrook sent me their winter sampler. The rooibos chai is lovely with oat milk. Not paid to say that, just liked it.", "The rooibos chai from Pebblebrook's winter sampler is lovely with oat milk. Thanks to the team for sending it over!", [("missing_disclosure", None)]),
 ("s15", "b15", "You can find it here (Affiliate link).", "You can find it here.*\n\n*I may earn a small commission.", [("missing_disclosure", None)]),
 ("s16", "b24", "Good tea, no fuss.", "Brewed with care. Packed with love. Delivered with a smile.", [("ai_slop", "Brewed with care. Packed with love. Delivered with a smile.")]),
 ("s17", "b02", "Your subscription box left Bristol this morning.", "Your subscription box left Bristol this morning. As always, it ships within 24 hours of your order.", [("invented_stat", "ships within 24 hours of your order")]),
 ("s18", "b23", "100g tin.", "100g tin. Was £12, now £8.", [("invented_stat", "Was £12, now £8")]),
 ("s19", "b16", "Organic loose leaf and plastic-free bags,", "Organic loose leaf and fully sustainable bags,", [("green_claim", "fully sustainable bags")]),
 ("s20", "b19", "Green tea likes it shorter and cooler.", "Green tea likes it shorter and cooler. Whether you're a seasoned tea lover or just starting out, there's a cup for everyone.", [("ai_slop", "Whether you're a seasoned tea lover or just starting out")]),
 ("s21", "b09", "Founded in Bristol in 2019.", "Recommended by nutritionists.", [("invented_stat", "Recommended by nutritionists")]),
 ("s22", "b01", "Free UK delivery on orders over £25.", "Free UK delivery on all orders.", [("invented_stat", "Free UK delivery on all orders")]),
]

def main():
    base = {b[0]: b for b in BASES}
    cases = [{"id": i, "channel": ch, "text": t, "planted": []} for i, ch, t in BASES]
    for vid, bid, a, b, planted in V2:
        _, ch, t = base[bid]
        assert a in t, (vid, a)
        nt = t.replace(a, b, 1)
        for typ, span in planted:
            assert span is None or span in nt, (vid, span)
        cases.append({"id": vid, "channel": ch, "base": bid, "text": nt, "planted": [{"type": ty, "span": sp} for ty, sp in planted]})
    json.dump(cases, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases-v2.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{len(cases)} cases, {sum(len(c['planted']) for c in cases)} subtle planted problems")

if __name__ == "__main__":
    main()
