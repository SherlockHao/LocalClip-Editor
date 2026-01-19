from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Callable, Any
from dataclasses import dataclass
import uuid
from datetime import datetime

@dataclass
class QueuedTask:
    task_id: str
    job_id: str
    language: str
    stage: str
    future: Future
    created_at: datetime

class TaskQueue:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, QueuedTask] = {}

    def submit(
        self,
        task_id: str,
        language: str,
        stage: str,
        func: Callable,
        *args,
        **kwargs
    ) -> str:
        """提交任务到队列"""
        job_id = f"{task_id}_{language}_{stage}_{uuid.uuid4().hex[:8]}"

        future = self.executor.submit(func, *args, **kwargs)

        queued_task = QueuedTask(
            task_id=task_id,
            job_id=job_id,
            language=language,
            stage=stage,
            future=future,
            created_at=datetime.utcnow()
        )

        self.tasks[job_id] = queued_task
        return job_id

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if job_id not in self.tasks:
            return {"status": "not_found"}

        task = self.tasks[job_id]
        if task.future.done():
            try:
                result = task.future.result()
                return {"status": "completed", "result": result}
            except Exception as e:
                return {"status": "failed", "error": str(e)}
        else:
            return {"status": "running"}

    def cancel(self, job_id: str) -> bool:
        """取消任务"""
        if job_id in self.tasks:
            return self.tasks[job_id].future.cancel()
        return False

    def get_task_jobs(self, task_id: str) -> list:
        """获取指定任务的所有作业"""
        return [
            {
                "job_id": job_id,
                "language": task.language,
                "stage": task.stage,
                "status": self.get_status(job_id)["status"]
            }
            for job_id, task in self.tasks.items()
            if task.task_id == task_id
        ]

# 全局任务队列实例
task_queue = TaskQueue(max_workers=4)
