from multiprocessing import Process, Queue, Manager
from dashboard import run_dashboard
from create3robot import run_robot


if __name__ == "__main__":
    manager = Manager() #ini SyncManager object which can be used for sharing objects between processes.
    command_queue = Queue() #ini queue | put(obj[, block[, timeout]]) | get(block[, timeout])
    shared_logs = manager.list()

    shared_state = manager.dict({
        "battery": 0,
        "status": "Disconnected",
        "bumper_left": False,
        "bumper_right": False,
        "ir": [0, 0, 0, 0, 0, 0, 0],
        "cliff": [False] * 4,
    })

    dashboard_process = Process(
        target=run_dashboard,
        args=(command_queue, shared_state, shared_logs)
    )

    robot_process = Process(
        target=run_robot,
        args=(command_queue, shared_state, shared_logs)
    )

    dashboard_process.start()
    robot_process.start()

    dashboard_process.join()
    robot_process.join()