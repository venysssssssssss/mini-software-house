"""Tests for the Agent base class with mocked Ollama."""

from unittest.mock import patch

from src.agents.base import (
    BASE_MODELS,
    FINETUNED_MODELS,
    Agent,
    get_model_for_role,
)


class TestGetModelForRole:
    def test_known_roles_base(self, monkeypatch):
        monkeypatch.delenv("USE_FINETUNED_MODELS", raising=False)
        assert get_model_for_role("planner") == "qwen2.5:3b"
        assert get_model_for_role("backend") == "qwen2.5-coder:3b"
        assert get_model_for_role("frontend") == "qwen2.5-coder:1.5b"
        assert get_model_for_role("tester") == "qwen2.5-coder:3b"
        assert get_model_for_role("documenter") == "gemma2:2b"
        assert get_model_for_role("rag") == "phi3:mini"

    def test_unknown_role_returns_default(self, monkeypatch):
        monkeypatch.delenv("USE_FINETUNED_MODELS", raising=False)
        assert get_model_for_role("unknown") == "qwen2.5:3b"
        assert get_model_for_role("") == "qwen2.5:3b"

    def test_finetuned_models_when_enabled(self, monkeypatch):
        monkeypatch.setenv("USE_FINETUNED_MODELS", "true")
        assert get_model_for_role("planner") == "planner-ft"
        assert get_model_for_role("backend") == "executor-ft"
        assert get_model_for_role("tester") == "tester-ft"
        assert get_model_for_role("documenter") == "documenter-ft"

    def test_finetuned_fallback_for_roles_without_ft(self, monkeypatch):
        monkeypatch.setenv("USE_FINETUNED_MODELS", "true")
        # frontend and rag have no fine-tuned variant
        assert get_model_for_role("frontend") == "qwen2.5-coder:1.5b"
        assert get_model_for_role("rag") == "phi3:mini"

    def test_finetuned_false_uses_base(self, monkeypatch):
        monkeypatch.setenv("USE_FINETUNED_MODELS", "false")
        assert get_model_for_role("planner") == "qwen2.5:3b"

    def test_finetuned_env_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("USE_FINETUNED_MODELS", "TRUE")
        assert get_model_for_role("planner") == "planner-ft"

    def test_base_models_dict_complete(self):
        assert len(BASE_MODELS) == 6
        for role in ["planner", "backend", "frontend", "tester", "documenter", "rag"]:
            assert role in BASE_MODELS

    def test_finetuned_models_dict(self):
        assert len(FINETUNED_MODELS) == 4
        assert "frontend" not in FINETUNED_MODELS
        assert "rag" not in FINETUNED_MODELS


class TestAgentChatHistory:
    def test_add_to_history(self):
        agent = Agent(name="test", model="m", system_prompt="sp")
        agent._add_to_history("user", "hello")
        assert len(agent.chat_history) == 1
        assert agent.chat_history[0] == {"role": "user", "content": "hello"}

    def test_history_capped_at_10(self):
        agent = Agent(name="test", model="m", system_prompt="sp")
        for i in range(15):
            agent._add_to_history("user", f"msg-{i}")
        assert len(agent.chat_history) == 10
        # Should keep the last 10
        assert agent.chat_history[0]["content"] == "msg-5"
        assert agent.chat_history[-1]["content"] == "msg-14"

    def test_history_rotation_preserves_recent(self):
        agent = Agent(name="test", model="m", system_prompt="sp")
        # Simulate 6 full turns (12 messages -> capped to 10)
        for i in range(6):
            agent._add_to_history("user", f"q{i}")
            agent._add_to_history("assistant", f"a{i}")
        assert len(agent.chat_history) == 10
        # After 12 msgs, last 10 are kept: q1,a1,q2,a2,q3,a3,q4,a4,q5,a5
        assert agent.chat_history[0]["content"] == "q1"
        assert agent.chat_history[-1]["content"] == "a5"


