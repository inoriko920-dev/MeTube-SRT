from metube_srt_desktop.application.dto.download import ResolveRequest, ResolvedItem, ResolvedSource
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset, SourceKind
from metube_srt_desktop.domain.subtitles import SubtitleKind, SubtitleTrack
from metube_srt_desktop.worker.protocol import (
    WorkerCommandEnvelope,
    WorkerCommandType,
    resolved_source_from_payload,
    resolved_source_to_payload,
)


def test_resolve_command_round_trip() -> None:
    command = WorkerCommandEnvelope.for_resolve(
        ResolveRequest("https://www.youtube.com/watch?v=abc"),
        job_id="resolve-1",
        worker_run_id="run-1",
    )
    decoded = WorkerCommandEnvelope.from_json_line(command.to_json_line())

    assert decoded.command_type is WorkerCommandType.RESOLVE
    assert decoded.as_resolve_request() == ResolveRequest("https://www.youtube.com/watch?v=abc")


def test_download_command_round_trip_preserves_frozen_subtitle_choice() -> None:
    subtitle = SubtitleTrack(
        language_code="id-orig",
        kind=SubtitleKind.AUTO_GENERATED,
        is_original=True,
    )
    job = JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory="Downloads",
        quality=QualityPreset.P1080,
        selected_subtitle=subtitle,
    )

    decoded = WorkerCommandEnvelope.from_json_line(
        WorkerCommandEnvelope.for_download(job, worker_run_id="run-1").to_json_line()
    )

    assert decoded.as_job_spec() == job


def test_resolved_source_wire_round_trip() -> None:
    source = ResolvedSource(
        source_url="https://www.youtube.com/watch?v=abc",
        kind=SourceKind.VIDEO,
        title="Video",
        items=(
            ResolvedItem(
                video_id="abc",
                title="Video",
                webpage_url="https://www.youtube.com/watch?v=abc",
                subtitles=(
                    SubtitleTrack(
                        language_code="id",
                        kind=SubtitleKind.MANUAL,
                        is_original=False,
                    ),
                ),
            ),
        ),
    )

    assert resolved_source_from_payload(resolved_source_to_payload(source)) == source
