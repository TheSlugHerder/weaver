import asyncio
import time
from typing import Optional

from src.weaver.game.models import Event
from src.weaver.game.engine import GameEngine
from src.weaver.task_queue import dequeue, get_redis


class BackgroundWorker:
    def __init__(self, poll_interval: float = 1.0):
        self._task: Optional[asyncio.Task] = None
        self._poll_interval = poll_interval
        self._running = False

    async def _process_event(self, evt: Event):
        try:
            evt.status = "processing"
            await evt.save()
            # Basic handler mapping
            if evt.type == "attack":
                session_id = evt.session_id
                actor_id = evt.actor_id
                payload = evt.payload
                target_index = int(payload.get("target_index", 0))
                attack_mod = int(payload.get("attack_mod", 0))
                result = await GameEngine.attack_monster(session_id, actor_id, target_index, attack_mod)
                evt.result = result
            elif evt.type == "save":
                session_id = evt.session_id
                payload = evt.payload
                target_type = payload.get("target_type", "monster")
                target_index = int(payload.get("target_index", 0))
                dc = int(payload.get("dc", 10))
                save_type = payload.get("save_type", "dex")
                result = await GameEngine.resolve_save(session_id, target_type, target_index, dc, save_type)
                evt.result = result
            elif evt.type == "spell":
                session_id = evt.session_id
                actor_id = evt.actor_id
                payload = evt.payload
                spell_name = payload.get("spell_name")
                targets = payload.get("targets", [])
                result = await GameEngine.cast_spell(session_id, actor_id, spell_name, targets)
                evt.result = result
            else:
                # unknown action — echo
                evt.result = {"echo": {"type": evt.type, "payload": evt.payload}}
            evt.status = "done"
            await evt.save()
        except Exception as e:
            evt.status = "failed"
            evt.result = {"error": str(e)}
            await evt.save()

    async def _run(self):
        self._running = True
        r = await get_redis()
        while self._running:
            # If Redis queue available, consume from it (durable, FIFO)
            if r:
                item = await dequeue(timeout=1)
                if item:
                    try:
                        # decode bytes to str if necessary
                        if isinstance(item, bytes):
                            item = item.decode()
                        evt = await Event.get(item)
                        if evt:
                            await self._process_event(evt)
                        continue
                    except Exception:
                        # on any issue, fall back to DB polling
                        pass

            # fallback: poll pending events from DB
            now = int(time.time())
            pending = await Event.find_many((Event.status == "pending") & ((Event.execute_at == None) | (Event.execute_at <= now))).to_list()
            if pending:
                for evt in pending:
                    await self._process_event(evt)
                continue
            await asyncio.sleep(self._poll_interval)

    def start(self):
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
