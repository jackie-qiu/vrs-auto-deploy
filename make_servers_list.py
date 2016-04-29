"""Build server list file server.txt."""

if __name__ == "__main__":

    servers = []

    for i in range(1, 101):
        server = "172.16.169.%s:root:As_9sx_X" % (i)
        servers.append(server)

    server_list = '\n'.join(str(server)[:] for server in servers)

    with open('server.txt', 'w') as f:
        f.write(server_list)

    f.close()
