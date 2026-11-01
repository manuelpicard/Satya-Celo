"""Tests for the core guarantee of Satya's verdict logic."""

from hypothesis import given, settings
from hypothesis import strategies as st

from satya.model import CERTAIN_VERDICTS, Direction, Evidence, Tier, Verdict
from satya.verdict import decide

evidence_st = st.builds(
    Evidence,
    source=st.sampled_from(["c2pa", "siegel", "register", "metadaten", "wasserzeichen", "aehnlichkeit"]),
    tier=st.sampled_from(list(Tier)),
    direction=st.sampled_from(list(Direction)),
    title=st.just("t"),
    detail=st.just("d"),
    issuer=st.one_of(st.none(), st.text(min_size=1, max_size=8)),
)


def ev(tier: Tier, direction: Direction, issuer: str = "X") -> Evidence:
    return Evidence("test", tier, direction, "t", "d", issuer=issuer)


@settings(max_examples=3000)
@given(st.lists(evidence_st, max_size=12))
def test_certain_verdict_requires_matching_proof(evidence):
    v, certain, _, _ = decide(evidence)
    proofs = [e for e in evidence if e.tier == Tier.PROOF]
    assert certain == (v in CERTAIN_VERDICTS)
    if v == Verdict.AI_PROVEN:
        assert any(p.direction == Direction.AI for p in proofs)
    if v == Verdict.HUMAN_ATTESTED:
        assert any(p.direction == Direction.HUMAN for p in proofs)
    if v == Verdict.CAPTURE_PROVEN:
        assert any(p.direction == Direction.CAPTURE for p in proofs)


@settings(max_examples=3000)
@given(st.lists(evidence_st.filter(lambda e: e.tier != Tier.PROOF), max_size=12))
def test_hints_alone_never_decide(evidence):
    v, certain, _, _ = decide(evidence)
    assert v == Verdict.UNDETERMINED and not certain


@settings(max_examples=2000)
@given(st.lists(evidence_st, max_size=8), st.lists(evidence_st.filter(lambda e: e.tier != Tier.PROOF), max_size=8))
def test_adding_hints_never_changes_verdict(evidence, hints):
    assert decide(evidence)[0] == decide(evidence + hints)[0]


def test_contradiction_is_never_certain():
    v, certain, _, _ = decide([ev(Tier.PROOF, Direction.AI), ev(Tier.PROOF, Direction.HUMAN)])
    assert v == Verdict.CONTRADICTION and not certain
    v, certain, _, _ = decide([ev(Tier.PROOF, Direction.AI), ev(Tier.PROOF, Direction.CAPTURE)])
    assert v == Verdict.CONTRADICTION and not certain


def test_basic_cases():
    assert decide([])[0] == Verdict.UNDETERMINED
    assert decide([ev(Tier.PROOF, Direction.AI)])[0] == Verdict.AI_PROVEN
    assert decide([ev(Tier.PROOF, Direction.HUMAN)])[0] == Verdict.HUMAN_ATTESTED
    assert decide([ev(Tier.PROOF, Direction.CAPTURE)])[0] == Verdict.CAPTURE_PROVEN
    assert decide([ev(Tier.PROOF, Direction.BROKEN)])[0] == Verdict.PROVENANCE_BROKEN
    # a valid proof for the current bytes wins over a broken embedded manifest
    assert decide([ev(Tier.PROOF, Direction.BROKEN), ev(Tier.PROOF, Direction.HUMAN)])[0] == Verdict.HUMAN_ATTESTED
    # strong hints in both directions still do not decide
    assert decide([ev(Tier.HINT, Direction.AI), ev(Tier.HINT, Direction.AI)])[0] == Verdict.UNDETERMINED
