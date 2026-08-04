"""Controlled failure used only to prove the required CI check blocks merge."""


def test_controlled_required_check_failure() -> None:
    raise AssertionError("CONTROLLED F0.6-R2 FAILURE: CI required must block merge")
