"""Config network interface."""
from __future__ import with_statement
from deploy_vrs import DeployVRS
from deploy_vrs import JsshProcess


def config_bond201(server, ip, gateway):
    """Config bond1.101."""
    p = JsshProcess(server, "", True)
    cmd = "mv /etc/sysconfig/network-scripts/ifcfg-bond1.101 /etc/sysconfig/network-scripts/ifcfg-bond1.201;\
           sed -i 's/^.*IPADDR=.*$/IPADDR=%s/' /etc/sysconfig/network-scripts/ifcfg-bond1.201; \
           sed -i 's/^.*GATEWAY=.*$/GATEWAY=%s/' /etc/sysconfig/network-scripts/ifcfg-bond1.201;\
           sed -i 's/^.*DEVICE=.*$/DEVICE=bond1.201/' /etc/sysconfig/network-scripts/ifcfg-bond1.201;\
           sed -i '/NETMASK/d' /etc/sysconfig/network-scripts/ifcfg-bond1.201;\
           echo 'PREFIX=24' >> /etc/sysconfig/network-scripts/ifcfg-bond1.201"\
           % (ip, gateway)

    p.run_ssh(cmd)


def config_bond204(server, ip):
    """Config bond1.204."""
    p = JsshProcess(server, "", True)

    cmd = "echo 'VLAN=yes' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204; \
           echo 'BOOTPROTO=static' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204;\
           echo 'DEVICE=bond1.204' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204;\
           echo 'ONBOOT=yes' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204;\
           echo 'IPADDR=%s' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204;\
           echo 'PREFIX=24' >> /etc/sysconfig/network-scripts/ifcfg-bond1.204"\
           % (ip)

    p.run_ssh(cmd)


if __name__ == "__main__":

    bond101_ips = []
    bond101_gateway = "10.32.65.254"

    for i in range(1, 250):
        ip = "10.32.65.%s" % (i)
        bond101_ips.append(ip)

    bond204_ips = []

    for i in range(1, 250):
        ip = "10.32.68.%s" % (i)
        bond204_ips.append(ip)

    deploy = DeployVRS(None, "server.txt", False, False)
    servers = deploy.read_servers()

    i = 0
    for server in servers:
        config_bond201(server, bond101_ips[i], bond101_gateway)
        config_bond204(server, bond204_ips[i])
        i = i + 1
