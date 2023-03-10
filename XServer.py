import socket
import logging
import ssl
import sys
import threading
import yaml

buffer_size = 1024


def parse_input_argument():
    xsfile = open('XServerConfig.yml', 'r')
    args = yaml.safe_load(xsfile)
    return args


def read_from_tcp_sock(sock):
    buff = bytearray()
    buffer = sock.recv(buffer_size)
    while len(buffer) == buffer_size:
        buff += buffer
        buffer = sock.recv(buffer_size)
    buff += buffer
    return buff.decode().strip(' ').encode()


def send_to_tcp_socket(sock, message):
    if len(message) % buffer_size == 0:
        message += ' '
    index = 0
    while index + buffer_size < len(message):
        sock.send(message[index:index + buffer_size].encode())
        index += buffer_size
    sock.send(message[index:len(message)].encode())


def read_from_udp_sock(sock):
    buff = bytearray()
    buffer, address = sock.recvfrom(buffer_size)
    while len(buffer) == buffer_size:
        buff += buffer
        buffer, address = sock.recvfrom(buffer_size)
    buff += buffer
    return buff.decode().strip(' ').encode(), address


def send_to_udp_socket(sock, message, address):
    if len(message) % buffer_size == 0:
        message += ' '
    index = 0
    while index + buffer_size < len(message):
        sock.sendto(message[index:index + buffer_size].encode(), address)
        index += buffer_size
    sock.sendto(message[index:len(message)].encode(), address)


def handle_tcp_conn_recv(stcp_socket):
    while True:
        message = read_from_tcp_sock(stcp_socket)
        logging.info("Message {} received successfully from TCP connection".format(message.decode()))
        header = message[:message.decode().find('$')]
        ipr, portr, ipc, portc = header.decode().split('#')
        portr = int(portr)
        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        send_to_udp_socket(udp_socket, message[message.decode().find('$') + 1:].decode(), (ipr, portr))
        logging.info("Message {} sent successfully to UDP connection".format(message.decode()))
        threading.Thread(target=handle_udp_conn_recv_tcp_send, args=(stcp_socket, udp_socket, header, )).start()


def handle_udp_conn_recv_tcp_send(stcp_socket, udp_socket, header):
    while True:
        main_message, address = read_from_udp_sock(udp_socket)
        logging.info("Message {} received successfully from UDP connection".format(main_message.decode()))
        message = header.decode() + '$' +main_message.decode()
        send_to_tcp_socket(stcp_socket, message)
        logging.info("Message {} sent successfully to TCP connection".format(message))


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

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(tcp_server_addr)
        s.listen(5)
    except socket.error as e:
        logging.error("(Error) Error openning the UDP socket: {}".format(e))
        logging.error(
            "(Error) Cannot open the UDP socket {}:{} or bind to it".format(tcp_server_ip, tcp_server_port))
        sys.exit(1)
    else:
        logging.info("Bind to the UDP socket {}:{}".format(tcp_server_ip, tcp_server_port))

    while True:
        conn, address = s.accept()
        safe_socket = ssl.wrap_socket(conn, server_side=True, certfile='server.crt', keyfile='server.key',
                                      ssl_version=ssl.PROTOCOL_TLS)
        threading.Thread(target=handle_tcp_conn_recv, args=(safe_socket, )).start()



