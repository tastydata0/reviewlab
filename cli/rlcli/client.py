import requests
import os
from typing import Optional, Dict, List, Any
from .config import load_token, load_url

class Client:
    def __init__(self):
        self.token = load_token()
        self.base_url = load_url()

    def _get_headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def login(self, email: str, password: str, token_ttl_minutes: int) -> Optional[str]:
        try:
            response = requests.post(
                f"{self.base_url}/users/login",
                json={
                    "email": email,
                    "password": password,
                    "expires_in": token_ttl_minutes,
                },
            )
            if response.status_code == 200:
                token = response.json().get("access_token")
                self.token = token
                return token
        except Exception:
            pass
        return None

    def submit_task(self, join_code: str, file_paths: List[str]) -> Dict[str, Any]:
        if not self.token:
            raise Exception("Please login first.")

        files_to_send = []
        opened_files = []
        try:
            for path in file_paths:
                if not os.path.exists(path):
                    raise Exception(f"File not found: {path}")
                f = open(path, "rb")
                opened_files.append(f)
                files_to_send.append(("files", (os.path.basename(path), f)))

            response = requests.post(
                f"{self.base_url}/submissions/",
                headers=self._get_headers(),
                data={"task_id": join_code},
                files=files_to_send,
            )
        finally:
            for f in opened_files:
                f.close()

        if response.status_code // 100 == 2:
            return response.json()
        else:
            raise Exception(
                f"Submission failed ({response.status_code}): {response.text}"
            )

    def get_my_submissions(self) -> List[Dict[str, Any]]:
        if not self.token:
            raise Exception("Please login first.")

        response = requests.get(
            f"{self.base_url}/submissions/my", headers=self._get_headers()
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Failed to fetch submissions ({response.status_code}): {response.text}"
            )

    def get_tasks(self) -> List[Dict[str, Any]]:
        if not self.token:
            raise Exception("Пожалуйста, сначала авторизуйтесь.")

        response = requests.get(f"{self.base_url}/tasks/", headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Не удалось получить список задач ({response.status_code}): {response.text}"
            )
