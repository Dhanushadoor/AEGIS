"""Integration tests for end-to-end agent flow and iterative re-assessment."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def use_testing_mode():
    os.environ["IBD_TESTING"] = "1"
    yield


@pytest.mark.usefixtures("add_agent_to_path")
class TestEndToEndApprovalPrediction:
    """End-to-end integration tests for the approval prediction agent."""

    @pytest.mark.asyncio
    async def test_full_assessment_flow_approved(self, add_agent_to_path):
        """
        Integration test: user provides request details → agent confirms parameters →
        agent runs assessment → returns Approved verdict with confidence score.
        """
        from agent import SampleAgent, AgentResponse

        agent = SampleAgent()

        approved_response = (
            "I have confirmed the following request parameters:\n"
            "- Product: SAP S/4HANA Cloud\n"
            "- Usage Type: Production\n"
            "- Region: Germany (DE)\n"
            "- Organisation: Acme Corp\n\n"
            "**Assessment Result:**\n"
            "Verdict: **Approved** (Confidence: 87%)\n\n"
            "Rationale: Your request meets all SAP regulatory requirements for GDPR in the EU region. "
            "Historical approval rate for similar S/4HANA Cloud production requests in Germany is 91%. "
            "No compliance flags were raised.\n\n"
            "You may proceed with formal submission when ready."
        )

        mock_result = {"messages": [MagicMock(content=approved_response)]}

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke(
                    "I want to assess my request: SAP S/4HANA Cloud, Production use, Germany, Acme Corp",
                    "e2e-test-ctx-1",
                )

        assert response.status == "completed"
        assert "Approved" in response.message
        assert "Confidence" in response.message or "87%" in response.message

    @pytest.mark.asyncio
    async def test_full_assessment_flow_needs_more_info(self, add_agent_to_path):
        """
        Integration test: agent identifies missing compliance documentation and
        returns Needs More Info verdict with specific gap list.
        """
        from agent import SampleAgent

        agent = SampleAgent()

        needs_info_response = (
            "**Assessment Result:**\n"
            "Verdict: **Needs More Info** (Confidence: 62%)\n\n"
            "Rationale: The SAP Ariba Procurement request for the US region is missing "
            "required data residency compliance documentation. Historical approval rate "
            "for similar requests without this documentation is 38%.\n\n"
            "**Gaps to address:**\n"
            "1. Missing field: Data Residency Compliance Certificate (required for US region)\n"
            "   Suggested fix: Attach CCPA compliance documentation\n"
            "2. Non-compliant: US data sovereignty rule requires on-premise data storage declaration\n"
            "   Suggested fix: Confirm data storage location in the request\n\n"
            "Please address the gaps above and I will run a new assessment."
        )

        mock_result = {"messages": [MagicMock(content=needs_info_response)]}

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke(
                    "Assess my SAP Ariba Procurement request for the US without compliance docs",
                    "e2e-test-ctx-2",
                )

        assert response.status == "completed"
        assert "Needs More Info" in response.message
        assert len(response.message) > 50

    @pytest.mark.asyncio
    async def test_iterative_reassessment_after_feedback(self, add_agent_to_path):
        """
        Integration test: user receives Rejected → provides updated info →
        agent runs new assessment referencing previous verdict.
        """
        from agent import SampleAgent

        agent = SampleAgent()

        # First assessment: rejected
        rejected_response = (
            "Your previous prediction: N/A (first assessment)\n\n"
            "**Assessment Result:**\n"
            "Verdict: **Rejected** (Confidence: 78%)\n\n"
            "Rationale: Critical regulatory flag: missing export control compliance "
            "for APAC region deployment.\n\n"
            "**Gaps:**\n"
            "1. Missing: Export control classification number\n"
            "   Fix: Obtain ECC from your export compliance officer"
        )

        # Second assessment after user provides ECC number: approved
        updated_response = (
            "Your previous prediction was Rejected at 78% confidence. "
            "Based on your updates (ECC number provided), here is the new assessment:\n\n"
            "**Updated Assessment Result:**\n"
            "Verdict: **Approved** (Confidence: 82%)\n\n"
            "Rationale: With the export control classification number provided, "
            "the APAC deployment now meets all regulatory requirements."
        )

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"messages": [MagicMock(content=rejected_response)]}
            return {"messages": [MagicMock(content=updated_response)]}

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = side_effect
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []

                # First request
                first_response = await agent.invoke(
                    "Assess SAP SuccessFactors APAC deployment without ECC",
                    "e2e-iterative-ctx",
                )
                assert first_response.status == "completed"
                assert "Rejected" in first_response.message

                # Iterative update
                second_response = await agent.invoke(
                    "I have added the export control classification number ECC-2024-001. Re-assess please.",
                    "e2e-iterative-ctx",
                )
                assert second_response.status == "completed"
                assert "previous prediction" in second_response.message.lower() or "Approved" in second_response.message

    @pytest.mark.asyncio
    async def test_mcp_tools_available_during_assessment(self, add_agent_to_path):
        """Verify that MCP mock tools are available and loaded during an assessment."""
        from mcp_providers.agw import _build_mock_tools

        tools = _build_mock_tools()
        assert len(tools) > 0, "Expected MCP mock tools to be available during test"

        tool_names = [t.name for t in tools]
        # Both regulatory and approval tools should be available
        has_regulatory = any("regulatory" in n.lower() for n in tool_names)
        has_approval = any(
            any(k in n.lower() for k in ["changes", "approvable", "approver"])
            for n in tool_names
        )
        assert has_regulatory or has_approval, \
            f"Expected regulatory or approval tools in: {tool_names}"

    @pytest.mark.asyncio
    async def test_agent_runs_without_tools(self, add_agent_to_path):
        """Verify that the agent gracefully handles the case where no tools are available."""
        from agent import SampleAgent

        agent = SampleAgent()

        fallback_response = (
            "I apologize — the assessment tools are temporarily unavailable. "
            "Please try again in a few minutes."
        )
        mock_result = {"messages": [MagicMock(content=fallback_response)]}

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke("Assess my request", "e2e-no-tools-ctx")

        assert response.status == "completed"
        assert len(response.message) > 0
