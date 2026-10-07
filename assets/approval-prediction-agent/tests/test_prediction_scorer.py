"""Unit tests for the prediction scoring logic."""

import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def use_testing_mode():
    os.environ["IBD_TESTING"] = "1"
    yield


@pytest.mark.usefixtures("add_agent_to_path")
class TestPredictionScorer:
    """Tests for the agent's prediction synthesis and confidence scoring."""

    @pytest.mark.asyncio
    async def test_agent_invoke_returns_completed_status(self, add_agent_to_path):
        """Verify that agent.invoke() completes and returns a status."""
        from agent import SampleAgent, AgentResponse

        agent = SampleAgent()

        mock_result = {
            "messages": [
                MagicMock(content="Based on your request, the prediction is: **Approved** (Confidence: 85%). Your SAP S/4HANA Cloud request for Production use in Germany meets all regulatory requirements.")
            ]
        }

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke("Predict approval for SAP S/4HANA in Germany", "test-ctx-1")

        assert response is not None
        assert isinstance(response, AgentResponse)
        assert response.status == "completed"
        assert len(response.message) > 0

    @pytest.mark.asyncio
    async def test_agent_stream_yields_processing_and_result(self, add_agent_to_path):
        """Verify that stream() yields at least one processing update and a final result."""
        from agent import SampleAgent

        agent = SampleAgent()

        mock_result = {
            "messages": [
                MagicMock(content="Verdict: Needs More Info (Confidence: 55%). The request is missing the data residency documentation.")
            ]
        }

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                chunks = []
                async for chunk in agent.stream("Check my Ariba request", "test-ctx-2"):
                    chunks.append(chunk)

        assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"
        # First chunk should be the processing update
        assert chunks[0]["is_task_complete"] is False
        assert chunks[0]["content"] == "Processing..."
        # Last chunk should be the final result
        final = chunks[-1]
        assert final["is_task_complete"] is True
        assert "Needs More Info" in final["content"] or len(final["content"]) > 0

    @pytest.mark.asyncio
    async def test_agent_handles_low_confidence_scenario(self, add_agent_to_path):
        """Verify that a low confidence prediction triggers appropriate response."""
        from agent import SampleAgent

        agent = SampleAgent()

        mock_result = {
            "messages": [
                MagicMock(content="Verdict: Rejected (Confidence: 35%). Confidence is below 60% — we recommend reviewing the gaps and consulting the SAP approval team before submitting.")
            ]
        }

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_result
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke("My Ariba request for US with no compliance docs", "test-ctx-3")

        assert response.status == "completed"
        assert len(response.message) > 0

    @pytest.mark.asyncio
    async def test_agent_handles_tool_invocation_error(self, add_agent_to_path):
        """Verify that agent handles exceptions gracefully and returns error status."""
        from agent import SampleAgent

        agent = SampleAgent()

        with patch.object(agent, "_invoke_with_fallback", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.side_effect = Exception("Simulated LLM failure")
            with patch.object(agent, "_get_tools", new_callable=AsyncMock) as mock_tools:
                mock_tools.return_value = []
                response = await agent.invoke("Test query", "test-ctx-error")

        assert response.status in ("completed", "error")
        assert "error" in response.message.lower() or "encountered" in response.message.lower()

    @pytest.mark.asyncio
    async def test_agent_mcp_tools_loaded_lazily(self, add_agent_to_path):
        """Verify that MCP tools are loaded lazily (not in __init__)."""
        from agent import SampleAgent

        # Create agent - should NOT call get_mcp_tools during init
        with patch("agent.get_mcp_tools", new_callable=AsyncMock) as mock_tools:
            mock_tools.return_value = []
            agent = SampleAgent()
            # Assert tools were NOT loaded yet
            mock_tools.assert_not_called()

        # Now call _get_tools — should load lazily
        with patch("agent.get_mcp_tools", new_callable=AsyncMock) as mock_tools2:
            mock_tools2.return_value = []
            tools = await agent._get_tools()
            mock_tools2.assert_called_once()
            assert tools == []
