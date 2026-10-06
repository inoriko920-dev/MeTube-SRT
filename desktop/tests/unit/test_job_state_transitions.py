import pytest

from metube_srt_desktop.domain.jobs import (
    JobState,
    is_terminal_job_state,
    transition_job_state,
)


def test_expected_download_state_path_is_valid() -> None:
    state = JobState.QUEUED
    state = transition_job_state(state, JobState.RUNNING)
    state = transition_job_state(state, JobState.POSTPROCESSING)
    state = transition_job_state(state, JobState.SUCCEEDED)

    assert state is JobState.SUCCEEDED
    assert is_terminal_job_state(state) is True


def test_cancelling_can_finish_as_cancelled_or_race_to_success() -> None:
    assert transition_job_state(JobState.CANCELLING, JobState.CANCELLED) is JobState.CANCELLED
    assert transition_job_state(JobState.CANCELLING, JobState.SUCCEEDED) is JobState.SUCCEEDED


def test_terminal_state_cannot_transition_back_to_running() -> None:
    with pytest.raises(ValueError, match="invalid job state transition"):
        transition_job_state(JobState.SUCCEEDED, JobState.RUNNING)
