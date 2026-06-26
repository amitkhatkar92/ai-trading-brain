import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


class TestDeployWorkflow(unittest.TestCase):
    def test_deploy_workflow_tears_down_existing_compose_stack_before_up(self):
        workflow = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
        deploy_step_match = re.search(
            r"- name: Deploy to VPS.*?script: \|\n(?P<script>(?:\s{12,}.*\n)+)",
            workflow,
            re.DOTALL,
        )

        down_cmd = "docker compose down --remove-orphans"
        up_cmd = "docker compose up -d --force-recreate --remove-orphans"

        self.assertIsNotNone(deploy_step_match, "Missing 'Deploy to VPS' workflow step")
        deploy_script = deploy_step_match.group("script")

        down_pos = deploy_script.find(down_cmd)
        up_pos = deploy_script.find(up_cmd)

        self.assertGreaterEqual(down_pos, 0, f"Missing workflow command: {down_cmd}")
        self.assertGreaterEqual(up_pos, 0, f"Missing workflow command: {up_cmd}")
        self.assertLess(down_pos, up_pos)
        self.assertIn("max_deploy_attempts=3", deploy_script)
        self.assertIn("until docker compose up -d --force-recreate --remove-orphans; do", deploy_script)


if __name__ == "__main__":
    unittest.main()
