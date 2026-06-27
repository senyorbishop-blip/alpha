"""
server/twitch_ext/ — Twitch Extension Backend Service (EBS).

Verifies Twitch Extension JWTs / Bits transaction receipts and routes a viewer's
purchase or sub-claim into the SAME viewer-power grant path the DM uses, so a
power bought with Bits lands in that viewer's in-game profile and animates on
the map through existing code.

Compliance: Bits always buy a single, KNOWN power the viewer selected (one SKU
per power). There is no "Bits -> random power" path anywhere in this module.
"""
