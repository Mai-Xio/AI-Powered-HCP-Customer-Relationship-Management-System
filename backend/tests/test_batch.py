import pytest
from pydantic import ValidationError

from app.crud import save_interactions
from app.main import batch_chat
from app.schemas import BatchChatRequest, BatchSaveRequest, InteractionDraft, InteractionPreferences


def test_batch_runs_each_entry_through_the_langgraph_agent():
    request = BatchChatRequest(
        entries=[
            "Met Dr. Meera Kapoor and discussed Prodo-X efficacy with positive sentiment.",
            "Met Dr. Priya Shah and discussed patient affordability with positive sentiment.",
        ],
        preferences=InteractionPreferences(
            timezone="Asia/Kolkata",
            date_format="DD/MM/YYYY",
            time_format="12h",
        ),
    )

    result = batch_chat(request)

    assert len(result.results) == 2
    assert [item.response.draft.hcp_name for item in result.results] == [
        "Dr. Meera Kapoor",
        "Dr. Priya Shah",
    ]
    assert all(item.response.planner_mode == "llm" for item in result.results)
    assert all(item.response.tool_trace[0].name == "log_interaction" for item in result.results)


def test_batch_is_capped_at_three_entries_for_demo_rate_limits():
    with pytest.raises(ValidationError, match="at most 3 items"):
        BatchChatRequest(entries=["one", "two", "three", "four"])

    with pytest.raises(ValidationError, match="at most 3 items"):
        BatchSaveRequest(interactions=[InteractionDraft()] * 4)


def test_atomic_batch_save_rolls_back_when_commit_fails():
    class FailingSession:
        rolled_back = False

        def add_all(self, interactions):
            self.interactions = interactions

        def commit(self):
            raise RuntimeError("database unavailable")

        def rollback(self):
            self.rolled_back = True

    session = FailingSession()

    with pytest.raises(RuntimeError, match="database unavailable"):
        save_interactions(session, [InteractionDraft(hcp_name="Dr. Rollback")])

    assert session.rolled_back is True
