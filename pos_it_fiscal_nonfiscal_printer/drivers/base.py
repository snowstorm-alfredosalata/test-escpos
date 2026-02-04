# Base driver and minimal action dispatching

class BaseDriver:
    def __init__(self, printer=None, env=None, escpos_factory=None, socket_factory=None, iot_proxy=None):
        self.printer = printer
        self.env = env
        self.escpos_factory = escpos_factory
        self.socket_factory = socket_factory
        self.iot_proxy = iot_proxy

    def handle_action(self, action, payload):
        if action == 'print_receipt':
            return self.print_receipt(payload)
        elif action == 'cashbox':
            return self.open_cashbox(payload)
        else:
            raise NotImplementedError(action)

    def print_receipt(self, payload):
        raise NotImplementedError

    def open_cashbox(self, payload):
        # Default: no-op
        return {'result': True, 'info': 'no_op'}
