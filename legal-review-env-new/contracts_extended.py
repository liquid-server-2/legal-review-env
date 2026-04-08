"""
Additional contract: Employment Agreement with IP assignment clauses.
Used for future task expansion and contract variety testing.
"""

EMPLOYMENT_CONTRACT = {
    "title": "Executive Employment Agreement",
    "text": """EXECUTIVE EMPLOYMENT AGREEMENT

This Executive Employment Agreement ("Agreement") is made as of March 1, 2024, between Horizon Technologies Inc., a California corporation ("Company"), and the individual identified in Schedule A ("Executive").

1. POSITION AND DUTIES
Executive shall serve as Chief Technology Officer, reporting to the Chief Executive Officer. Executive shall devote substantially all of Executive's business time and attention to the Company's business.

2. COMPENSATION
(a) Base Salary: $280,000 per annum, payable in accordance with the Company's standard payroll practices.
(b) Annual Bonus: Executive shall be eligible for an annual performance bonus of up to 30% of Base Salary, at the Board's sole and absolute discretion.
(c) Equity: Executive shall receive stock options covering 0.5% of the Company's fully diluted shares, vesting over four years with a one-year cliff.

3. BENEFITS
Executive shall be entitled to participate in the Company's standard employee benefit plans, including health insurance, dental, and vision coverage, subject to the terms of such plans.

4. CONFIDENTIALITY
Executive acknowledges that in the course of employment, Executive will have access to the Company's trade secrets and confidential information. Executive agrees to maintain the confidentiality of such information both during and after employment, without temporal limitation.

5. INTELLECTUAL PROPERTY ASSIGNMENT
Executive hereby irrevocably assigns to the Company all right, title, and interest in any inventions, discoveries, developments, improvements, or innovations conceived, developed, or reduced to practice by Executive, whether alone or jointly, during Executive's employment and for a period of one (1) year thereafter, that relate to the Company's current or anticipated business. This assignment applies regardless of whether such work was performed during or outside normal business hours or using Company resources.

6. NON-COMPETE
During the term of employment and for a period of twenty-four (24) months thereafter, Executive shall not directly or indirectly engage in any business that competes with the Company's business within the United States.

7. NON-SOLICITATION
For a period of twenty-four (24) months following termination, Executive shall not solicit any employee, consultant, or customer of the Company.

8. TERMINATION
(a) At-Will: Either party may terminate this Agreement at any time, with or without cause, upon thirty (30) days written notice.
(b) For Cause: The Company may terminate Executive immediately for Cause, defined as material breach, fraud, felony conviction, or repeated failure to perform duties after written warning.
(c) Severance: If terminated without Cause, Executive shall receive three (3) months base salary as severance, conditioned on execution of a release.

9. GOVERNING LAW
This Agreement shall be governed by California law. Any disputes shall be resolved in the state or federal courts of Santa Clara County, California.
""",
    "ground_truth": {
        "clauses": [
            "position_and_duties",
            "compensation",
            "benefits",
            "confidentiality",
            "intellectual_property_assignment",
            "non_compete",
            "non_solicitation",
            "termination",
            "governing_law"
        ],
        "risks": [
            {
                "clause_reference": "intellectual_property_assignment",
                "severity": "high",
                "rationale": "Overly broad IP assignment captures work done outside business hours unrelated to company, and extends one year post-employment — likely unenforceable in California but still a red flag.",
                "keywords": ["irrevocably", "one year", "outside business hours", "assigns"]
            },
            {
                "clause_reference": "non_compete",
                "severity": "high",
                "rationale": "24-month nationwide non-compete is unenforceable in California under Business & Professions Code 16600, but creates chilling effect and litigation risk.",
                "keywords": ["non-compete", "24 months", "United States", "unenforceable"]
            },
            {
                "clause_reference": "compensation",
                "severity": "medium",
                "rationale": "Annual bonus is at Board's 'sole and absolute discretion' with no performance metrics defined, giving executive no enforceable right to bonus.",
                "keywords": ["sole discretion", "bonus", "no metrics"]
            },
            {
                "clause_reference": "termination",
                "severity": "medium",
                "rationale": "Severance of only 3 months is below market for CTO-level executive; conditioned on release creates pressure to waive claims.",
                "keywords": ["3 months", "severance", "conditioned", "release"]
            }
        ],
        "redlines": [
            {
                "clause_reference": "intellectual_property_assignment",
                "priority": 1,
                "issue": "Overbroad, captures personal projects",
                "proposed_direction": "Limit to IP conceived using Company resources or relating to current actual business; remove post-employment tail or reduce to 6 months"
            },
            {
                "clause_reference": "non_compete",
                "priority": 2,
                "issue": "Unenforceable and overbroad",
                "proposed_direction": "Delete entirely (void under CA law) or narrow to specific named competitors for 6 months"
            },
            {
                "clause_reference": "compensation",
                "priority": 3,
                "issue": "Bonus fully discretionary",
                "proposed_direction": "Define objective performance metrics tied to 50% of bonus; guaranteed minimum 50% if metrics met"
            },
            {
                "clause_reference": "termination",
                "priority": 4,
                "issue": "Severance too low, release condition",
                "proposed_direction": "Increase to 6 months; allow 21-day review and 7-day revocation period for release per ADEA"
            }
        ]
    }
}
