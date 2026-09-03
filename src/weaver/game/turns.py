import random

from src.weaver.game.models import TurnOrder
from src.weaver.models.game import GameSession


class TurnManager:
    @staticmethod
    async def init_turn_order(session_id: str) -> TurnOrder:
        session = await GameSession.get(session_id)
        if not session:
            raise ValueError("Session not found")
        # Build order from players
        players = [p.user_id for p in session.players]
        random.shuffle(players)
        order = TurnOrder(session_id=session_id, order=players, current_index=0)
        await order.insert()
        return order

    @staticmethod
    async def get_current_actor(session_id: str) -> str | None:
        order = await TurnOrder.find_one(TurnOrder.session_id == session_id)
        if not order or not order.order:
            return None
        idx = order.current_index % len(order.order)
        return order.order[idx]

    @staticmethod
    async def advance_turn(session_id: str) -> str | None:
        order = await TurnOrder.find_one(TurnOrder.session_id == session_id)
        if not order or not order.order:
            return None
        order.current_index = (order.current_index + 1) % len(order.order)
        await order.save()
        return order.order[order.current_index]

    @staticmethod
    async def enqueue_action(session_id: str, actor_id: str | None, action_type: str, payload: dict, execute_at: int | None = None):
        from src.weaver.game.models import Event

        evt = Event(session_id=session_id, actor_id=actor_id, type=action_type, payload=payload, execute_at=execute_at)
        await evt.insert()
        # try to enqueue into Redis-backed durable queue (best-effort)
        try:
            from src.weaver.task_queue import enqueue as _enqueue

            # do not await failure; best-effort
            await _enqueue(str(evt.id))
        except Exception:
            pass
        return evt
