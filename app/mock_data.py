"""
Mock data for cognitive engine fallback scenarios
Separates mock data from business logic for better maintainability
"""

MOCK_KNOWLEDGE_BASE = {
    "flood": [
        {
            "content": (
                "Properties located in Special Flood Hazard Areas (SFHA) require elevation "
                "certificates. The lowest floor must be elevated to or above "
                "Base Flood Elevation (BFE)."
            ),
            "modality": "text",
            "relevance": 0.92,
            "evidence_strength": "mandatory",
            "source": "mock"
        }
    ],
    "wildfire": [
        {
            "content": (
                "Properties within 100 feet of wildland vegetation interface must have "
                "defensible space. Clear vegetation within 30 feet of structure "
                "and reduce fuel loads up to 100 feet."
            ),
            "modality": "text",
            "relevance": 0.94,
            "evidence_strength": "required",
            "source": "mock"
        }
    ],
    "age": [
        {
            "content": (
                "Dwellings over 50 years old may require additional underwriting "
                "review. Foundation condition and roof age are critical factors "
                "for older properties."
            ),
            "modality": "text",
            "relevance": 0.87,
            "evidence_strength": "recommended",
            "source": "mock"
        }
    ],
    "default": [
        {
            "content": (
                "Underwriting guidelines for residential properties in California"
            ),
            "modality": "text",
            "relevance": 0.85,
            "evidence_strength": "required",
            "source": "mock"
        }
    ],
}


def get_mock_results(query: str, context: dict) -> list:
    """
    Get mock search results based on query keywords

    Args:
        query: Search query string
        context: Underwriting context

    Returns:
        List of mock search results
    """
    query_lower = query.lower()

    # Check for keyword matches
    for keyword, results in MOCK_KNOWLEDGE_BASE.items():
        if keyword != "default" and keyword in query_lower:
            return results

    # Return default results if no keyword match
    default_results = MOCK_KNOWLEDGE_BASE["default"].copy()
    default_results[0]["content"] = (
        f"Underwriting guidelines for {context.get('property_type', 'residential')} "
        f"properties in {context.get('location', 'California')}"
    )
    return default_results
