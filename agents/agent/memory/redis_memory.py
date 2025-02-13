from agents.agent.memory.memory import MemoryManager, MemoryObject
from agents.common.redis_utils import redis_utils


class RedisMemory(MemoryManager):
    memory: dict[str, list[MemoryObject]] = {}
    prefix: str = "deepcore.memory"
    max_ttl: int = 5 * 24 * 60 * 60

    def __init__(self, memory_size: int = 10) -> None:
        super().__init__(memory_size=memory_size)

    def get_memory_by_conversation_id(self, conversation_id: str) -> list[MemoryObject]:
        redis_key = self._get_redis_key(conversation_id)
        dict_list = redis_utils.get_list(redis_key)
        return [MemoryObject.from_dict(d) for d in dict_list]

    def save_memory(self, conversation_id: str, memory: MemoryObject):
        redis_key = self._get_redis_key(conversation_id)
        redis_utils.push_to_list(redis_key, memory.to_dict(), self.memory_size, self.max_ttl)

    def _get_redis_key(self, conversation_id: str):
        return f"{self.prefix}.{conversation_id}"