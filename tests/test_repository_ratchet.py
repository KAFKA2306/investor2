from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryRatchetTest(unittest.TestCase):
    def test_canonical_investment_flow_contract_exists(self) -> None:
        doc = ROOT / "docs" / "architecture" / "canonical-investment-flow.md"
        self.assertTrue(doc.is_file(), "canonical investment-flow contract is missing")
        text = doc.read_text(encoding="utf-8")
        for required in (
            "data/input_ledger",
            "data/hypothesis_lab",
            "frozen manifests",
            "Evidence & Evolution Dashboard",
            "data/decision_ledger",
            "update success",
            "freshness",
            "usable evidence outputs",
        ):
            self.assertIn(required, text)

    def test_readme_links_canonical_flow_and_hypothesis_lab(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/architecture/canonical-investment-flow.md", readme)
        self.assertIn("docs/research/studies/hypothesis-lab.md", readme)
        self.assertIn("data/decision_ledger/README.md", readme)

    def test_canonical_paths_exist(self) -> None:
        self.assertTrue((ROOT / "data" / "input_ledger").is_dir())
        self.assertTrue((ROOT / "data" / "hypothesis_lab").is_dir())
        self.assertTrue((ROOT / "data" / "decision_ledger").is_dir())
        self.assertTrue((ROOT / "data" / "benchmarks").is_dir())
        self.assertTrue((ROOT / "ontology" / "project.yaml").is_file())

    def test_real_data_hypothesis_contract_exists(self) -> None:
        self.assertTrue(
            (ROOT / "data" / "hypothesis_lab" / "hypotheses" / "growth_value_dislocation_v1.json").is_file()
        )
        self.assertTrue(
            (ROOT / "data" / "hypothesis_lab" / "captures" / "2026-08-13-growth-value-dislocation-stage-a.json").is_file()
        )
        self.assertTrue(
            (ROOT / "data" / "hypothesis_lab" / "deep_dives" / "2026-08-13-rion-6823.json").is_file()
        )

    def test_new_alpha_search_is_not_the_stub_orchestrator(self) -> None:
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        marker = "run:newalphasearch:"
        self.assertIn(marker, taskfile)
        section = taskfile.split(marker, 1)[1].split("  research:repeat:2010s:", 1)[0]
        self.assertIn("hypothesis_lab_run.ts", section)
        self.assertNotIn("pipeline_run.ts", section)

    def test_superseded_weekly_research_workflow_is_absent(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "weekly-repo-research.yml"
        self.assertFalse(workflow.exists(), "superseded weekly research workflow reintroduced")


if __name__ == "__main__":
    unittest.main()
