"""
Synthetic contract texts for the Legal Review environment.
Each contract is realistic but entirely fictional — no real parties or deals.
"""

CONTRACTS = {
    "saas_agreement_v1": {
        "title": "Software-as-a-Service Subscription Agreement",
        "text": """SOFTWARE-AS-A-SERVICE SUBSCRIPTION AGREEMENT

This Software-as-a-Service Subscription Agreement ("Agreement") is entered into as of the Effective Date by and between Nexus Analytics Corp., a Delaware corporation ("Provider"), and the entity identified in the Order Form ("Customer").

1. DEFINITIONS
"Order Form" means the document executed by both parties specifying the Services, subscription term, and fees.
"Services" means the cloud-based analytics platform made available by Provider under this Agreement.
"Customer Data" means all data submitted by Customer to the Services.

2. SERVICES
Provider grants Customer a non-exclusive, non-transferable, worldwide right to access and use the Services during the Subscription Term solely for Customer's internal business purposes.

3. FEES AND PAYMENT
Customer shall pay all fees specified in the Order Form within thirty (30) days of invoice. Provider may charge interest on overdue amounts at the rate of 1.5% per month or the highest rate permitted by law, whichever is lower. All fees are non-refundable.

4. CONFIDENTIALITY
Each party agrees to keep the other party's Confidential Information confidential using at least the same degree of care it uses to protect its own confidential information, but in no event less than reasonable care.

5. INTELLECTUAL PROPERTY
Provider retains all right, title, and interest in and to the Services. Customer retains all right, title, and interest in and to Customer Data. Customer grants Provider a limited license to use Customer Data solely to provide the Services.

6. INDEMNIFICATION
Customer shall indemnify, defend, and hold harmless Provider and its officers, directors, employees, and agents from and against any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable attorneys' fees) arising out of or related to: (a) Customer's use of the Services in violation of this Agreement; (b) Customer Data; or (c) Customer's violation of any applicable law or regulation. Provider shall indemnify Customer against third-party claims that the Services infringe any patent, copyright, or trademark, provided Customer gives Provider prompt written notice.

7. LIMITATION OF LIABILITY
IN NO EVENT SHALL PROVIDER BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES, INCLUDING LOSS OF PROFITS, REVENUE, DATA, OR GOODWILL, EVEN IF PROVIDER HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES. PROVIDER'S TOTAL LIABILITY ARISING OUT OF OR RELATED TO THIS AGREEMENT SHALL NOT EXCEED THE AMOUNTS PAID BY CUSTOMER IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.

8. TERMINATION
Either party may terminate this Agreement upon thirty (30) days written notice if the other party materially breaches this Agreement and fails to cure such breach within the notice period. Provider may immediately terminate this Agreement if Customer fails to pay any amounts due. Upon termination, Customer's right to access the Services ceases immediately.

9. DATA SECURITY
Provider shall implement and maintain commercially reasonable administrative, physical, and technical safeguards designed to protect Customer Data. In the event of a security breach affecting Customer Data, Provider shall notify Customer within seventy-two (72) hours of discovery.

10. GOVERNING LAW AND DISPUTE RESOLUTION
This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware, without regard to its conflict of law provisions. Any dispute arising hereunder shall be resolved by binding arbitration in Wilmington, Delaware under the rules of the American Arbitration Association.

11. AUTO-RENEWAL
This Agreement and each Order Form shall automatically renew for successive one-year periods unless either party provides written notice of non-renewal at least ninety (90) days before the end of the then-current term.

12. ENTIRE AGREEMENT
This Agreement constitutes the entire agreement between the parties and supersedes all prior agreements, representations, and understandings.
""",
        "ground_truth": {
            "clauses": [
                "definitions",
                "services_grant",
                "fees_and_payment",
                "confidentiality",
                "intellectual_property",
                "indemnification",
                "limitation_of_liability",
                "termination",
                "data_security",
                "governing_law",
                "auto_renewal",
                "entire_agreement"
            ],
            "risks": [
                {
                    "clause_reference": "fees_and_payment",
                    "severity": "medium",
                    "rationale": "All fees are stated as non-refundable with no exception for service outages or termination for cause, which disadvantages the customer.",
                    "keywords": ["non-refundable", "interest", "1.5%"]
                },
                {
                    "clause_reference": "indemnification",
                    "severity": "high",
                    "rationale": "Customer indemnity is broad (any violation of law, all customer data claims) while Provider indemnity is narrowly limited to IP infringement only, creating an asymmetric risk allocation.",
                    "keywords": ["indemnify", "asymmetric", "broad"]
                },
                {
                    "clause_reference": "limitation_of_liability",
                    "severity": "high",
                    "rationale": "The liability cap is limited to 12 months of fees, which may be inadequate for catastrophic data breaches, and the exclusion of consequential damages is one-sided.",
                    "keywords": ["limitation", "cap", "consequential", "one-sided"]
                },
                {
                    "clause_reference": "termination",
                    "severity": "medium",
                    "rationale": "Provider can terminate immediately for non-payment without cure period, leaving customer without service access and no data retrieval window.",
                    "keywords": ["immediately", "no cure", "data access"]
                },
                {
                    "clause_reference": "auto_renewal",
                    "severity": "low",
                    "rationale": "90-day notice window for non-renewal is longer than industry standard (30-60 days) and may be easy to miss.",
                    "keywords": ["auto-renewal", "90 days", "notice"]
                }
            ],
            "redlines": [
                {
                    "clause_reference": "limitation_of_liability",
                    "priority": 1,
                    "issue": "Cap too low; consequential damages exclusion one-sided",
                    "proposed_direction": "Raise cap to 24 months; mutual exclusion or carve-out for data breaches"
                },
                {
                    "clause_reference": "indemnification",
                    "priority": 2,
                    "issue": "Asymmetric indemnification",
                    "proposed_direction": "Narrow customer indemnity to gross negligence/willful misconduct; broaden provider indemnity"
                },
                {
                    "clause_reference": "termination",
                    "priority": 3,
                    "issue": "No cure period for non-payment; no data retrieval window",
                    "proposed_direction": "Add 10-day cure period; guarantee 30-day data export window post-termination"
                },
                {
                    "clause_reference": "fees_and_payment",
                    "priority": 4,
                    "issue": "Non-refundable fees with no exceptions",
                    "proposed_direction": "Add pro-rata refund right for termination for cause and material SLA breach"
                },
                {
                    "clause_reference": "auto_renewal",
                    "priority": 5,
                    "issue": "90-day notice too long",
                    "proposed_direction": "Reduce to 30 days written notice"
                }
            ]
        }
    },

    "nda_simple": {
        "title": "Mutual Non-Disclosure Agreement",
        "text": """MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of January 15, 2024, between Acme Ventures LLC ("Party A") and Brightstone Technologies Inc. ("Party B").

1. PURPOSE
The parties wish to explore a potential business relationship (the "Purpose") and may disclose confidential information to each other.

2. CONFIDENTIAL INFORMATION
"Confidential Information" means any non-public information disclosed by one party to the other, whether oral, written, or electronic, that is designated as confidential or that reasonably should be understood to be confidential given the context.

3. OBLIGATIONS
Each party agrees to: (a) hold the other party's Confidential Information in strict confidence; (b) not disclose such information to third parties without prior written consent; (c) use the Confidential Information only for the Purpose.

4. EXCLUSIONS
Obligations do not apply to information that: (a) is or becomes publicly known through no breach of this Agreement; (b) was already known to the receiving party; (c) is independently developed; (d) is required to be disclosed by law.

5. TERM
This Agreement is effective for two (2) years from the Effective Date.

6. RETURN OF INFORMATION
Upon request, each party shall promptly return or destroy all Confidential Information.

7. GOVERNING LAW
This Agreement shall be governed by the laws of New York.
""",
        "ground_truth": {
            "clauses": [
                "purpose",
                "confidential_information_definition",
                "obligations",
                "exclusions",
                "term",
                "return_of_information",
                "governing_law"
            ],
            "risks": [
                {
                    "clause_reference": "term",
                    "severity": "medium",
                    "rationale": "Two-year confidentiality period may be insufficient for trade secrets; standard is 3-5 years or indefinite for trade secrets.",
                    "keywords": ["two years", "term", "expiry"]
                },
                {
                    "clause_reference": "confidential_information_definition",
                    "severity": "low",
                    "rationale": "Definition includes oral disclosures without a confirmation requirement, which creates evidentiary uncertainty about what was actually disclosed.",
                    "keywords": ["oral", "designation", "uncertainty"]
                }
            ],
            "redlines": [
                {
                    "clause_reference": "term",
                    "priority": 1,
                    "issue": "Short term",
                    "proposed_direction": "Extend to 5 years with indefinite protection for trade secrets"
                },
                {
                    "clause_reference": "confidential_information_definition",
                    "priority": 2,
                    "issue": "Oral disclosures unclear",
                    "proposed_direction": "Require written confirmation within 10 business days for oral disclosures"
                }
            ]
        }
    }
}

# Task-to-contract mapping
TASK_CONTRACTS = {
    "clause_identification": "nda_simple",
    "risk_flagging": "saas_agreement_v1",
    "negotiation_strategy": "saas_agreement_v1"
}
