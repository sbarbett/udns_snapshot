import time

class TaskHandler:
    def __init__(self, client):
        self.client = client

    def check(self, task_id: str) -> dict:
        """Check the status of a task.

        Args:
        - task_id (str): The task ID.

        Returns:
        - dict: The task status.
        """
        return self.client.get(f"/tasks/{task_id}")

    def wait(self, task_id: str, poll_interval: int = 10) -> dict:
        """Wait for a task to complete. This function will poll the task status every poll_interval seconds until the task
        is no longer in progress.

        Args:
        - task_id (str): The task ID.
        - poll_interval (int): The number of seconds to wait between polling the task status.

        Returns:
        - dict: The task status.
        """
        while True:
            task_status = self.check(task_id)
            if task_status['code'] != 'IN_PROCESS':
                break
            time.sleep(poll_interval)
        return task_status

    def result(self, task_id: str) -> dict:
        """Get the result of a task.

        Args:
        - task_id (str): The task ID.

        Returns:
        - dict: The task result.
        """
        return self.client.get(f"/tasks/{task_id}/result")
