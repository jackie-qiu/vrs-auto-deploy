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

    def __init__(self, server, cmd):
        """Constructor."""
        multiprocessing.Process.__init__(self)
        self.server = server
        self.cmd = cmd

    def run(self):
        """Run ssh command."""
        cli = self.server.user_name + "@" + self.server.host + " " + self.cmd
        child = pexpect.spawn('ssh %s' % cli)
        index = child.expect([".*yes/no.*", ".*ssword:", pexpect.TIMEOUT])
        if (index == 0):
            child.sendline('yes')
            child.expect('.*ssword:')
            i = child.expect([pexpect.TIMEOUT, '.*ssword:'])
            if i == 0:
                print 'ERROR!'
                print 'SSH could not login. Here is what SSH said:'
                print child.before, child.after
                return None
        elif index == 1:
            child.sendline(self.server.password)
        else:
            print 'ERROR!'
            print 'SSH could not login. Here is what SSH said:'
            print child.before, child.after
            return None
        child.expect(pexpect.EOF)
        print child.before


class DeployVRS(object):
    """Class that implements deployment of VRS on KVM servers ."""

    def __init__(self, arg):
        """Constructor."""
        super(DeployVRS, self).__init__()
        self.arg = arg

    def _parse_config(self, conf):
        return Server()

    def read_config(self):
        """Read the servers from the file."""
        servers = []
        with open(self.arg) as f:
            for line in f:
                info = line.split(':')
                server = Server(info[0], info[1], info[2])
                servers.append(server)

        return servers

    def install(self, server, cmd):
        """Install VRS to the servers."""
        pass

    def uninstall(self, server, cmd):
        """Uninstall VRS on the servers."""
        pass

    def upgrade(self, server, cmd):
        """Upgrate VRS on the servers."""
        pass

    def exec_cmd(self, server, cmd):
        """Exec command on the servers."""
        p = JsshProcess(server, cmd)
        p.start()
        print "Spaw the async ssh process success."


def print_help():
    """Print help."""
    print sys.argv[0] + ' -c [install|uninstall|upgrade|exec]]'


def main():
    """Main entry."""
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hc:v", ["command"])
    except getopt.GetoptError, err:
        print str(err)
        print_help()
        sys.exit(2)

    command = None
    verbose = False
    for o, a in opts:
        if o == "-v":
            verbose = True
        elif o in ("-c", "--command"):
            command = a
            print command
        elif o in ("-h", "--help"):
            print_help()
            sys.exit()
        else:
            assert False, "unhandled option"

    deploy = DeployVRS("server.txt")
    if(command == "install"):
        func = deploy.install
    elif(command == "uninstall"):
        func = deploy.uninstall
    elif(command == "upgrade"):
        func = deploy.upgrade
    else:
        func = deploy.exec_cmd

    servers = deploy.read_config()
    for server in servers:
        if(verbose):
            print "Exec %s command on server %s" % (command, server)
        func(server, command)

if __name__ == "__main__":
    main()
