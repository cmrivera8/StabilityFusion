from pyqtgraph.parametertree import Parameter, ParameterTree

class ParameterTreeWidget(ParameterTree):
    def __init__(self):
        super().__init__()

        params = [
            {'name': 'Plot Settings', 'type': 'group', 'children': [
                {'name': 'Enable Grid', 'type': 'bool', 'value': True},
                {'name': 'Line Color', 'type': 'color', 'value': 'b'}
            ]},
            {'name': 'Data Processing', 'type': 'group', 'children': [
                {'name': 'Moving Average Window', 'type': 'int', 'value': 5},
                {'name': 'Calculate Allan Deviation', 'type': 'action'},
                {'name': 'Add temporal trace', 'type': 'action'},
            ]}
        ]
        self.param = Parameter.create(name='params', type='group', children=params)
        self.setParameters(self.param, showTop=False)

    def connect_add_trace_action(self, callback):
        self.param.child('Data Processing', 'Add temporal trace').sigActivated.connect(callback)