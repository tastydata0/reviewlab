import requests
import os
from typing import Optional, Dict, List, Any
from .auth import load_token

# URL of our FastAPI backend
BASE_URL = "http://localhost:8080/api"


class Client:
    def __init__(self):
        self.token = load_token()

    def _get_headers(self):
        if not self.token:
            return {}
        return {"Authorization": f"Bearer {self.token}"}

    def login(self, email: str, password: str) -> Optional[str]:
        try:
            response = requests.post(
                f"{BASE_URL}/users/login",
                json={
                    "email": email,
                    "password": password,
                    "expires_in": 120,
                },  # 2 hours
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
                f"{BASE_URL}/submissions/",
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
            f"{BASE_URL}/submissions/my", headers=self._get_headers()
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

        response = requests.get(f"{BASE_URL}/tasks/", headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(
                f"Не удалось получить список задач ({response.status_code}): {response.text}"
            )
