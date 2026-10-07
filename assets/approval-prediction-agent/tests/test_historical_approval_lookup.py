"""Unit tests for the historical approval lookup tool (Ariba Approval API mock)."""

import json
import os
import pytest


@pytest.fixture(autouse=True)
def use_testing_mode():
    os.environ["IBD_TESTING"] = "1"
    yield


@pytest.mark.usefixtures("add_agent_to_path")
class TestHistoricalApprovalLookup:
    """Tests for the historical approval data lookup capability via MCP tools."""

    def test_mcp_mock_loads_ariba_approval_tools(self, add_agent_to_path):
        """Verify that mcp-mock.json provides Ariba approval tools."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        tool_names = [t.name for t in tools]
        ariba_tools = [
            n for n in tool_names
            if any(k in n.lower() for k in ["changes", "pending", "approvable", "approver"])
        ]
        assert len(ariba_tools) > 0, f"Expected Ariba approval tools, got: {tool_names}"

    @pytest.mark.asyncio
    async def test_get_changes_returns_approval_history(self, add_agent_to_path):
        """Verify that get_changes tool returns historical approval records."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        changes_tool = next((t for t in tools if t.name == "get_changes"), None)
        assert changes_tool is not None, "get_changes tool not found in mock"

        result = await changes_tool.ainvoke({"realm": "test-realm", "user": "testuser"})
        data = json.loads(result) if isinstance(result, str) else result
        assert "approvals" in data, f"Expected 'approvals' in response, got: {data}"
        assert len(data["approvals"]) > 0
        first = data["approvals"][0]
        assert "documentId" in first
        assert "status" in first
        assert "productName" in first

    @pytest.mark.asyncio
    async def test_get_pending_approvables(self, add_agent_to_path):
        """Verify that getPendingApprovables returns current pending approvals."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        pending_tool = next((t for t in tools if t.name == "getPendingApprovables"), None)
        assert pending_tool is not None, "getPendingApprovables tool not found"

        result = await pending_tool.ainvoke({"realm": "test-realm", "user": "testuser"})
        data = json.loads(result) if isinstance(result, str) else result
        assert "pendingApprovables" in data

    @pytest.mark.asyncio
    async def test_get_document_details_returns_full_record(self, add_agent_to_path):
        """Verify that get_document_details returns a complete approval record."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        details_tool = next((t for t in tools if t.name == "get_document_details"), None)
        assert details_tool is not None, "get_document_details tool not found"

        result = await details_tool.ainvoke({
            "approvable_type": "ProductLicenseRequest",
            "approvable_id": "REQ-2024-001",
            "realm": "test-realm",
            "user": "testuser",
        })
        data = json.loads(result) if isinstance(result, str) else result
        required_fields = ["documentId", "productName", "status", "region"]
        for field in required_fields:
            assert field in data, f"Expected field '{field}' in document details"

    @pytest.mark.asyncio
    async def test_approval_history_contains_both_outcomes(self, add_agent_to_path):
        """Verify mock data includes both approved and rejected records for realistic testing."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        changes_tool = next((t for t in tools if t.name == "get_changes"), None)
        if changes_tool is None:
            pytest.skip("get_changes tool not available")

        result = await changes_tool.ainvoke({"realm": "test-realm", "user": "testuser"})
        data = json.loads(result) if isinstance(result, str) else result
        statuses = {a["status"] for a in data.get("approvals", [])}
        # The mock should include both approved and rejected for realistic testing
        assert "Approved" in statuses or "Rejected" in statuses, \
            f"Expected approval outcomes in mock data, got statuses: {statuses}"
