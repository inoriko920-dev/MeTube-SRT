from metube_srt_desktop.adapters.download import (
    SubprocessDownloadWorkerFactory,
    SubprocessWorkerAdapter,
)
from metube_srt_desktop.domain.jobs import JobSpec, QualityPreset


def test_subprocess_factory_creates_lazy_worker_adapter() -> None:
    job = JobSpec(
        job_id="job-1",
        source_url="https://www.youtube.com/watch?v=abc",
        output_directory="Downloads",
        quality=QualityPreset.BEST,
        selected_subtitle=None,
    )
    factory = SubprocessDownloadWorkerFactory(
        worker_argv=("python", "-m", "metube_srt_desktop.worker")
    )

    worker = factory.create(job, worker_run_id="run-1")

    assert isinstance(worker, SubprocessWorkerAdapter)
