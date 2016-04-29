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


class JsshProcess(multiprocessing.Process):

    """Class that implements ssh to the KVM servers ."""

    def __init__(self, server, cmd, verbose):
        """Constructor."""
        multiprocessing.Process.__init__(self)
        self.server = server
        self.cmd = cmd
        self.verbose = verbose

    def run(self):
        """Run cmd in async thread."""
        return self.run_ssh(self.cmd)

    def run_ssh(self, cmd):
        """Run ssh command."""
        cli = self.server.user_name + "@" + self.server.host + " " + cmd
        child = pexpect.spawn('ssh %s' % cli)
        index = child.expect([".*yes/no.*", ".*ssword:", pexpect.TIMEOUT])
        if (index == 0):
            child.sendline('yes')
            i = child.expect([pexpect.TIMEOUT, '.*ssword:'])
            if i == 0:
                print 'ERROR!'
                print 'SSH could not login. Here is what SSH said:'
                print child.before, child.after
                return None
            else:
                child.sendline(self.server.password)
        elif index == 1:
            child.sendline(self.server.password)
        else:
            print 'ERROR!'
            print 'SSH could not login. Here is what SSH said:'
            print child.before, child.after
            return None
        child.expect(pexpect.EOF)
        if(self.verbose):
            print child.before

        return child.before

    def run_scp(self, filename, path):
        """Run scp command."""
        dst = self.server.user_name + "@" + self.server.host + ":" + path
        cli = "scp " + filename + " " + dst
        if(self.verbose):
            print cli

        child = pexpect.spawn(cli)
        index = child.expect([".*yes/no.*", ".*ssword:", pexpect.TIMEOUT])
        if (index == 0):
            child.sendline('yes')
            i = child.expect([pexpect.TIMEOUT, '.*ssword:'])
            if i == 0:
                print 'ERROR!'
                print 'SCP could not login. Here is what SCP said:'
                print child.before, child.after
                return None
            else:
                child.sendline(self.server.password)
        elif index == 1:
            child.sendline(self.server.password)
        else:
            print 'ERROR!'
            print 'SCP could not login. Here is what SCP said:'
            print child.before, child.after
            return None
        child.expect(pexpect.EOF)
        if(self.verbose):
            print child.before

        return child.before


