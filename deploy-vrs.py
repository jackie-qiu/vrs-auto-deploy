# Copyright 2014 Alcatel-Lucent USA Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""The module implements the Nuage VRS deployment."""
from __future__ import with_statement
import sys
import getopt
import multiprocessing
import json

try:
    import pexpect
except ImportError:
    print """
         You must install pexpect module
    """
    sys.exit(1)


class Server(object):

    """The Server that deploy VRS."""

    def __init__(self, host, user_name, password):
        """Constructor."""
        self.host = host
        self.user_name = user_name
        self.password = password

    def __str__(self):
        """Tostring."""
        return self.host


class JsshProcess(object):

    """Class that implements ssh to the KVM servers ."""

    def __init__(self, server, cmd, verbose):
        """Constructor."""
        self.server = server
        self.cmd = cmd
        self.verbose = verbose

    def __ssh_failed(self, child):
        print 'ERROR!'
        print 'SSH could not login. Here is what SSH said:'
        print child.before, child.after
        return child.before

    def __ssh_send_password(self, child):
        child.sendline(self.server.password)
        index = child.expect(pattern=[pexpect.TIMEOUT, 'Permission denied.*', pexpect.EOF], timeout=300)
        if index == 0:
            return False, self.__ssh_failed(child)
        elif index == 1:
            print "Incorrect password on the server %s" % (self.server.host)
            return False, "Incorrect password on the server %s" % (self.server.host)
        else:
            return True, child.before

    def run_ssh(self, cmd):
        """Run ssh command."""
        cli = self.server.user_name + "@" + self.server.host + " " + cmd
        child = pexpect.spawn('ssh %s' % cli)
        # child.logfile_send = sys.stdout
        index = child.expect(pattern=[".*yes/no.*", ".*ssword:", pexpect.TIMEOUT], timeout=30)
        if index == 0:
            child.sendline('yes')
            i = child.expect(pattern=[pexpect.TIMEOUT, '.*ssword:'], timeout=30)
            if i == 0:
                return self.__ssh_failed(child)
            else:
                success, result = self.__ssh_send_password(child)
        elif index == 1:
            success, result = self.__ssh_send_password(child)
        else:
            return self.__ssh_failed(child)
        # child.expect(pattern=pexpect.EOF, timeout=300)
        if self.verbose:
            print "Runing command %s on server %s with result %s." % (self.cmd, self.server, result)

        return result

    def run_scp(self, filename, path):
        """Run scp command."""
        dst = self.server.user_name + "@" + self.server.host + ":" + path
        cli = "scp " + filename + " " + dst
        if self.verbose:
            print cli

        child = pexpect.spawn(cli)
        index = child.expect([".*yes/no.*", ".*ssword:", pexpect.TIMEOUT])
        if index == 0:
            child.sendline('yes')
            i = child.expect([pexpect.TIMEOUT, '.*ssword:'])
            if i == 0:
                return self.__ssh_failed(child)
            else:
                success, result = self.__ssh_send_password(child)
        elif index == 1:
            success, result = self.__ssh_send_password(child)
        else:
            return self.__ssh_failed()
        # child.expect(pexpect.EOF)
        if self.verbose:
            print child.before

        return result


