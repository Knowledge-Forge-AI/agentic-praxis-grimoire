from src.app import total


def test_existing_total():
    assert total([1, 2]) == 3


def test_provider_task_placeholder():
    """The provider adds the task-specific tests after reviewing the plan."""
    pass
