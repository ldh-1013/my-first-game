import json, os
from settings import SAVE_PATH, TOTAL_STAGES

class SaveManager:
    def __init__(self):
        self.data = {"last_stage": 1, "stages": {}}
        self.load()

    def load(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                self.data["last_stage"] = loaded.get("last_stage", 1)
                self.data["stages"] = loaded.get("stages", {})
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def save(self):
        try:
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def record_clear(self, stage_num, stars, score):
        key = str(stage_num)
        entry = self.data["stages"].get(key, {"best_stars": 0, "best_score": None})
        entry["best_stars"] = max(entry.get("best_stars", 0), stars)
        prev = entry.get("best_score")
        entry["best_score"] = score if prev is None else min(prev, score)
        self.data["stages"][key] = entry
        self.save()

    def set_last_stage(self, stage_num):
        self.data["last_stage"] = stage_num
        self.save()

    def get_last_stage(self):
        return self.data.get("last_stage", 1)

    def has_progress(self):
        return bool(self.data["stages"]) or self.get_last_stage() > 1

    def get_best(self, stage_num):
        entry = self.data["stages"].get(str(stage_num))
        if not entry:
            return 0, None
        return entry.get("best_stars", 0), entry.get("best_score")