class DeployVRS(object):

    """Class that implements deployment of VRS on KVM servers ."""

    def __init__(self, config_file, servers_file, verbose, is_vrs_g):
        """Constructor."""
        super(DeployVRS, self).__init__()
        self.config_file = config_file
        self.servers_file = servers_file
        self.verbose = verbose
        self.is_vrs_g = is_vrs_g

    def _parse_config(self, conf):
        return Server()

    def read_vrs_config(self):
        """Read the VRS configuration from the json file."""
        with open(self.config_file) as json_file:
            json_data = json.load(json_file)

        return json_data

    def read_servers(self):
        """Read the servers from the file."""
        servers = []
        with open(self.servers_file) as f:
            for line in f:
                info = line.split(':')
                server = Server(info[0], info[1], info[2])
                servers.append(server)

        return servers

    def check(self, server, cmd):
        """Check the Nuage VRS status of the server."""
        p = JsshProcess(server, "", self.verbose)
        if not self.is_vrs_g:
            if self.verbose:
                print "Check status of file /etc/nova/nova.conf on %s." % (server)

            cmd = "ls /etc/nova/nova.conf"
            if self.verbose:
                print cmd
            result = p.run_ssh(cmd)
            if "cannot access" in result:
                error_message = "/etc/nova/nova.conf doesn't exist on server %s." % (server)
                print error_message
                return False, error_message

        if self.verbose:
            print "Check status of file /etc/default/openvswitch on %s." % (server)

        cmd = "ls /etc/default/openvswitch"
        if self.verbose:
            print cmd
        result = p.run_ssh(cmd)
        if("cannot access" in result):
            error_message = "/etc/default/openvswitch doesn't exist on server %s." % (server)
            print error_message
            return False, error_message

        if self.verbose:
            print "Check status of nuage-openvsiwtch service on %s ..." % (server)

        cmd = "/bin/systemctl status openvswitch.service"
        if self.verbose:
            print cmd
        result = p.run_ssh(cmd)
        if("status=0/SUCCESS" not in result):
            error_message = "openvswitch.service status failed on server %s." % (server)
            return False, error_message

        if not self.is_vrs_g:
            print "Execute VRS status checking on server %s success." % (server)
        else:
            print "Execute VRS-G status checking on server %s success." % (server)

        return True, ""

    def __install_rpm(self, server, ssh_session, isupgrade):
        """Install or upgrade Nuage VRS rpms to the servers."""
        print "Scp nuage VRS rpm packages to %s ..." % (server)
        vrs_config = self.read_vrs_config()

        scp_filename = ""
        for rpm_name in vrs_config['rpm']:
            scp_filename = scp_filename + rpm_name + " "
        ssh_session.run_scp(scp_filename, "/root/")
        if not self.is_vrs_g:
            print "Install nuage VRS rpm packages to %s ..." % (server)
        else:
            print "Install nuage VRS-G rpm packages to %s ..." % (server)

        cmd = ""
        for rpm_name in vrs_config['rpm']:
            cmd = cmd + "/root/" + rpm_name + " "
        if self.verbose:
            print cmd
        if isupgrade:
            ssh_session.run_ssh("rpm -Uvh " + cmd)
        else:
            ssh_session.run_ssh("rpm -ivh " + cmd)

    def install(self, server, cmd):
        """Install VRS to the servers."""
        p = JsshProcess(server, "", self.verbose)

        print "Yum install dependent rpm package ..."

        cmd = "yum install -y python-novaclient libvirt \
               python-twisted-core perl-JSON qemu-kvm vconfig \
               perl-Sys-Syslog.x86_64 protobuf-c.x86_64 \
               python-setproctitle.x86_64"
        if self.verbose:
            print cmd
        p.run_ssh(cmd)

        self.__install_rpm(server, p, False)
        if not self.is_vrs_g:
            print "Setting ovs_bridge to alubr0 in nova.conf on server %s..." % (server)
            cmd = "sed -i 's/\^ovs_bridge\.\*/ovs_bridge=alubr0/' /etc/nova/nova.conf"
            if self.verbose:
                print cmd
            p.run_ssh(cmd)

        vrs_config = self.read_vrs_config()

        print "Setting /etc/default/openvswitch config file on server %s..." % (server)
        if self.is_vrs_g:
            cmd = "sed -i 's/\^PERSONALITY\.\*/PERSONALITY=vrs-g/' /etc/default/openvswitch"
            if self.verbose:
                print cmd
            p.run_ssh(cmd)

        cmd = "sed -i 's/\^NETWORK_UPLINK_INTF\.\*/NETWORK_UPLINK_INTF=%s/' /etc/default/openvswitch; \
               sed -i 's/^.*ACTIVE_CONTROLLER=.*$/ACTIVE_CONTROLLER=%s/' /etc/default/openvswitch;\
               sed -i 's/^.*STANDBY_CONTROLLER=.*$/STANDBY_CONTROLLER=%s/' /etc/default/openvswitch;\
               sed -i 's/^.*BRIDGE_MTU=.*$/BRIDGE_MTU=1600/' /etc/default/openvswitch"\
               % (vrs_config['network_uplink_intf'], vrs_config['active_controller'], vrs_config['standby_controller'])
        if self.verbose:
            print cmd
        p.run_ssh(cmd)

        if not self.is_vrs_g:
            print "Restart openstack-nova-compute service on %s ..." % (server)

            cmd = "/bin/systemctl restart openstack-nova-compute.service"
            if self.verbose:
                print cmd
            p.run_ssh(cmd)

        print "Restart nuage-openvsiwtch service on %s ..." % (server)

        cmd = "/bin/systemctl restart openvswitch.service"
        if self.verbose:
            print cmd
        p.run_ssh(cmd)

        print "Check status of nuage-openvsiwtch service on %s ..." % (server)
        cmd = "/bin/systemctl status openvswitch.service"
        if self.verbose:
            print cmd
        result = p.run_ssh(cmd)
        if "status=0/SUCCESS" in result:
            if not self.is_vrs_g:
                print "Execute VRS install on server %s success." % (server)
            else:
                print "Execute VRS-G install on server %s success." % (server)
            return True, ""
        return False, result

    def uninstall(self, server, cmd):
        """Uninstall VRS on the servers."""
        p = JsshProcess(server, "", self.verbose)

        cli = "/bin/systemctl stop openvswitch.service"
        if self.verbose:
            print cli
        p.run_ssh(cli)

        cli = "rpm -qa | grep nuage"
        if self.verbose:
            print cli
        result = p.run_ssh(cli)
        nuage_rpms = result.split('\r\n')
        uninstalled_rpms = []
        for rpms in nuage_rpms:
            if "nuage-metadata" in rpms:
                uninstalled_rpms.insert(0, rpms)
                continue
            if "nuage" in rpms:
                uninstalled_rpms.append(rpms)

        for rpms in uninstalled_rpms:
            cli = "rpm -e " + rpms
            if self.verbose:
                print cli
            p.run_ssh(cli)

        if not self.is_vrs_g:
            print "Execute VRS uninstall on server %s success." % (server)
        else:
            print "Execute VRS-G uninstall on server %s success." % (server)

        return True, ""

    def upgrade(self, server, cmd):
        """Upgrate VRS on the servers."""
        p = JsshProcess(server, "", self.verbose)

        self.__install_rpm(server, p, True)

        print "Restart nuage-openvsiwtch service on %s ..." % (server)

        cmd = "/bin/systemctl restart openvswitch.service"
        if self.verbose:
            print cmd
        p.run_ssh(cmd)

        print "Check status of nuage-openvsiwtch service on %s ..." % (server)
        cmd = "/bin/systemctl status openvswitch.service"
        if self.verbose:
            print cmd
        result = p.run_ssh(cmd)
        if "status=0/SUCCESS" in result:
            if not self.is_vrs_g:
                print "Execute VRS install on server %s success." % (server)
            else:
                print "Execute VRS-G install on server %s success." % (server)
            return True, ""
        return False, result

    def exec_cmd(self, server, cmd):
        """Exec command on the servers."""
        p = JsshProcess(server, cmd, self.verbose)
        p.run_ssh(cmd)
        print "Execute ssh command %s on server %s success." % (cmd, server)
        return True, ""