class TestAgentGenerateResponse:
    @patch("src.agents.base.ollama")
    def test_generate_response_success(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {"message": {"content": "Hello back!"}}

        agent = Agent(name="test", model="test-model", system_prompt="You are helpful.")
        result = agent.generate_response("Hi")

        assert result == "Hello back!"
        mock_client.chat.assert_called_once()

        # Verify system prompt is first message
        call_args = mock_client.chat.call_args
        messages = call_args[1]["messages"] if "messages" in call_args[1] else call_args[0][1]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."

    @patch("src.agents.base.ollama")
    def test_generate_response_adds_to_history(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {"message": {"content": "response"}}

        agent = Agent(name="test", model="m", system_prompt="sp")
        agent.generate_response("question")

        assert len(agent.chat_history) == 2
        assert agent.chat_history[0] == {"role": "user", "content": "question"}
        assert agent.chat_history[1] == {"role": "assistant", "content": "response"}

    @patch("src.agents.base.ollama")
    def test_generate_response_sends_keep_alive_zero(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {"message": {"content": "ok"}}

        agent = Agent(name="test", model="m", system_prompt="sp")
        agent.generate_response("test")

        call_kwargs = mock_client.chat.call_args[1]
        assert call_kwargs["keep_alive"] == 0

    @patch("src.agents.base.ollama")
    def test_generate_response_ollama_error(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.side_effect = ConnectionError("Ollama is down")

        agent = Agent(name="test", model="m", system_prompt="sp")
        result = agent.generate_response("test")

        assert "Error:" in result
        assert "Ollama is down" in result


# ---- Sprint 2: Metrics Collection ----


class TestAgentMetrics:
    def setup_method(self):
        Agent.reset_metrics()

    @patch("src.agents.base.ollama")
    def test_metrics_collected_on_success(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {
            "message": {"content": "response"},
            "prompt_eval_count": 42,
            "eval_count": 15,
        }

        agent = Agent(name="TestAgent", model="test-model", system_prompt="sp")
        agent.generate_response("hello")

        metrics = Agent.get_collected_metrics()
        assert len(metrics) == 1
        m = metrics[0]
        assert m.agent_name == "TestAgent"
        assert m.model == "test-model"
        assert m.prompt_tokens == 42
        assert m.response_tokens == 15
        assert m.latency_ms > 0
        assert m.success is True
        assert m.error is None

    @patch("src.agents.base.ollama")
    def test_metrics_collected_on_failure(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.side_effect = ConnectionError("down")

        agent = Agent(name="FailAgent", model="m", system_prompt="sp")
        agent.generate_response("test")

        metrics = Agent.get_collected_metrics()
        assert len(metrics) == 1
        m = metrics[0]
        assert m.success is False
        assert m.error == "down"
        assert m.latency_ms >= 0

    @patch("src.agents.base.ollama")
    def test_reset_clears_metrics(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {"message": {"content": "ok"}}

        agent = Agent(name="t", model="m", system_prompt="sp")
        agent.generate_response("test")
        assert len(Agent.get_collected_metrics()) == 1

        Agent.reset_metrics()
        assert len(Agent.get_collected_metrics()) == 0

    @patch("src.agents.base.ollama")
    def test_metrics_shared_across_agents(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        mock_client.chat.return_value = {
            "message": {"content": "ok"},
            "prompt_eval_count": 10,
            "eval_count": 5,
        }

        a1 = Agent(name="Agent1", model="m1", system_prompt="sp")
        a2 = Agent(name="Agent2", model="m2", system_prompt="sp")

        a1.generate_response("q1")
        a2.generate_response("q2")

        metrics = Agent.get_collected_metrics()
        assert len(metrics) == 2
        assert metrics[0].agent_name == "Agent1"
        assert metrics[1].agent_name == "Agent2"

    @patch("src.agents.base.ollama")
    def test_metrics_default_zero_when_missing(self, mock_ollama):
        mock_client = mock_ollama.Client.return_value
        # Ollama response without token counts
        mock_client.chat.return_value = {"message": {"content": "ok"}}

        agent = Agent(name="t", model="m", system_prompt="sp")
        agent.generate_response("test")

        m = Agent.get_collected_metrics()[0]
        assert m.prompt_tokens == 0
        assert m.response_tokens == 0
