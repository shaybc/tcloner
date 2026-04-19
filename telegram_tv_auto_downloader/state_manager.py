import json
import os
import tempfile
from dataclasses import dataclass, field


@dataclass
class State:
    last_message_ids: dict[str, int] = field(default_factory=dict)
    downloaded_episodes: dict[str, list[str]] = field(default_factory=dict)


class StateManager:
    def __init__(self, path: str = "state.json") -> None:
        self.path = path
        self.state = State()
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self.state = State()
            return

        with open(self.path, "r", encoding="utf-8") as state_file:
            payload = json.load(state_file)

        self.state = State(
            last_message_ids={
                str(key): int(value)
                for key, value in payload.get("last_message_ids", {}).items()
            },
            downloaded_episodes={
                str(series): list(episodes)
                for series, episodes in payload.get("downloaded_episodes", {}).items()
            },
        )

    def save(self) -> None:
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)

        payload = {
            "last_message_ids": self.state.last_message_ids,
            "downloaded_episodes": self.state.downloaded_episodes,
        }

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            delete=False,
            suffix=".tmp",
        ) as temp_file:
            json.dump(payload, temp_file, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_path = temp_file.name

        os.replace(temp_path, self.path)

    def get_last_message_id(self, channel: str) -> int:
        return int(self.state.last_message_ids.get(channel, 0))

    def set_last_message_id(self, channel: str, message_id: int) -> None:
        self.state.last_message_ids[channel] = int(message_id)
        self.save()

    def is_downloaded(self, series_name: str, episode_code: str) -> bool:
        return episode_code in self.state.downloaded_episodes.get(series_name, [])

    def mark_downloaded(self, series_name: str, episode_code: str) -> None:
        episodes = self.state.downloaded_episodes.setdefault(series_name, [])
        if episode_code not in episodes:
            episodes.append(episode_code)
            self.save()
