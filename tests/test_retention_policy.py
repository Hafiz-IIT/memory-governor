import unittest

from memory_governor import MemoryGovernor
from retention_policy import RetentionPolicy, governed_retrieve


class RetentionPolicyTests(unittest.TestCase):
    def test_provenance_filter(self):
        g = MemoryGovernor()
        g.remember("trusted", scope="x", provenance="user", now=100)
        g.remember("other", scope="x", provenance="external", now=101)
        policy = RetentionPolicy(allowed_provenances=frozenset({"user"}))
        rows = governed_retrieve(g, scope="x", policy=policy, now=102)
        self.assertEqual([r.text for r in rows], ["trusted"])

    def test_max_age_filter(self):
        g = MemoryGovernor()
        g.remember("old", scope="x", provenance="user", now=100)
        g.remember("fresh", scope="x", provenance="user", now=190)
        policy = RetentionPolicy(max_age_seconds=50)
        rows = governed_retrieve(g, scope="x", policy=policy, now=200)
        self.assertEqual([r.text for r in rows], ["fresh"])

    def test_sensitive_memory_requires_explicit_policy(self):
        g = MemoryGovernor()
        g.remember("private", scope="x", provenance="user", sensitivity="private", now=100)
        self.assertEqual(
            governed_retrieve(g, scope="x", policy=RetentionPolicy(), now=101),
            [],
        )


if __name__ == "__main__":
    unittest.main()
