from app.services.stamping.die.process_identity import matches_die_identity


def test_matches_die_identity_optional_filters() -> None:
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier=None, version=None)
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier="安庆常庆", version=None)
    assert matches_die_identity("安庆常庆", "V1", stamping_supplier="安庆常庆", version="V1")
    assert not matches_die_identity("安庆常庆", "V1", stamping_supplier="芜湖", version=None)
    assert not matches_die_identity("安庆常庆", "V1", stamping_supplier=None, version="V2")
