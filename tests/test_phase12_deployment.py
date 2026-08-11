from __future__ import annotations

import json
import unittest
from pathlib import Path

from finaccess_eswatini.phase12_deployment import (
    API_BASE_URL,
    DEPLOYMENT_REPOSITORY,
    FRONTEND_BASE_URL,
    PUBLIC_BASE_URL,
    _check,
    _deployed_source_has_external_api_dependency,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Phase12DeploymentConfigurationTests(unittest.TestCase):
    def test_vercel_services_host_web_and_fastapi_under_one_domain(self) -> None:
        config = json.loads((DEPLOYMENT_REPOSITORY / "vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(config["services"]["web"], {"root": "web/", "framework": "nextjs"})
        self.assertEqual(
            config["services"]["backend"],
            {"root": "backend/", "framework": "fastapi", "entrypoint": "main:app"},
        )
        self.assertEqual(
            config["rewrites"][0],
            {"source": "/api/(.*)", "destination": {"service": "backend"}},
        )
        self.assertEqual(
            config["rewrites"][1],
            {"source": "/(.*)", "destination": {"service": "web"}},
        )

    def test_deployed_frontend_has_no_external_api_dependency(self) -> None:
        self.assertFalse(_deployed_source_has_external_api_dependency())
        self.assertFalse((PROJECT_ROOT / "render.yaml").exists())
        self.assertFalse((DEPLOYMENT_REPOSITORY / "web" / "app" / "chatgpt-auth.ts").exists())

    def test_environment_template_contains_only_a_placeholder(self) -> None:
        root_env = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("FINACCESS_CORS_ORIGINS", root_env)
        self.assertIn("your-frontend.example", root_env)
        self.assertNotIn("onrender.com", root_env)
        self.assertFalse((DEPLOYMENT_REPOSITORY / ".env.example").exists())
        self.assertFalse((DEPLOYMENT_REPOSITORY / "web" / ".env.example").exists())

    def test_publication_rules_protect_raw_and_processed_microdata(self) -> None:
        ignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/raw/*", ignore)
        self.assertIn("data/processed/*", ignore)
        self.assertIn("!models/model1_financial_inclusion_pipeline.joblib", ignore)
        self.assertIn("!models/model2_shap_explainer.joblib", ignore)

    def test_production_frontend_and_api_share_one_https_origin(self) -> None:
        self.assertEqual(PUBLIC_BASE_URL, "https://finaccess-eswatini.vercel.app")
        self.assertEqual(API_BASE_URL, PUBLIC_BASE_URL)
        self.assertEqual(FRONTEND_BASE_URL, PUBLIC_BASE_URL)

    def test_check_record_is_machine_readable(self) -> None:
        self.assertEqual(
            _check("example", True, "Evidence."),
            {"check": "example", "status": "PASS", "evidence": "Evidence."},
        )

    def test_phase12_runner_and_notebook_builder_exist(self) -> None:
        self.assertTrue((PROJECT_ROOT / "scripts" / "run_phase12_deployment.ps1").is_file())
        self.assertTrue((PROJECT_ROOT / "scripts" / "build_phase12_notebook.py").is_file())


if __name__ == "__main__":
    unittest.main()
