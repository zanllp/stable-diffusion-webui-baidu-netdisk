import asyncio
import datetime
import os
from typing import Dict, Literal
import uuid
import re
import subprocess
from scripts.bin import bin_file_path


class BaiduyunTask:
    def __init__(
        self,
        subprocess: asyncio.subprocess.Process,
        type: Literal["upload", "download"],
        send_dirs: str,
        recv_dir: str,
    ):
        self.subprocess = subprocess
        self.id = str(uuid.uuid4())
        self.start_time = datetime.datetime.now()
        self.running = True
        self.logs = []
        self.raw_logs = []
        self.files_state = {}
        self.type = type
        self.send_dirs = send_dirs
        self.recv_dir = recv_dir
        self.n_files = 0
        self.n_success_files = 0
        self.n_failed_files = 0

    def start_time_human_readable(self):
        return self.start_time.strftime("%Y-%m-%d %H:%M:%S")

    def update_state(self):
        self.n_files = 0
        self.n_success_files = 0
        self.n_failed_files = 0
        for key in self.files_state:
            status = self.files_state[key]["status"]
            self.n_files += 1
            if status == "upload-success" or status == "file-skipped":
                self.n_success_files += 1
            elif status == "upload-failed":
                self.n_failed_files += 1
        self.running = not isinstance(self.subprocess.returncode, int)

    def append_log(self, parsed_log, raw_log):
        self.raw_logs.append(raw_log)
        self.logs.append(parsed_log)
        if isinstance(parsed_log, dict) and "id" in parsed_log:
            self.files_state[parsed_log["id"]] = parsed_log

    def get_summary(task):
        return {
            "type": task.type,
            "id": task.id,
            "running": task.running,
            "start_time": task.start_time_human_readable(),
            "recv_dir": task.recv_dir,
            "send_dirs": task.send_dirs,
            "n_files": task.n_files,
            "n_failed_files": task.n_failed_files,
            "n_success_files": task.n_success_files,
        }

    @staticmethod
    async def create(
        type: Literal["upload", "download"], send_dirs: str, recv_dir: str
    ):
        if type not in ["upload", "download"]:
            raise Exception("????????????")
        process = await asyncio.create_subprocess_exec(
            bin_file_path,
            type,
            *process_path_arr(str(send_dirs).split(",")),
            parse_and_replace_time(recv_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        task = BaiduyunTask(process, type, send_dirs, recv_dir)
        task.update_state()
        baiduyun_task_cache[task.id] = task
        return task

    @staticmethod
    def get_by_id(id: str):
        return baiduyun_task_cache.get(id)

    @staticmethod
    def get_cache():
        return baiduyun_task_cache


baiduyun_task_cache: Dict[str, BaiduyunTask] = {}

def process_path_arr(path_arr):
    """
    ?????????????????????????????????
    ????????????????????????????????????
    ????????????????????????????????????????????????????????????
    """
    cwd = os.getcwd()
    result = []
    for path in path_arr:
        if os.path.isabs(path):
            result.append(path)
        else:
            result.append(os.path.join(cwd, path))
    return list(map(parse_and_replace_time, result))

def parse_and_replace_time(s):
    pattern = r'<#(.+?)#>'
    matches = re.findall(pattern, s)
    for match in matches:
        formatted_time = datetime.datetime.now().strftime(match)
        s = s.replace(f'<#{match}#>', formatted_time)
    return s