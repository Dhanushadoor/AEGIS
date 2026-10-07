"""Unit tests for the regulatory data check tool (via MCP mock)."""

import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.tools import StructuredTool


@pytest.fixture(autouse=True)
def use_testing_mode():
    """Ensure IBD_TESTING is set for all tests in this module."""
    os.environ["IBD_TESTING"] = "1"
    yield


@pytest.mark.usefixtures("add_agent_to_path")
class TestRegulatoryDataCheck:
    """Tests for the regulatory data check capability via MCP tools."""

    def test_mcp_mock_loads_regulatory_tools(self, add_agent_to_path):
        """Verify that mcp-mock.json provides regulatory data tools."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        assert len(tools) > 0, "Expected at least one mock tool to be loaded"

        tool_names = [t.name for t in tools]
        # Verify regulatory data tools are present
        assert any(
            "regulatorydataassessment" in name.lower() or "regulatory" in name.lower()
            for name in tool_names
        ), f"Expected at least one regulatory assessment tool, got: {tool_names}"

    @pytest.mark.asyncio
    async def test_list_regulatory_assessments_returns_results(self, add_agent_to_path):
        """Verify that the list_regulatorydataassessment tool returns structured mock data."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        list_tool = next(
            (t for t in tools if "list_regulatorydataassessment" in t.name), None
        )
        assert list_tool is not None, "list_regulatorydataassessment tool not found in mock"

        result = await list_tool.ainvoke({})
        assert result is not None
        # The mock returns a JSON string with results
        import json
        data = json.loads(result) if isinstance(result, str) else result
        assert "results" in data, f"Expected 'results' key in response, got: {data}"
        assert len(data["results"]) > 0, "Expected at least one regulatory assessment"
        first = data["results"][0]
        assert "ProductName" in first
        assert "ComplianceStatus" in first
        assert "AssessmentResult" in first

    @pytest.mark.asyncio
    async def test_get_regulatory_assessment_by_key(self, add_agent_to_path):
        """Verify that get_regulatorydataassessment tool returns a single entity."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        get_tool = next(
            (t for t in tools if t.name.startswith("get_regulatorydataassessment")),
            None,
        )
        assert get_tool is not None, "get_regulatorydataassessment tool not found"

        result = await get_tool.ainvoke({"ComplianceRequirementUUID": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"})
        import json
        data = json.loads(result) if isinstance(result, str) else result
        assert "ComplianceRequirementUUID" in data
        assert "ProductName" in data

    @pytest.mark.asyncio
    async def test_regulatory_assessment_data_structure(self, add_agent_to_path):
        """Verify that regulatory assessment mock data contains required fields."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        list_tool = next(
            (t for t in tools if "list_regulatorydataassessment" in t.name), None
        )
        if list_tool is None:
            pytest.skip("list_regulatorydataassessment tool not available")

        result = await list_tool.ainvoke({})
        import json
        data = json.loads(result) if isinstance(result, str) else result
        required_fields = ["ProductName", "ComplianceStatus", "AssessmentResult"]
        for item in data.get("results", []):
            for field in required_fields:
                assert field in item, f"Expected field '{field}' in regulatory assessment item"
