from pathlib import Path
import sys
import tempfile
import unittest

from consciousness_presence.core import import_memories, read_core
from consciousness_presence.store import PresenceStore
from project_consciousness.identity_runtime import LifeRuntime


class PresenceCoreHistoryTests(unittest.TestCase):
    def test_evicted_memories_are_recovered_from_verified_historical_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            life = root / "life"
            with LifeRuntime.create(life, seed=173, budget=7) as runtime:
                runtime.apply({"kind": "ingest", "domain": "explore",
                               "text": "The remembered observatory stood on Isla Órbita.",
                               "source_uri": "experiment://observatory/original"}, "original")
                original = runtime.snapshot()["memories"][-1]
                runtime.apply({"kind": "dream"}, "dream")
                dreamed = runtime.snapshot()["memories"][-1]
                budget_after_dream = runtime.snapshot()["budget_remaining"]
                last_id = dreamed["id"]
                for index in range(258):
                    event = runtime.apply({"kind": "reflect", "text": f"Provisional interpretation {index}.",
                                           "references": [last_id]}, f"reflection-{index}")
                    last_id = event["result"]["memory_ids"][0]
                before = runtime.snapshot()
                self.assertEqual(256, len(before["memories"]))
                self.assertNotIn(original["id"], {memory["id"] for memory in before["memories"]})
                self.assertNotIn(dreamed["id"], {memory["id"] for memory in before["memories"]})
                self.assertEqual(budget_after_dream, before["budget_remaining"])
                binding = {"project": str(Path(__file__).resolve().parents[1]), "life": str(life),
                           "python": sys.executable, "skill": str(root / "skill"),
                           "life_id": runtime.manifest["life_id"], "agent_id": before["agent_id"]}

            core = read_core(binding)
            self.assertTrue(core["verification"]["valid"])
            self.assertEqual(260, len(core["memories"]))
            with PresenceStore(root / "presence") as store:
                store.bind(binding)
                import_memories(store, core)
                import_memories(store, core)
                self.assertEqual(260, store.status()["counts"]["records"])
                record_id = f"core:{binding['life_id']}:{original['id']}"
                recovered = store.read(record_id)
                self.assertEqual(original["text"], recovered["text"])
                self.assertEqual("REPORTED", recovered["provenance"])
                self.assertEqual(original["source_uri"], recovered["source"]["source_uri"])
                self.assertIn(record_id, [item["id"] for item in store.search("isla orbita", limit=100)])
                dream_record = store.read(f"core:{binding['life_id']}:{dreamed['id']}")
                self.assertEqual("SIMULATED", dream_record["provenance"])
                self.assertEqual(dreamed["references"], dream_record["source"]["references"])
            with LifeRuntime.open(life) as runtime:
                self.assertEqual(before, runtime.snapshot())


if __name__ == "__main__":
    unittest.main()
