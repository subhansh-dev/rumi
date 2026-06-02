"""Entry point: python -m rumi_gateway"""
from rumi_gateway.server import GatewayServer

if __name__ == '__main__':
    server = GatewayServer()
    server.start()
