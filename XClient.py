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
import yaml

buffer_size = 1024


def parse_input_argument():
    xcfile = open('XClientConfig.yml', 'r')
    args = yaml.safe_load(xcfile)
    return args


def read_from_tcp_sock(sock):
    """Just for read n byte  from tcp socket"""
    buff = bytearray()
    buffer = sock.recv(buffer_size)
    while len(buffer) == buffer_size:
        buff += buffer
        buffer = sock.recv(buffer_size)
    buff += buffer
    return buff


def send_to_tcp_socket(sock, message):
    index = 0
    while index + buffer_size <= len(message):
        sock.send(message[index:index + buffer_size].encode())
        index += buffer_size
    sock.send(message[index:len(message)].encode())


def handle_tcp_conn_recv(stcp_socket, udp_socket):
    """
    read from tcp socket for the UDP segment received through the tunnel,
    then forward received segment to incom_udp_addr
    """
    while True:
        message = read_from_tcp_sock(stcp_socket)
        header = message[:message.decode().find('_')]
        ipr, portr, ipc, portc = header.decode().split('-')
        portc = int(portc)
        udp_socket.sendto(message[message.decode().find('_') + 1:], (ipc, portc))


def handle_tcp_conn_send(stcp_socket, rmt_udp_addr, client_udp_addr, udp_to_tcp_queue):
    """
    get remote UDP ip and port(rmt_udp_addr) and Concat them then sending it to the TCP socket
    after that read from udp_to_tcp_queue for sending a UDP segment and update queue,
    don't forgot to block the queue when you are reading from it.
    """
    while True:
        main_message = udp_to_tcp_queue.get(block=True)
        header = rmt_udp_addr[0] + '-' + str(rmt_udp_addr[1]) + '-' +\
                 client_udp_addr[0] + '-' + str(client_udp_addr) + '_'
        message: str = header + main_message.decode()
        send_to_tcp_socket(stcp_socket, message)


def handle_udp_conn_recv(udp_socket, tcp_server_addr, rmt_udp_addr):
    """
        This function should be in while True,
        Receive a UDP packet form incom_udp_addr.
        It also keeps the associated thread for handling tcp connections in udp_conn_list,
        if incom_udp_addr not in udp_conn_list, Recognize a new UDP connection from incom_udp_addr. So establish a TCP connection to the remote server for it
        and if incom_udp_addr in udp_conn_list you should continue sending in esteblished socekt  ,
        you need a queue for connecting udp_recv thread to tcp_send thread.
    """
    udp_remote_mapping = {}
    while True:
        message, address = udp_socket.recvfrom(buffer_size)
        if address not in udp_remote_mapping.keys():
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations('cer.pem')
            tcp_safe_socket = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                                                  server_hostname=tcp_server_addr[0])
            try:
                tcp_safe_socket.connect(tcp_server_addr)
            except socket.error as e:
                logging.error("(Error) Error openning the TCP socket: {}".format(e))
                logging.error(
                    "(Error) Cannot open the TCP socket {}:{} or bind to it".format(tcp_server_addr[0],
                                                                                    tcp_server_addr[1]))
                sys.exit(1)
            else:
                logging.info("Bind to the TCP socket {}:{}".format(tcp_server_addr[0], tcp_server_addr[1]))

            tcp_queue = mp.Queue()
            tcp_queue.put(message)
            udp_remote_mapping[address] = tcp_queue

            threading.Thread(target=handle_tcp_conn_send, args=(tcp_safe_socket, rmt_udp_addr, tcp_queue)).start()

            threading.Thread(target=handle_tcp_conn_recv, args=(tcp_safe_socket, udp_socket)).start()
        else:
            udp_remote_mapping[address].put(message)


if __name__ == "__main__":
    args = parse_input_argument()

    tcp_server_ip = args['server'][0]
    tcp_server_port = args['server'][1]
    tcp_server_addr = (tcp_server_ip, tcp_server_port)

    if args['verbosity'] == 'error':
        log_level = logging.ERROR
    elif args['verbosity'] == 'info':
        log_level = logging.INFO
    elif args['verbosity'] == 'debug':
        log_level = logging.DEBUG
    format = "%(asctime)s: (%(levelname)s) %(message)s"
    logging.basicConfig(format=format, level=log_level, datefmt="%H:%M:%S")

    for tun_addr in args['udp_tunnel']:
        udp_listening_ip = tun_addr[0]
        udp_listening_port = tun_addr[1]
        rmt_udp_ip = tun_addr[2]
        rmt_udp_port = tun_addr[3]
        rmt_udp_addr = (rmt_udp_ip, rmt_udp_port)

        try:
            udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
            udp_socket.bind((udp_listening_ip, udp_listening_port))
        except socket.error as e:
            logging.error("(Error) Error openning the UDP socket: {}".format(e))
            logging.error(
                "(Error) Cannot open the UDP socket {}:{} or bind to it".format(udp_listening_ip, udp_listening_port))
            sys.exit(1)
        else:
            logging.info("Bind to the UDP socket {}:{}".format(udp_listening_ip, udp_listening_port))

        mp.Process(target=handle_udp_conn_recv,
                   args=(udp_socket, tcp_server_addr, rmt_udp_addr)).start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Closing the TCP connection...")
