import socket

buffer_size = 1024

if __name__ == '__main__':

    udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    while True:
        udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        udp_socket.bind(('127.0.0.1', 6374))
        message, address = udp_socket.recvfrom(buffer_size)

        try:
            a = eval(message.decode())
        except Exception as e:
            a = ''
            pass
        udp_socket.sendto(str(a).encode(), address)