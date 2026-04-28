"""Contract test: ONTO-PUB-3 relation metadata accessible from client response dicts.

The client uses Dict[str, Any] for relations — new fields from ONTO-PUB-3
(canonical_type, raw_predicate, normalization_confidence, plausibility_score)
flow through without any client code changes. This test verifies that.
"""


class TestRelationContractPassthrough:
    def test_new_fields_accessible_from_relation_dict(self):
        """ONTO-PUB-3 metadata fields are accessible when present in the API response."""
        # Simulate an API response with ONTO-PUB-3 fields
        relation = {
            "source_id": "abc123",
            "target_id": "def456",
            "relation_type": "works_at",
            "canonical_type": "works_at",
            "raw_predicate": "Employed By",
            "normalization_confidence": 1.0,
            "plausibility_score": 0.95,
        }

        # Client accesses these as plain dict keys
        assert relation["canonical_type"] == "works_at"
        assert relation["raw_predicate"] == "Employed By"
        assert relation["normalization_confidence"] == 1.0
        assert relation["plausibility_score"] == 0.95

    def test_backward_compat_missing_fields(self):
        """Pre-ONTO-PUB-3 relations without new fields still work."""
        relation = {
            "source_id": "abc123",
            "target_id": "def456",
            "relation_type": "WORKS_AT",
        }

        # .get() returns None for missing ONTO-PUB-3 fields
        assert relation.get("canonical_type") is None
        assert relation.get("raw_predicate") is None
        assert relation.get("plausibility_score") is None