help_str = """Nuage VRS deployment utility on RHEL7/Centos7
usage: python deploy-vrs.py [-c|--command] [install|uninstall|upgrade|cli|check] [OPTIONS]
Insert server informatiion into server.txt as the format "IP:USERNAME:PASSWORD"
Commands:
  install                     install Nuage Openvswitch rpms on the servers in the server.txt
  uninstall                   remove Nuage Openvswitch rpms from the servers in the server.txt
  upgrade                     upgrade Nuage Openvswitch rpms on the servers in the server.txt
  cli                         execute any linux command on the servers in the server.txt
  check                       check /etc/nova/nova.conf, /etc/default/openvswitch and openvswitch.service
                              status on the servers in the server.txt


Options:
  [-f|--config]               path of the json file which configure the VSC ip address and Nuage Openvswitch
                              rpm package name
  [-g|--vrsg]                 install the Nuage VRS-G
  [-v]                        display verbose
  [-h|--help]                 display this help message
"""


def print_help():
    """Print help."""
    print help_str


def worker(func, server, command, queue):
    """Multiprocessing worker."""
    result, error_message = func(server, command)

    queue.put(str(result) + "##!!" + server.host + " " + error_message)


def collector(number_of_process, queue):
    """Multiprocessing result collector."""
    failed_servers = []
    for i in range(number_of_process):
        result = queue.get().split('##!!')
        if(result[0] == 'False'):
            failed_servers.append(result[1])

    for server in failed_servers:
        print "Execute command failed on server %s" % (server)

    with open('failed_servers.txt', 'w') as f:
        f.write('\n'.join(str(server)[:] for server in failed_servers))

    f.close()


def main():
    """Main entry."""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:f:vg", ["command=", "config=", "vrsg="])
    except getopt.GetoptError, err:
        print str(err)
        print_help()
        sys.exit(2)

    verbose = False
    is_vrs_g = False
    command = None
    config_file = None
    for opt, arg in opts:
        if opt == "-v":
            verbose = True
        elif opt in ("-c", "--command"):
            command = arg
        elif opt in ("-f", "--config"):
            config_file = arg
        elif opt in ("-g", "--vrsg"):
            is_vrs_g = True
        elif opt in ("-h", "--help"):
            print_help()
            sys.exit()
        else:
            assert False, "unhandled option"

    deploy = DeployVRS(config_file, "server.txt", verbose, is_vrs_g)
    if command == "install":
        func = deploy.install
    elif command == "uninstall":
        func = deploy.uninstall
    elif command == "upgrade":
        func = deploy.upgrade
    elif command == "check":
        func = deploy.check
    else:
        func = deploy.exec_cmd

    servers = deploy.read_servers()
    record = []

    queue = multiprocessing.Queue(100)

    for server in servers:
        if verbose:
            print "Spawn process to execute %s command on server %s" % (command, server)
        worker_process = multiprocessing.Process(target=worker, args=(func, server, command, queue))
        worker_process.start()
        record.append(worker_process)

    collector_process = multiprocessing.Process(target=collector, args=(len(record), queue))
    collector_process.start()

    for worker_process in record:
        worker_process.join()

    queue.close()

    collector_process.join()


if __name__ == "__main__":
    main()
