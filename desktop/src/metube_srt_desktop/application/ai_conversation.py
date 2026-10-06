from __future__ import annotations

from metube_srt_desktop.application.dto.ai_chat import (
    AIAgentContext,
    AIChatMessage,
    AIChatRole,
    AIConversationReply,
)
from metube_srt_desktop.application.ports.ai_provider import AIProviderError, AIProviderPort

_HUMANLIKE_SYSTEM_INSTRUCTION = """
Kamu adalah AI Agent di aplikasi Windows MeTube-SRT.

Tugasmu hanya membantu pengguna mengontrol dan memahami proses download video, playlist,
channel, antrian, kualitas video, folder tujuan, dan subtitle asli. Kamu bukan agen komputer
umum dan tidak boleh mengklaim menjalankan shell, yt-dlp, browser, atau tindakan di luar
perintah aplikasi yang tersedia.

Gaya bicara wajib:
- Gunakan Bahasa Indonesia yang alami seperti asisten manusia yang benar-benar mengikuti percakapan.
- Jangan terdengar seperti bot, formulir, dokumentasi, atau pesan error teknis.
- Jangan memakai kalimat pembuka generik seperti "Sebagai AI..." atau mengulang pertanyaan pengguna.
- Ingat konteks percakapan sebelumnya. Pahami rujukan seperti "yang tadi", "ulang lagi",
  "jangan pakai subtitle", dan "folder sebelumnya" jika konteksnya tersedia.
- Kalau maksud pengguna sudah jelas, jangan bertanya ulang.
- Jawaban normal 1-4 kalimat. Lebih panjang hanya jika pengguna memang meminta penjelasan.
- Jika ada error, jelaskan dengan bahasa sederhana. Jangan menebak penyebab yang belum diketahui.
- Jika pengguna memberi perintah download, rangkum rencana dengan natural dan sebutkan detail penting
  seperti kualitas/SRT hanya jika relevan.
- Jangan pernah mengatakan download sudah berhasil sebelum aplikasi memberi status berhasil.
- Jangan menawarkan terjemahan subtitle. Kebijakan subtitle MeTube-SRT adalah:
  manual/creator -> auto-generated asli yang terbukti original -> tanpa SRT.
- Jangan menampilkan API key, token, cookie, secret, atau meminta pengguna mengirimkannya di chat.
- Tidak perlu markdown rumit. Utamakan percakapan ringkas dan jelas.

Contoh nada yang benar:
Pengguna: "download yang tadi 720p tanpa srt"
Jawab: "Siap. Yang tadi saya siapkan ulang dalam 720p tanpa subtitle."

Pengguna: "kenapa gagal?"
Jawab: "Download-nya belum selesai. Dari status aplikasi, prosesnya terputus di tahap akhir.
Kalau detail error tersedia, saya jelaskan penyebabnya dari situ tanpa menebak."
""".strip()


class HumanlikeAIConversation:
    """Conversation memory + natural-language policy over an AI provider."""

    def __init__(self, provider: AIProviderPort, *, max_messages: int = 16) -> None:
        if max_messages < 2:
            raise ValueError("max_messages must be >= 2")
        self._provider = provider
        self._max_messages = max_messages
        self._history: list[AIChatMessage] = []

    def history(self) -> tuple[AIChatMessage, ...]:
        return tuple(self._history)

    def reply(self, user_text: str, context: AIAgentContext) -> AIConversationReply:
        clean_text = user_text.strip()
        if not clean_text:
            raise ValueError("Pesan AI tidak boleh kosong.")

        user_message = AIChatMessage(AIChatRole.USER, clean_text)
        provider_messages = (*self._history, _context_message(context), user_message)

        try:
            reply_text = self._provider.generate_reply(
                system_instruction=_HUMANLIKE_SYSTEM_INSTRUCTION,
                messages=provider_messages,
            ).strip()
            if not reply_text:
                raise AIProviderError("empty_response", "Gemini tidak mengembalikan jawaban.")
        except AIProviderError as exc:
            fallback = _friendly_provider_failure(exc.error_code)
            self._remember(user_message, AIChatMessage(AIChatRole.ASSISTANT, fallback))
            return AIConversationReply(
                text=fallback,
                provider_ok=False,
                error_code=exc.error_code,
            )

        assistant_message = AIChatMessage(AIChatRole.ASSISTANT, reply_text)
        self._remember(user_message, assistant_message)
        return AIConversationReply(text=reply_text, provider_ok=True)

    def clear(self) -> None:
        self._history.clear()

    def _remember(self, *messages: AIChatMessage) -> None:
        self._history.extend(messages)
        if len(self._history) > self._max_messages:
            del self._history[: len(self._history) - self._max_messages]


def _context_message(context: AIAgentContext) -> AIChatMessage:
    url = context.current_url or "belum ada URL"
    quality = context.quality or "belum dipilih"
    output = context.output_directory or "belum dipilih"
    srt = "aktif" if context.subtitle_requested else "tidak aktif"
    text = (
        "[Konteks aplikasi saat ini — gunakan sebagai konteks, jangan dibacakan mentah]\n"
        f"URL: {url}\n"
        f"Kualitas: {quality}\n"
        f"SRT: {srt}\n"
        f"Folder: {output}\n"
        f"Antrian: aktif={context.queue_active}, menunggu={context.queue_waiting}, "
        f"gagal/terputus={context.queue_failed}"
    )
    return AIChatMessage(AIChatRole.USER, text)


def _friendly_provider_failure(error_code: str) -> str:
    if error_code == "missing_api_key":
        return (
            "API Gemini belum ditambahkan. Buka menu API Gemini, tambahkan key dulu, "
            "lalu kirim pesanmu lagi."
        )
    if error_code == "invalid_api_key":
        return (
            "API key Gemini yang aktif ditolak. Coba cek atau ganti key di menu API Gemini, "
            "lalu saya coba lagi."
        )
    if error_code == "rate_limited":
        return (
            "Gemini sedang kena batas pemakaian. Tunggu sebentar lalu coba lagi; "
            "download manual tetap bisa dipakai."
        )
    if error_code == "network_error":
        return "Saya belum bisa terhubung ke Gemini. Cek koneksi internet lalu coba lagi."
    return "Saya belum bisa menghubungi Gemini sekarang. Coba lagi sebentar."
