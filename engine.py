class VisualEngine:
    def __init__(self, nodes):
        self.nodes = nodes

    def process(self, frame):
        for node in self.nodes:
            frame = node.process(frame)
        return frame
