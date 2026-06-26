# FRBR-based three-layer bibliographic model (Work / Manifestation / Item)

A "book" is modeled across three FRBR-derived layers — **Work** (the abstract
creation), **Manifestation** (a published edition, with ISBN/publisher), and
**Item** (a physical copy with a barcode) — related one-to-many top to bottom
and referenced **by ID** as separate aggregates, never physically nested. The
FRBR **Expression** layer (translations, intellectual forms) is **deliberately
excluded** from v1.

This is a deliberate move away from the Grokking interview model's two-layer
`Book` / `BookItem`, toward the real ILS vocabulary (Next-L / FRBR-LRM) that
issue #1's comment calls the "real requirements".

## Why

- The two-layer toy collapses information that the domain genuinely needs:
  author/original-title belong to the Work, ISBN/publisher/edition to the
  Manifestation, barcode/state/location to the Item. Loans attach to an Item;
  Holds to a Manifestation. A flat model cannot express these distinctions.
- **Expression is excluded** because it adds real cataloguing weight (modeling
  translations and intellectual forms) while having **no effect on
  circulation** — the v1 slice. Work is kept (lightweight) because grouping
  editions of the same creation is still useful; Expression is not.

## Consequences

- Availability and policy decisions hang off Manifestation/Item, so most
  circulation reads start there, not at the Work.
- If serials, authority control, or translation-aware cataloguing enter scope
  later, Expression may need to be introduced between Work and Manifestation —
  an additive change, not a rewrite, given the layers are already ID-linked.
