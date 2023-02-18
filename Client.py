import socket

buffer_size = 1024


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


if __name__ == '__main__':

    udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    while True:
        a = input('Please Enter Input : ')
        send_to_udp_socket(udp_socket, a, ('127.0.0.1', 6324))
        res, address = read_from_udp_sock(udp_socket)
        print(res.decode())