from typing import Optional

# pylint: disable=unused-argument
class IDataStore:
    def get(self, key: str) -> Optional[str]:
        return None

    def set(self, key: str, value: str):
        pass

    def shutdown(self):
        pass
