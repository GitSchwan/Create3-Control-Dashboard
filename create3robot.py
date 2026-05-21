import asyncio
import queue

from irobot_edu_sdk.backend.bluetooth import Bluetooth
from irobot_edu_sdk.robots import Create3, event

from app_logger import add_log, configure_logger


def run_robot(command_queue, shared_state, shared_logs):
    configure_logger(shared_logs)

    print("Starting robot process...")
    shared_state["status"] = "Starting robot process"

    try:
        robot_main(command_queue, shared_state)

    except asyncio.CancelledError:
        shared_state["status"] = "Robot process stopped"
        print("Robot process stopped.")

    except KeyboardInterrupt:
        shared_state["status"] = "Robot process interrupted"
        print("Robot process interrupted by user.")

    except Exception as error:
        shared_state["status"] = "Robot process crashed"
        print(f"Unexpected robot process error: {error}")
        add_log(f"Unexpected robot process error: {error}")


def robot_main(command_queue, shared_state):
    def robot_connect() -> Create3 | None:
        try:
            print("Creating robot object...")
            add_log("Creating robot object...")
            return Create3(Bluetooth())

        except Exception as error:
            print(f"Connection object creation error: {error}")
            add_log(f"Connection object creation error: {error}")
            return None

    robot = robot_connect()

    if robot is None:
        print("Shutting robot process down...")
        shared_state["status"] = "Failed to create robot connection"
        return

    shared_state["status"] = "Robot object created"
    shared_state.setdefault("bumper_left", False)
    shared_state.setdefault("bumper_right", False)
    shared_state.setdefault("battery", None)
    shared_state.setdefault("ir", None)

    #Bumper sensors

    @event(robot.when_bumped, [False, True])
    async def right_bumper():
        shared_state["bumper_right"] = True
        shared_state["status"] = "Right bumper triggered"

    @event(robot.when_bumped, [True, False])
    async def left_bumper():
        shared_state["bumper_left"] = True
        shared_state["status"] = "Left bumper triggered"

    @event(robot.when_bumped, [True, True])
    async def both_bumpers():
        shared_state["bumper_left"] = True
        shared_state["bumper_right"] = True
        shared_state["status"] = "Both bumpers triggered"

    #Cliff sensors

    @event(robot.when_cliff_sensor, [True, False, False, False])
    async def cliff():
        shared_state["cliff"] = [True, False, False, False]

    @event(robot.when_cliff_sensor, [False, True, False, False])
    async def cliff():
        shared_state["cliff"] = [False, True, False, False]

    @event(robot.when_cliff_sensor, [False, False, True, False])
    async def cliff():
        shared_state["cliff"] = [False, False, True, False]

    @event(robot.when_cliff_sensor, [False, False, False, True])
    async def cliff():
        shared_state["cliff"] = [False, False, False, True]

    @event(robot.when_cliff_sensor, [True, True, True, True])
    async def cliff():
        shared_state["cliff"] = [True, True, True, True]

    async def handle_command(command):
        if not isinstance(command, dict):
            print(f"Ignoring invalid command: {command}")
            add_log(f"Ignoring invalid command: {command}")
            return

        action = command.get("action")

        try:
            if action == "forward":
                shared_state["status"] = "Moving forward"
                await robot.move(10)

            elif action == "backward":
                shared_state["status"] = "Moving backward"
                await robot.move(-10)

            elif action == "stop":
                shared_state["status"] = "Stopping"
                await robot.move(0)
                shared_state["status"] = "Stopped"

            elif action == "turn_left":
                shared_state["status"] = "Turning left"
                await robot.turn_left(45)
                shared_state["status"] = "Turned left"

            elif action == "turn_right":
                shared_state["status"] = "Turning right"
                await robot.turn_right(45)
                shared_state["status"] = "Turned right"

            elif action == "dock":
                shared_state["status"] = "Docking"
                add_log("Docking...")
                await robot.dock()
                shared_state["status"] = "Docked"
                add_log("Docked.")

            elif action == "undock":
                shared_state["status"] = "Undocking"
                add_log("Undocking...")
                await robot.undock()
                shared_state["status"] = "Undocked"
                add_log("Undocked.")

            elif action == "set_color":
                r = command["color"]["rgb"]["r"]
                g = command["color"]["rgb"]["g"]
                b = command["color"]["rgb"]["b"]
                await robot.set_lights_on_rgb(r, g, b)

            else:
                add_log(f"Ignoring unknown action: {action}")

        except asyncio.CancelledError:
            raise

        except Exception as error:
            shared_state["status"] = "Command failed"
            add_log(f"Command failed for action {action}: {error}")

    async def update_robot_state():
        try:
            battery_value = await robot.get_battery_level()
            shared_state["battery"] = battery_value[1]
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            add_log(f"Could not read battery level: {erro}")

        try:
            ir_values = await robot.get_ir_proximity()
            shared_state["ir"] = [ir_values.sensors[0],ir_values.sensors[1],ir_values.sensors[2],ir_values.sensors[3],
                                  ir_values.sensors[4],ir_values.sensors[5],ir_values.sensors[6]]
            shared_state["bumper_left"] = False
            shared_state["bumper_right"] = False
        except asyncio.CancelledError:
            raise
        except Exception as err:
            add_log(f"Could not read IR proximity: {err}")

    @event(robot.when_play)
    async def play(robot):
        shared_state["status"] = "Connected to robot"
        add_log("Robot play loop started.")
        print("Robot play loop started.")

        while True:
            try:
                try:
                    command = command_queue.get_nowait()
                except queue.Empty:
                    command = None

                if command is not None:
                    await handle_command(command)

                await asyncio.sleep(0.05)
                await update_robot_state()

            except asyncio.CancelledError:
                shared_state["status"] = "Robot play loop cancelled"
                add_log("Robot play loop cancelled.")
                raise

            except Exception as error:
                shared_state["status"] = "Robot loop error"
                add_log(f"Error in robot play loop: {error}")
                await asyncio.sleep(0.2)

    try:
        shared_state["status"] = "Starting robot.play"
        add_log("Starting robot.play...")
        print("Starting robot.play...")

        robot.play()

        shared_state["status"] = "robot.play finished"
        add_log("robot.play finished.")
        print("robot.play finished.")

    except asyncio.CancelledError:
        shared_state["status"] = "Robot main cancelled"
        add_log("Robot main was cancelled.")
        raise

    except KeyboardInterrupt:
        shared_state["status"] = "Robot main interrupted"
        add_log("Robot main interrupted by user.")

    except Exception as error:
        shared_state["status"] = "Robot play failed"
        add_log(f"Robot play failed: {error}")
        print(f"Robot play failed: {error}")
