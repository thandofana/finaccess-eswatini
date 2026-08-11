from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from api.app.main import app
from api.app.service import (
    ArtifactIntegrityError,
    InferenceError,
    get_prediction_service,
)
from finaccess_eswatini.data_audit import PROJECT_ROOT
from finaccess_eswatini.phase9_explainability import SPECS
from finaccess_eswatini.phase10_api_validation import DEFAULT_OUTPUT_DIR


EXAMPLE_REQUEST = PROJECT_ROOT / "api" / "examples" / "assessment_request.json"
EXAMPLE_RESPONSE = PROJECT_ROOT / "api" / "examples" / "assessment_response.json"


class Phase10ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(EXAMPLE_REQUEST.read_text(encoding="utf-8"))
        cls.summary = json.loads((DEFAULT_OUTPUT_DIR / "phase10_summary.json").read_text(encoding="utf-8"))
        cls.client_context = TestClient(app, raise_server_exceptions=False)
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()
        cls.client_context.__exit__(None, None, None)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_health_verifies_both_model_and_explainer_pairs(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "healthy")
        self.assertEqual({item["target"] for item in body["models"]}, {"account_fin", "account_mob"})
        for item, spec in zip(body["models"], SPECS, strict=True):
            self.assertEqual(item["pipeline_sha256"], spec.expected_sha256)
            self.assertEqual(len(item["explainer_sha256"]), 64)

    def test_one_request_returns_two_clear_model_derived_results(self) -> None:
        response = self.client.post("/api/v1/assessment", json=self.payload)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("financially included", body["financial_inclusion"]["question"])
        self.assertIn("mobile money", body["mobile_money_adoption"]["question"])
        for key in ("financial_inclusion", "mobile_money_adoption"):
            result = body[key]
            self.assertRegex(result["answer"], r"^This person is (un)?likely")
            self.assertAlmostEqual(result["probability_percent"], round(result["probability"] * 100, 1))
            self.assertEqual(result["threshold"], 0.5)
            self.assertEqual(result["threshold_status"], "provisional")
            self.assertEqual(len(result["main_factors"]), 5)
            magnitudes = [abs(factor["contribution_log_odds"]) for factor in result["main_factors"]]
            self.assertTrue(all(left >= right for left, right in zip(magnitudes, magnitudes[1:])))
            for factor in result["main_factors"]:
                expected = "increased_likelihood" if factor["contribution_log_odds"] > 0 else "reduced_likelihood"
                self.assertEqual(factor["direction"], expected)

    def test_api_probabilities_match_direct_cached_service(self) -> None:
        api_response = self.client.post("/api/v1/assessment", json=self.payload).json()
        from api.app.schemas import AssessmentRequest

        direct = get_prediction_service().assess(AssessmentRequest.model_validate(self.payload), "test").model_dump()
        self.assertAlmostEqual(
            api_response["financial_inclusion"]["probability"],
            direct["financial_inclusion"]["probability"],
            places=12,
        )
        self.assertAlmostEqual(
            api_response["mobile_money_adoption"]["probability"],
            direct["mobile_money_adoption"]["probability"],
            places=12,
        )
        self.assertIs(get_prediction_service(), get_prediction_service())

    def test_invalid_category_missing_extra_and_inconsistent_inputs_are_422(self) -> None:
        payloads = []
        payloads.append(dict(self.payload, female="Unknown"))
        missing = dict(self.payload)
        missing.pop("educ")
        payloads.append(missing)
        payloads.append(dict(self.payload, target="account_fin"))
        payloads.append(dict(self.payload, internet_engagement_level="Daily internet use"))
        payloads.append(dict(self.payload, phone_access_tier="No personal mobile phone"))
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.post("/api/v1/assessment", json=payload)
                self.assertEqual(response.status_code, 422)
                error = response.json()["error"]
                self.assertEqual(error["code"], "VALIDATION_ERROR")
                self.assertTrue(error["details"])
                self.assertNotIn("input", error["details"][0])

    def test_legitimate_category_unseen_by_one_training_encoder_is_disclosed(self) -> None:
        payload = dict(self.payload, con12="Never")
        response = self.client.post("/api/v1/assessment", json=payload)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(any("con12='Never'" in warning for warning in result["financial_inclusion"]["warnings"]))
        self.assertEqual(result["mobile_money_adoption"]["warnings"], [])

    def test_openapi_contract_documents_request_and_responses(self) -> None:
        document = self.client.get("/openapi.json").json()
        operation = document["paths"]["/api/v1/assessment"]["post"]
        self.assertEqual(set(operation["responses"]), {"200", "422", "500", "503"})
        request_schema = document["components"]["schemas"]["AssessmentRequest"]
        self.assertEqual(len(request_schema["required"]), 17)
        self.assertFalse(request_schema["additionalProperties"])
        self.assertIn("examples", request_schema)

    def test_inference_and_artifact_failures_are_sanitized(self) -> None:
        class BrokenInferenceService:
            def assess(self, _request):
                raise InferenceError("private diagnostic")

        app.dependency_overrides[get_prediction_service] = lambda: BrokenInferenceService()
        response = self.client.post("/api/v1/assessment", json=self.payload)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "INFERENCE_ERROR")
        self.assertNotIn("private diagnostic", response.text)

        def broken_artifacts():
            raise ArtifactIntegrityError("private path")

        app.dependency_overrides[get_prediction_service] = broken_artifacts
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "SERVICE_NOT_READY")
        self.assertNotIn("private path", response.text)

    def test_example_reports_and_scope_guards(self) -> None:
        self.assertTrue(EXAMPLE_RESPONSE.is_file())
        response = json.loads(EXAMPLE_RESPONSE.read_text(encoding="utf-8"))
        self.assertEqual(response["assessment_id"], "phase10-validated-example")
        self.assertTrue((DEFAULT_OUTPUT_DIR / "endpoint_contract.json").is_file())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "validation_cases.csv").is_file())
        self.assertTrue((DEFAULT_OUTPUT_DIR / "api_report.md").is_file())
        self.assertEqual(self.summary["validation_cases"], self.summary["validation_cases_passed"])
        self.assertFalse(self.summary["profiles_persisted"])
        self.assertFalse(self.summary["cors_configured"])
        self.assertFalse(self.summary["deployment_started"])
        self.assertFalse(self.summary["frontend_started"])
        self.assertTrue(self.summary["deliverable_validation"]["passed"])


if __name__ == "__main__":
    unittest.main()
