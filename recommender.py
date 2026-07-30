"""Stand-in for the proprietary SLM + RAG pipeline (docs/architecture/07).

This rule-based stub exists so the API's contract — an AI recommendation
with citations that always requires human approval — is exercised
end-to-end without standing up GPU inference. Swapping this function's
body for a real RAG call to a served SLM does not change any caller.
"""

HIGH_RISK_COUNTRIES = {"KP", "IR", "MM"}  # illustrative FATF-grey/black-list stand-in


def recommend(customer_country: str, customer_type: str) -> dict:
    if customer_country in HIGH_RISK_COUNTRIES:
        return {
            "decision": "escalate_edd",
            "risk_tier": "high",
            "confidence": 0.81,
            "rationale": (
                f"Customer's declared country ({customer_country}) is on the tenant's "
                "high-risk country list, meeting the criteria for mandatory Enhanced "
                "Due Diligence."
            ),
            "citations": [
                {
                    "sourceType": "policy_clause",
                    "clauseRef": "AML-Policy v1 §4.2 (stub)",
                    "snippet": "Customers incorporated in a high-risk jurisdiction require EDD prior to onboarding approval.",
                }
            ],
        }
    return {
        "decision": "approve",
        "risk_tier": "low",
        "confidence": 0.92,
        "rationale": "No high-risk indicators found in declared customer attributes.",
        "citations": [
            {
                "sourceType": "policy_clause",
                "clauseRef": "AML-Policy v1 §3.1 (stub)",
                "snippet": "Standard due diligence applies where no high-risk indicators are present.",
            }
        ],
    }
