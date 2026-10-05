# Bundled tool policy

STEP 08 stores manifests and staging scripts here, not ad-hoc binaries.

Future release staging will place pinned FFmpeg/ffprobe and Deno payloads into
the portable distribution only after provenance, checksum, license, and clean
Windows smoke tests pass.

Do not copy executables from a developer machine into source control.
