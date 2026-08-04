"""Canonical KPI framework from KPI_Scoring_Dashboard.xlsx.

Five weighted categories (weights sum to 100). Each category's points are split
equally across its active KPIs. A KPI is scored Met / Partial / Not Met.
Imported by migration 0005 and the test seeding so they never drift.
"""

# (name, weight) — weights sum to 100
CATEGORIES: list[tuple[str, str]] = [
    ("Performance & Delivery", "35.00"),
    ("Collaboration & Team Engagement", "20.00"),
    ("Ownership & Initiative", "20.00"),
    ("Learning & Growth", "15.00"),
    ("Business & Impact Alignment", "10.00"),
]

# (category, name, description, measurement, target)
KPIS: list[tuple[str, str, str, str, str]] = [
    # Performance & Delivery (35)
    (
        "Performance & Delivery",
        "Task Completion Rate",
        "Percentage of assigned tasks completed within agreed timelines",
        "(# completed on time / total assigned) x 100",
        "≥ 90%",
    ),
    (
        "Performance & Delivery",
        "Quality of Output",
        "Accuracy, attention to detail, and adherence to standards",
        "% of work approved without revisions",
        "≥ 95%",
    ),
    (
        "Performance & Delivery",
        "Process Efficiency",
        "Ability to complete tasks with minimal rework",
        "# of reworks per project or task",
        "≤ 10%",
    ),
    (
        "Performance & Delivery",
        "Documentation & Compliance",
        "Following team processes, SOPs, and file protocols",
        "Audit or lead review",
        "Full compliance",
    ),
    # Collaboration & Team Engagement (20)
    (
        "Collaboration & Team Engagement",
        "Cross-Team Communication",
        "Timely, professional interaction with colleagues and other teams",
        "Peer feedback survey",
        "≥ 4/5",
    ),
    (
        "Collaboration & Team Engagement",
        "Meeting Participation",
        "Attendance and constructive contribution in meetings",
        "Attendance record + feedback",
        "≥ 90% participation",
    ),
    (
        "Collaboration & Team Engagement",
        "Collaboration Quality",
        "How effectively the member works with others to achieve shared goals",
        "360° feedback",
        "Positive trend",
    ),
    (
        "Collaboration & Team Engagement",
        "Team Morale Contribution",
        "Proactive positivity, mentorship, or support of peers",
        "Peer/lead feedback",
        "Demonstrated contribution",
    ),
    # Ownership & Initiative (20)
    (
        "Ownership & Initiative",
        "Accountability",
        "Consistency in following through on commitments",
        "Manager review + peer inputs",
        "Consistent accountability",
    ),
    (
        "Ownership & Initiative",
        "Problem Solving",
        "Identifies and resolves issues proactively",
        "# of issues resolved without escalation",
        "≥ 80%",
    ),
    (
        "Ownership & Initiative",
        "Innovation & Continuous Improvement",
        "Suggestions, ideas, or efficiencies introduced",
        "# of improvements suggested or implemented",
        "≥ 1 per quarter",
    ),
    (
        "Ownership & Initiative",
        "Dependability Index",
        "Reliability under deadlines or pressure",
        "Lead assessment",
        "Above Average",
    ),
    # Learning & Growth (15)
    (
        "Learning & Growth",
        "Skill Advancement",
        "Participation in internal/external learning activities",
        "# of trainings, courses, or certifications completed",
        "≥ 1 per quarter",
    ),
    (
        "Learning & Growth",
        "Application of Learning",
        "Using new skills in actual work scenarios",
        "Evidence of application in deliverables",
        "Demonstrated improvement",
    ),
    (
        "Learning & Growth",
        "Growth Goal Achievement",
        "Progress toward individual development plans",
        "% of personal goals met",
        "≥ 80%",
    ),
    (
        "Learning & Growth",
        "Knowledge Sharing",
        "Teaching or mentoring others on new skills",
        "# of sessions, guides, or shared learnings",
        "≥ 1 per quarter",
    ),
    # Business & Impact Alignment (10)
    (
        "Business & Impact Alignment",
        "Impact on KPIs",
        "Contribution to key company/team metrics",
        "Direct link to department KPIs",
        "Documented alignment",
    ),
    (
        "Business & Impact Alignment",
        "Customer or Stakeholder Feedback",
        "External feedback on professionalism, quality, or communication",
        "Client or stakeholder rating",
        "≥ 4/5",
    ),
    (
        "Business & Impact Alignment",
        "Efficiency Contribution",
        "Ideas or efforts that saved time, cost, or resources",
        "Quantified impact or manager validation",
        "≥ 1 measurable improvement/quarter",
    ),
    (
        "Business & Impact Alignment",
        "Strategic Alignment",
        "Understanding and acting in line with company goals",
        "Leadership evaluation",
        "Strong alignment",
    ),
]
