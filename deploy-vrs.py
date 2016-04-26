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


class DeployVRS(object):
    """Class that implements deployment of VRS on KVM servers ."""

    def __init__(self, arg):
        """Constructor."""
        super(DeployVRS, self).__init__()
        self.arg = arg

    def _read_config(self):
        with open("server.txt") as f:
            for line in f:
                print line

    def install(self):
        """Install VRS to the servers."""
        pass

    def uninstall(self):
        """Uninstall VRS on the servers."""
        pass

    def upgrate(self):
        """Upgrate VRS on the servers."""
        pass


def print_help():
    """Print help."""
    pass


def main():
    """Main entry."""
    pass

if __name__ == "__main__":
    main()
