import socket

buffer_size = 1024

if __name__ == '__main__':

    udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    while True:
        a = input('Please Enter Input : ')
        udp_socket.sendto(a.encode(), ('127.0.0.1', 6324))
        res, address = udp_socket.recvfrom(buffer_size)
        print(res.decode())