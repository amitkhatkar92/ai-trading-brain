import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


class TestDeployWorkflow(unittest.TestCase):
    def extract_deploy_script(self, workflow: str) -> str:
        lines = workflow.splitlines()

        deploy_step_idx = next(
            (i for i, line in enumerate(lines) if line.strip() == "- name: Deploy to VPS"),
            None,
        )
        self.assertIsNotNone(deploy_step_idx, "Missing 'Deploy to VPS' workflow step")

        script_idx = next(
            (i for i in range(deploy_step_idx + 1, len(lines)) if lines[i].strip() == "script: |"),
            None,
        )
        self.assertIsNotNone(script_idx, "Missing 'script: |' block in deploy step")

        script_indent = len(lines[script_idx]) - len(lines[script_idx].lstrip(" "))
        script_lines = []
        for line in lines[script_idx + 1 :]:
            if not line.strip():
                script_lines.append("")
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent <= script_indent:
                break
            script_lines.append(line.strip())

        return "\n".join(script_lines)

    def test_deploy_workflow_tears_down_existing_compose_stack_before_up(self):
        workflow = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
        deploy_script = self.extract_deploy_script(workflow)

        down_cmd = "docker compose down --remove-orphans"
        up_cmd = "docker compose up -d --force-recreate --remove-orphans"

        down_pos = deploy_script.find(down_cmd)
        up_pos = deploy_script.find(up_cmd)

        self.assertGreaterEqual(down_pos, 0, f"Missing workflow command: {down_cmd}")
        self.assertGreaterEqual(up_pos, 0, f"Missing workflow command: {up_cmd}")
        self.assertLess(
            down_pos,
            up_pos,
            "docker compose down must execute before up to prevent race conditions",
        )
        self.assertRegex(deploy_script, r"max_deploy_attempts=\d+")
        self.assertIn("for deploy_attempt in $(seq 1 \"$max_deploy_attempts\")", deploy_script)
        self.assertIn("docker compose up -d --force-recreate --remove-orphans", deploy_script)


if __name__ == "__main__":
    unittest.main()
