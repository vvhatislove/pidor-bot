import asyncio
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from config.config import config
from config.constants import AIPrompt
from logger import setup_logger
from services.ai_service import AIService, clean_model_response, is_bad_model_response

logger = setup_logger(__name__)


@dataclass(frozen=True)
class BufferedPrompt:
    key: str
    prompt: str


CONTEXT_FREE_PROMPTS = [
    BufferedPrompt("pidor_searching", AIPrompt.SEARCHING_PIDOR_PROMPT),
    BufferedPrompt("pidor_win_phrase", AIPrompt.WIN_PHRASE_PIDOR_PROMPT),
    BufferedPrompt("duel_winner_choice", AIPrompt.DUEL_WINNER_CHOICE_PROMPT),
]


class AIResponseBuffer:
    def __init__(self, target_size: int, generation_concurrency: int, storage_path: str | Path) -> None:
        self._target_size = max(target_size, 0)
        self._semaphore = asyncio.Semaphore(max(generation_concurrency, 1))
        self._storage_path = Path(storage_path)
        self._buffers: dict[str, deque[str]] = {
            prompt.key: deque(maxlen=self._target_size) for prompt in CONTEXT_FREE_PROMPTS
        }
        self._seen: dict[str, set[str]] = {prompt.key: set() for prompt in CONTEXT_FREE_PROMPTS}
        self._prompts = {prompt.key: prompt for prompt in CONTEXT_FREE_PROMPTS}
        self._refill_tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()
        self._load_from_disk()

    async def pop(self, key: str) -> str | None:
        should_refill = False
        async with self._lock:
            buffer = self._buffers.get(key)
            if not buffer:
                return None
            response = buffer.popleft()
            self._save_to_disk_locked()
            should_refill = len(buffer) < self._target_size
        if should_refill:
            self.schedule_refill(key)
        return response

    def schedule_refill(self, key: str) -> None:
        if key not in self._prompts:
            return
        task = self._refill_tasks.get(key)
        if task and not task.done():
            return
        self._refill_tasks[key] = asyncio.create_task(self._safe_refill_prompt(self._prompts[key]))

    async def refill_once(self) -> None:
        await asyncio.gather(*(self._refill_prompt(prompt) for prompt in CONTEXT_FREE_PROMPTS))

    async def refill_key_once(self, key: str) -> None:
        prompt = self._prompts.get(key)
        if prompt:
            await self._refill_prompt(prompt)

    async def _safe_refill_prompt(self, prompt: BufferedPrompt) -> None:
        try:
            await self._refill_prompt(prompt)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Scheduled AI response buffer refill failed for %s", prompt.key)

    async def _refill_prompt(self, prompt: BufferedPrompt) -> None:
        attempts = 0
        max_attempts = max(self._target_size * 2, 1)
        while attempts < max_attempts:
            async with self._lock:
                current_size = len(self._buffers[prompt.key])
            if current_size >= self._target_size:
                return

            async with self._semaphore:
                response = await AIService.get_response("", prompt.prompt)
            attempts += 1
            if not response:
                return

            async with self._lock:
                if response in self._seen[prompt.key]:
                    continue
                self._buffers[prompt.key].append(response)
                self._seen[prompt.key].add(response)
                self._save_to_disk_locked()
                logger.info(
                    "Buffered AI response for %s (%s/%s)",
                    prompt.key,
                    len(self._buffers[prompt.key]),
                    self._target_size,
                )

    def _load_from_disk(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.exception("Failed to load AI response buffer from %s", self._storage_path)
            return

        if not isinstance(data, dict):
            logger.warning("Ignoring malformed AI response buffer file: %s", self._storage_path)
            return

        for key, values in data.items():
            if key not in self._buffers or not isinstance(values, list):
                continue
            for value in values:
                if not isinstance(value, str):
                    continue
                value = clean_model_response(value)
                if not value.strip() or is_bad_model_response(value) or value in self._seen[key]:
                    continue
                self._buffers[key].append(value)
                self._seen[key].add(value)
        logger.info("Loaded AI response buffer from %s", self._storage_path)

    def _save_to_disk_locked(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {key: list(buffer) for key, buffer in self._buffers.items()}
        tmp_path = self._storage_path.with_suffix(self._storage_path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self._storage_path)


ai_response_buffer = AIResponseBuffer(
    target_size=config.AI_BUFFER_TARGET_SIZE,
    generation_concurrency=config.AI_BUFFER_GENERATION_CONCURRENCY,
    storage_path=config.AI_BUFFER_STORAGE_PATH,
)


async def ai_response_buffer_worker() -> None:
    logger.info("AI response buffer worker started")
    while True:
        try:
            await ai_response_buffer.refill_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AI response buffer refill failed")
        await asyncio.sleep(config.AI_BUFFER_REFILL_INTERVAL_SECONDS)
