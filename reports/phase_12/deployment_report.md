# Phase 12 Deployment Report

## Outcome

FinAccess Eswatini is publicly deployed as one Vercel application. The selected Signal frontend posts one validated profile to a same-origin FastAPI route, which returns predictions and model-derived SHAP explanations from both independently validated models.

**Phase status: PASS WITH NOTES**

## Public endpoints

- Application: https://finaccess-eswatini.vercel.app
- API information: https://finaccess-eswatini.vercel.app/api
- Health and artifact integrity: https://finaccess-eswatini.vercel.app/api/health
- Interactive API documentation: https://finaccess-eswatini.vercel.app/api/docs
- Combined assessment: https://finaccess-eswatini.vercel.app/api/v1/assessment

Recruiters can open the application directly without a Vercel, Render, or OpenAI account.

## Architecture and reasoning

- Platform: One Vercel Hobby project using Vercel Services.
- Frontend: Next.js 16 Signal interface in the web service.
- API: FastAPI Python 3.13 inference service under /api.
- Inference: Two saved scikit-learn pipelines with model-matched SHAP explainers.
- Request flow: Browser -> same-origin /api route -> FastAPI -> both models.
- One shared domain removes the cross-host proxy, public API environment variable, and browser CORS dependency.
- Raw and processed respondent records remain outside the deployment repository. Only the six validated model/explainer artifacts and their metadata are published.
- Every pipeline and explainer digest is checked before the service reports healthy.

## Live validation

| Check | Result | Evidence |
|---|---|---|
| public_frontend_https | PASS | HTTP 200 at the production domain; Signal heading and developer credit found without an authentication redirect. |
| api_health_and_artifact_integrity | PASS | HTTP 200; two hash-matched model/explainer pairs are ready. |
| openapi_contract | PASS | HTTP 200; same-origin health and assessment paths present. |
| interactive_api_documentation | PASS | HTTP 200 at /api/docs. |
| combined_assessment | PASS | HTTP 200; one public request returned both outcomes. |
| validated_prediction_equivalence | PASS | Live probabilities and all local SHAP factors match the validated Phase 10 example. |
| explanation_factors | PASS | Model-derived explanation counts: {'financial_inclusion': 5, 'mobile_money_adoption': 5}. |
| invalid_input_rejected | PASS | Empty profile rejected with HTTP 422. |
| one_domain_no_cors_dependency | PASS | The browser and FastAPI routes share one HTTPS origin; CORS is not in the normal path. |
| vercel_services_configuration | PASS | Next.js and FastAPI are separate Vercel services with API-first routing. |
| no_external_api_dependency | PASS | Deployed routing and assessment source contain no Render, Sites, or external API URL. |
| public_access_without_project_auth | PASS | No ChatGPT sign-in module or OpenAI hosting manifest is tracked in the deployment repository. |
| microdata_publication_safety | PASS | No respondent-level dataset is tracked by the public deployment repository. |
| model_artifacts_published | PASS | 6/6 validated deployment artifacts tracked. |
| secret_file_safety | PASS | No live environment, private-key, or certificate file is tracked. |

## Production smoke-test example

- Financial inclusion: This person is unlikely to be financially included. (26.9%); 5 explanation factors.
- Mobile money: This person is unlikely to use mobile money. (36.8%); 5 explanation factors.

The example verifies the live path; it is not a general analytical finding. The input profile is documented in `api/examples/assessment_request.json`.

## Local regression gate

- Python project suite: 96 tests passed with no failures or errors.
- Deployment-package API suite: 4 tests passed.
- Frontend production dependency audit: 0 vulnerabilities.
- Frontend lint and Next.js production build: passed.
- Rendered frontend routes: 5/5 passed.

The machine-readable local record is in `regression_validation.json`.

## Risks and limitations

- Vercel Services and the Vercel Python runtime are beta features, so deployment regression checks remain important.
- The Python dependency bundle was optimized by Vercel at 434.92 MB; dependency growth should be monitored.
- Automatic Git deployments require granting the Vercel GitHub App access to the private web repository; the validated release was deployed with the authenticated CLI.
- Serverless cold-start time can vary, although the live path no longer depends on a Render free-service wake-up.
- This remains a portfolio proof of concept, not a production financial decision engine.

Latency values in `deployment_validation.json` are point-in-time observations, not a service-level commitment.

## Phase boundary

Phase 12 covers deployment configuration, hosting, security controls, and public smoke testing. Phase 13 portfolio polish has not been started.
