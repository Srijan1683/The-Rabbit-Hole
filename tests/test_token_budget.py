import tiktoken

from app.agent.token_manager import build_token_budget, count_message_tokens


def test_token_count_and_budget_reserve() -> None:
    message = {"role": "user", "content": "Explore quantum entanglement."}
    model = "unknown-test-model"
    encoding = tiktoken.get_encoding("cl100k_base")

    assert count_message_tokens(message, model=model) == len(
        encoding.encode("user")
    ) + len(encoding.encode("Explore quantum entanglement."))

    budget = build_token_budget(
        model=model,
        context_window=1_000,
        system_prompt_tokens=100,
        current_query_tokens=50,
        history_tokens=250,
        response_reserve=200,
    )

    assert budget.available_for_response == 400