class DeployVRS(object):

    """Class that implements deployment of VRS on KVM servers ."""

    def __init__(self, config_file, verbose):
        """Constructor."""
        super(DeployVRS, self).__init__()
        self.config_file = config_file
        self.verbose = verbose

    def _parse_config(self, conf):
        return Server()

    def read_vrs_config(self):
        """Read the VRS configuration from the json file."""
        with open("config.json") as json_file:
            json_data = json.load(json_file)

        return json_data

    def read_servers(self):
        """Read the servers from the file."""
        servers = []
        with open(self.config_file) as f:
            for line in f:
                info = line.split(':')
                server = Server(info[0], info[1], info[2])
                servers.append(server)

        return servers

    def check(self, server, cmd):
        """Check the Nuage VRS status of the server."""
        p = JsshProcess(server, "", self.verbose)

        print "Check status of file /etc/nova/nova.conf on %s ..." % (server)
        cmd = "ls /etc/nova/nova.conf"

        print "Check status of file /etc/default/openvswitch on %s ..." % (server)
        cmd = "ls /etc/default/openvswitch"

        print "Check status of nuage-openvsiwtch service on %s ..." % (server)
        cmd = "/bin/systemctl status openvswitch.service"
        if(self.verbose):
            print cmd
        result = p.run_ssh(cmd)
        if(not("status=0/SUCCESS" in result)):
            return False

        return True

    def install(self, server, cmd):
        """Install VRS to the servers."""
        p = JsshProcess(server, "", self.verbose)

        print "Yum install dependent rpm package ..."

        cmd = "yum install -y python-novaclient libvirt \
               python-twisted-core perl-JSON qemu-kvm vconfig \
               perl-Sys-Syslog.x86_64 protobuf-c.x86_64 \
               python-setproctitle.x86_64"
        if(self.verbose):
            print cmd
        p.run_ssh(cmd)

        print "Scp nuage VRS rpm packages to %s ..." % (server)
        vrs_config = self.read_vrs_config()

        scp_filename = ""
        for rpm_name in vrs_config['rpm']:
            scp_filename = scp_filename + rpm_name + " "
        p.run_scp(scp_filename, "/root/")

        print "Install nuage VRS rpm packages to %s ..." % (server)
        cmd = ""
        for rpm_name in vrs_config['rpm']:
            cmd = cmd + "/root/" + rpm_name + " "
        if(self.verbose):
            print cmd
        p.run_ssh("rpm -ivh " + cmd)

        print "Setting ovs_bridge to alubr0 in nova.conf on server %s..." % (server)
        cmd = "sed -i 's/\^ovs_bridge\.\*/ovs_bridge=alubr0/' /etc/nova/nova.conf"
        if(self.verbose):
            print cmd
        p.run_ssh(cmd)

        print "Setting /etc/default/openvswitch config file on server %s..." % (server)
        cmd = "sed -i 's/\^NETWORK_UPLINK_INTF\.\*/NETWORK_UPLINK_INTF=%s/' /etc/default/openvswitch; \
               sed -i 's/\^ACTIVE_CONTROLLER\.\*/ACTIVE_CONTROLLER=%s/' /etc/default/openvswitch;\
               sed -i 's/\^STANDBY_CONTROLLER\.\*/STANDBY_CONTROLLER=%s/' /etc/default/openvswitch"\
               % (vrs_config['network_uplink_intf'], vrs_config['active_controller'], vrs_config['standby_controller'])
        if(self.verbose):
            print cmd
        p.run_ssh(cmd)

        print "Restart nuage-openvsiwtch service on %s ..." % (server)

        cmd = "/bin/systemctl restart openvswitch.service"
        if(self.verbose):
            print cmd
        p.run_ssh(cmd)

        print "Check status of nuage-openvsiwtch service on %s ..." % (server)
        cmd = "/bin/systemctl status openvswitch.service"
        if(self.verbose):
            print cmd
        result = p.run_ssh(cmd)
        if("status=0/SUCCESS" in result):
            return True
        return False

    def uninstall(self, server, cmd):
        """Uninstall VRS on the servers."""
        return True

    def upgrade(self, server, cmd):
        """Upgrate VRS on the servers."""
        return True

    def exec_cmd(self, server, cmd):
        """Exec command on the servers."""
        p = JsshProcess(server, cmd, self.verbose)
        p.start()
        if(self.verbose):
            print "Spaw ssh command %s on server %s success." % (cmd, server)
        return True


def print_help():
    """Print help."""
    print sys.argv[0] + ' -c [install|uninstall|upgrade|exec|check]]'


def main():
    """Main entry."""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:v", ["command="])
    except getopt.GetoptError, err:
        print str(err)
        print_help()
        sys.exit(2)

    verbose = False
    command = None
    for opt, arg in opts:
        if opt == "-v":
            verbose = True
        elif opt in ("-c", "--command"):
            command = arg
        elif opt in ("-h", "--help"):
            print_help()
            sys.exit()
        else:
            assert False, "unhandled option"

    deploy = DeployVRS("server.txt", verbose)
    if(command == "install"):
        func = deploy.install
    elif(command == "uninstall"):
        func = deploy.uninstall
    elif(command == "upgrade"):
        func = deploy.upgrade
    elif(command == "check"):
        func = deploy.check
    else:
        func = deploy.exec_cmd

    servers = deploy.read_servers()
    for server in servers:
        failed_servers = []
        print "Exec %s command on server %s" % (command, server)
        result = func(server, command)
        if(not result):
            failed_servers.append(server)

    for server in failed_servers:
        print "Execute command %s failed on server %s" % (command, server)


if __name__ == "__main__":
    main()
