# -*- coding: utf-8 -*-

class Inventory:
    """6칸 인벤토리. 슬롯에 아이템 ID 문자열을 저장한다."""

    MAX_SLOTS = 6

    def __init__(self):
        self.slots = [None] * self.MAX_SLOTS  # None = 빈 슬롯

    def add(self, item_id):
        """아이템 추가. 성공 시 True, 꽉 찼으면 False."""
        for i in range(self.MAX_SLOTS):
            if self.slots[i] is None:
                self.slots[i] = item_id
                return True
        return False

    def remove(self, item_id):
        """아이템 제거. 성공 시 True."""
        for i in range(self.MAX_SLOTS):
            if self.slots[i] == item_id:
                self.slots[i] = None
                return True
        return False

    def has(self, item_id):
        return item_id in self.slots

    def is_full(self):
        return all(s is not None for s in self.slots)

    def count(self):
        return sum(1 for s in self.slots if s is not None)
