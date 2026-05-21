from dash import Dash, html, dcc, Input, Output, State
import plotly.graph_objects as go
import asyncio
from app_logger import add_log, get_logs_as_text, configure_logger

# global state
last_command = "None"
connected_robot = None

def run_dashboard(command_queue, shared_state, shared_logs) -> None:
    configure_logger(shared_logs)


    app = Dash()

    #layout of the app
    app.layout = html.Div(className="app-container", children=[
            html.H1("iRobot Create 3 Control Center"),

            #auto refresh
            dcc.Interval(id="interval", interval=500, n_intervals=0),

            #command storage
            dcc.Store(id="command-store"),

            #top section
            html.Div(className="top-section", children=[
                    #sensor values
                    html.Div(className="card sensor-card", children=[
                            html.H3("Sensor Status"),
                            html.Div(id="sensor-values"),
                        ],),
                    #battery
                    html.Div(
                        className="card battery-card",
                        children=[
                            html.H3("Battery"),
                            html.Div(id="battery-status"),
                        ],),
                    #cliff sensors
                    html.Div(className="card cliff-card", children=[
                            html.H3("Cliff Sensors"),
                            html.Div(id="cliff-status"),
                        ],),
                ],
            ), #top section Close

            html.Br(),

            #ir chart
            html.Div(className="card", children=[
                    html.H3("IR Proximity Sensors"),
                    dcc.Graph(id="ir-chart"),
                ],),

            html.Br(),

            #controls
            html.Div(className="card", children=[
                    html.H3("Controls"),
                    html.Div(className="controls", children=[
                            html.Button("Forward", id="btn-forward", n_clicks=0),
                            html.Button("Backward", id="btn-backward", n_clicks=0),
                            html.Button("Turn Left", id="btn-left", n_clicks=0),
                            html.Button("Turn Right", id="btn-right", n_clicks=0),
                            html.Button("Stop", id="btn-stop", n_clicks=0),
                            html.Button("Dock", id="btn-dock", n_clicks=0),
                            html.Button("Undock", id="btn-undock", n_clicks=0),
                        ],),
                    html.Br(),
                    html.Div(id="last-command", children="Last command: None"),
                ],), #controls close

            html.Br(),

            #log
            html.Div(className="card", children=[
                    html.H3("Event Log"),
                    html.Div(id="log-output", className="log-output",),
            ],),
        ],)

    def get_robot_data() -> dict:
        return {
            "bumper_left": shared_state.get("bumper_left", False),
            "bumper_right": shared_state.get("bumper_right", False),
            "ir": shared_state.get("ir", [0, 0, 0, 0, 0, 0, 0]),
            "battery": shared_state.get("battery", 0),
            "cliff": shared_state.get("cliff", [False, False, False, False]),
        }


    @app.callback(
        Output("sensor-values", "children"),
        Output("battery-status", "children"),
        Output("cliff-status", "children"),
        Output("ir-chart", "figure"),
        Output("log-output", "children"),
        Input("interval", "n_intervals"),
    )
    def update_dashboard(_):
        try:
            data = get_robot_data()
        except Exception as er:
            add_log(f"Dashboard update failed: {er}")
            data = {
                "bumper_left": "N/A",
                "bumper_right": "N/A",
                "ir": [0, 0, 0, 0, 0, 0, 0],
                "battery": 0,
                "cliff": [0, 0, 0, 0],
            }

        # sensor text
        sensor_text = [
            html.Div(f"Bumper Left: {data['bumper_left']}"),
            html.Div(f"Bumper Right: {data['bumper_right']}"),
        ]

        for index, value in enumerate(data["ir"]):
            sensor_text.append(html.Div(f"IR {index + 1}: {value}"))

        # battery
        battery_value = int(data["battery"] or 0)

        battery = html.Div(
            [
                html.Div(f"{battery_value}%"),
                html.Progress(
                    value=str(battery_value),
                    max="100",
                    className="battery-progress",
                ),
            ]
        )

        # cliff sensors
        cliff = [html.Div(f"Sensor {i}: {value}") for i, value in enumerate(data["cliff"])]

        # chart
        fig = go.Figure(
            data=[
                go.Bar(
                    x=[f"IR {i + 1}" for i in range(len(data["ir"]))],
                    y=data["ir"],
                )
            ]
        )

        fig.update_layout(
            height=350,
            margin=dict(l=40, r=40, t=20, b=40),
            yaxis_title="Value",
        )

        # log output
        log_output = get_logs_as_text()

        return sensor_text, battery, cliff, fig, log_output

    @app.callback(
        Output("last-command", "children"),
        Input("btn-forward", "n_clicks"),
        Input("btn-backward", "n_clicks"),
        Input("btn-left", "n_clicks"),
        Input("btn-right", "n_clicks"),
        Input("btn-stop", "n_clicks"),
        Input("btn-dock", "n_clicks"),
        Input("btn-undock", "n_clicks"),
        prevent_initial_call=True)
    def handle_buttons(*_):
        from dash import callback_context

        button_id = callback_context.triggered[0]["prop_id"].split(".")[0]

        commands = {
            "btn-forward": "Forward",
            "btn-backward": "Backward",
            "btn-left": "Turn Left",
            "btn-right": "Turn Right",
            "btn-stop": "Stop",
            "btn-dock": "Dock",
            "btn-undock": "Undock",
        }
        command = commands[button_id]

        if command == "Forward":
            command_queue.put({"action": "forward"})
        elif command == "Backward":
            command_queue.put({"action": "backward"})
        elif command == "Turn Left":
            command_queue.put({"action": "turn_left"})
        elif command == "Turn Right":
            command_queue.put({"action": "turn_right"})
        elif command == "Stop":
            command_queue.put({"action": "stop"})
        elif command == "Dock":
            command_queue.put({"action": "dock"})
        elif command == "Undock":
            command_queue.put({"action": "undock"})

        add_log(f"Command executed: {command}")

        return f"Last command: {command}"

    app.run(debug=True, use_reloader=False, host="127.0.0.1", port=8050)