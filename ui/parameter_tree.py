from pyqtgraph.parametertree import Parameter, ParameterTree

class ParameterTreeWidget(ParameterTree):
    def __init__(self):
        super().__init__()

        params = [
            {'name': 'Data acquisition', 'type': 'group', 'children': [
                {'name': 'Start', 'type': 'str', 'value': "2024-12-05 17:45:04"},
                {'name': 'Stop', 'type': 'str', 'value': "2024-12-05 19:26:07"},
                {'name': 'Get data', 'type': 'action'},
            ]},
            {'name': 'Data processing', 'type': 'group', 'children': [
                {'name': 'Moving Average', 'type': 'int', 'value': 5},
            ]}
        ]
        self.param = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.param, showTop=False)

    def connect_get_data_action(self, callback):
        self.param.child('Data acquisition', 'Get data').sigActivated.connect(callback)