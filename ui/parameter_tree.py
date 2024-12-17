from pyqtgraph.parametertree import Parameter, ParameterTree

class ParameterTreeWidget(ParameterTree):
    def __init__(self):
        super().__init__()

        self.params_changing = False

        params = [
            {'name': 'Data acquisition', 'type': 'group', 'children': [
                {'name': 'Start', 'type': 'str', 'value': "2024-12-12 15:34:33"},
                {'name': 'Stop', 'type': 'str', 'value': "2024-12-12 15:40:46"},
                {'name': 'Get data', 'type': 'action'},
            ]},
            {'name': 'Data processing', 'type': 'group', 'children': [
                {'name': 'Moving Average', 'type': 'int', 'value': 1},
                {'name': 'Allan deviation', 'type': 'group', 'children': [
                    {'name': 'Start', 'type': 'str', 'value': "2024-12-12 15:34:33"},
                    {'name': 'Stop', 'type': 'str', 'value': "2024-12-12 15:40:46"},
                    {'name': 'Region size', 'type': 'str', 'value': "1000"},
                    {'name': 'Mode', 'type': 'list', 'value': 'Decade', 'limits': ['Decade','Octave','All']},
                    {'name': 'Auto calculate', 'type': 'bool'},
                    {'name': 'Calculate', 'type': 'action'},
                    {'name': 'Zoom region', 'type': 'action'},
                ]},
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