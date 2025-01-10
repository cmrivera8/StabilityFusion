from pyqtgraph.parametertree import Parameter, ParameterTree

class ParameterTreeWidget(ParameterTree):
    def __init__(self):
        super().__init__()

        self.params_changing = False

        params = [
            {'name': 'Data acquisition', 'type': 'group', 'children': [
                {'name': 'Start', 'type': 'str', 'value': "now-1h"},
                {'name': 'Stop', 'type': 'str', 'value': "now"},
                {'name': 'Get data', 'type': 'action'},
            ]},
            {'name': 'Data processing', 'type': 'group', 'children': [
                {'name': 'Moving Average', 'type': 'int', 'value': 1},
                {'name': 'Allan deviation', 'type': 'group', 'children': [
                    {'name': 'Start', 'type': 'str', 'value': "2025-01-07 02:58:32"},
                    {'name': 'Stop', 'type': 'str', 'value': "2025-01-07 03:15:12"},
                    {'name': 'Region size', 'type': 'str', 'value': "1000"},
                    {'name': 'Initial tau (s)', 'type': 'str', 'value': ""},
                    {'name': 'Mode', 'type': 'list', 'value': 'Decade', 'limits': ['Decade','Octave','All']},
                    {'name': 'Auto calculate', 'type': 'bool'},
                    {'name': 'Calculate', 'type': 'action'},
                    {'name': 'Zoom region', 'type': 'action'},
                ]},
            ]},
            {'name': 'Global settings', 'type': 'group', 'children': [
                {'name': 'Main measurement', 'type': 'list', 'value': '', 'limits': ['']},
                {'name': 'Plot type', 'type': 'list', 'value': 'Allan deviation', 'limits': ['Allan deviation','Temporal']},
                {'name': 'Show all', 'type': 'action'},
                {'name': 'Hide all', 'type': 'action'},
            ]},
            {'name': 'Presets', 'type': 'group', 'children': [
                {'name': 'Name', 'type': 'list', 'value': 'Default', 'limits': ['Default','New']},
                {'name': 'Save', 'type': 'action'},
                {'name': 'Load', 'type': 'action'},
                {'name': 'Remove', 'type': 'action'},
            ]},
        ]
        self.param = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.param, showTop=False)