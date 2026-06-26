import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


class TestDeployWorkflow(unittest.TestCase):
    def test_deploy_workflow_tears_down_existing_compose_stack_before_up(self):
        workflow = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

        down_cmd = "docker compose down --remove-orphans"
        up_cmd = "docker compose up -d --force-recreate"

        self.assertIn(down_cmd, workflow)
        self.assertIn(up_cmd, workflow)
        self.assertLess(workflow.index(down_cmd), workflow.index(up_cmd))


if __name__ == "__main__":
    unittest.main()
