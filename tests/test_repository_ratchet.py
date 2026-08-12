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
            "frozen manifests",
            "Evidence & Evolution Dashboard",
            "update success",
            "freshness",
            "usable evidence outputs",
        ):
            self.assertIn(required, text)

    def test_readme_links_canonical_flow(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/architecture/canonical-investment-flow.md", readme)

    def test_canonical_paths_exist(self) -> None:
        self.assertTrue((ROOT / "data" / "input_ledger").is_dir())
        self.assertTrue((ROOT / "data" / "benchmarks").is_dir())
        self.assertTrue((ROOT / "ontology" / "project.yaml").is_file())

    def test_superseded_weekly_research_workflow_is_absent(self) -> None:
        workflow = ROOT / ".github" / "workflows" / "weekly-repo-research.yml"
        self.assertFalse(workflow.exists(), "superseded weekly research workflow reintroduced")


if __name__ == "__main__":
    unittest.main()
