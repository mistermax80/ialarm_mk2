"""File for util funcions."""

import asyncio


def get_active_tasks(prefix:str) -> str:
    """Retrive string within list of task starting with prefix."""
    tasks = ""
    for t in asyncio.all_tasks():
        name = t.get_name()  # Python 3.8+ ha get_name()
        if name.startswith(prefix):
            tasks += name + "\n"
    return tasks
