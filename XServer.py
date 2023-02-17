import multiprocessing as mp
import socket
import logging
# import numpy as np
from queue import Queue
import ssl
import time
import sys
import argparse
import random
import time
import threading

buffer_size = 1024


def parse_input_argument():
    parser = argparse.ArgumentParser(description='This is a client program that create a tunnel\
                                                  to the server over various TCP connections.')

    parser.add_argument('-ut', '--udp-tunnel', action='append', required=True,
                        help="Make a tunnel from the client to the server. The format is\
                              'listening ip:listening port:remote ip:remote port'.")
    parser.add_argument('-s', '--server', required=True,
                        help="The IP address and (TCP) port number of the tunnel server.\
                               The format is 'server ip:server port'.")
    parser.add_argument('-v', '--verbosity', choices=['error', 'info', 'debug'], default='info',
                        help="Determine the verbosity of the messages. The default value is 'info'.")

    args = parser.parse_args()
    return args


def read_from_tcp_sock(sock):
    buff = bytearray()
    buffer = sock.recv(buffer_size)
    while len(buffer) == buffer_size:
        buff += buffer
        buffer = sock.recv(buffer_size)
    buff += buffer
    return buff


def handle_tcp_conn_recv(stcp_socket):
    while True:
        message = read_from_tcp_sock(stcp_socket)
        header = message[:message.decode().find('_')]
        ipr, portr, ipc, portc = header.decode().split('-')
        portr = int(portr)
        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_socket.sendto(message[message.decode().find('_') + 1:], (ipr, portr))
        threading.Thread(target=handle_udp_conn_recv_tcp_send, args=(stcp_socket, udp_socket, header, )).start()


def handle_udp_conn_recv_tcp_send(stcp_socket, udp_socket, header):
    while True:
        main_message, address = udp_socket.recvfrom(buffer_size)
        message = header + main_message
        stcp_socket.send(message.encode())


if __name__ == "__main__":
    args = parse_input_argument()

    tcp_server_ip = args.server.split(':')[0]
    tcp_server_port = int(args.server.split(':')[1])
    tcp_server_addr = (tcp_server_ip, tcp_server_port)

    if args.verbosity == 'error':
        log_level = logging.ERROR
    elif args.verbosity == 'info':
        log_level = logging.INFO
    elif args.verbosity == 'debug':
        log_level = logging.DEBUG
    format = "%(asctime)s: (%(levelname)s) %(message)s"
    logging.basicConfig(format=format, level=log_level, datefmt="%H:%M:%S")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain('cert.pem', 'key.pem')

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 1234))
    s.listen()

    while True:
        conn, address = s.accept()
        safe_socket = context.wrap_socket(conn, server_hostname=tcp_server_addr[0])



