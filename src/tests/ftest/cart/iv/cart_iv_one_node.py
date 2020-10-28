#!/usr/bin/python
'''
  (C) Copyright 2018-2019 Intel Corporation.

  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  GOVERNMENT LICENSE RIGHTS-OPEN SOURCE SOFTWARE
  The Government's rights to use, modify, reproduce, release, perform, display,
  or disclose this software are subject to the terms of the Apache License as
  provided in Contract No. B609815.
  Any reproduction of computer software, computer software documentation, or
  portions thereof marked with this legend must also reproduce the markings.
'''

from __future__ import print_function

import sys
import time
import tempfile
import json
import os
import struct
import codecs
import subprocess
import shlex
import traceback

from avocado       import Test
from avocado       import main

sys.path.append('./util')

# Can't all this import before setting sys.path
# pylint: disable=wrong-import-position
from cart_utils import CartUtils

def _check_value(expected_value, received_value):
    """
        Checks that the received value (a hex string) contains the expected
        value (a string). If the received value is longer than the expected
        value, make sure any remaining characters are zeros

        returns True if the values match, False otherwise
    """
    char = None
    # Comparisons are lower case
    received_value = received_value.lower()

    # Convert the expected value to hex characters
    expected_value_hex = "".join("{:02x}".format(ord(c)) \
                                 for c in expected_value).lower()

    # Make sure received value is at least as long as expected
    if len(received_value) < len(expected_value_hex):
        return False

    # Make sure received value starts with the expected value
    if expected_value_hex not in received_value[:len(expected_value_hex)]:
        return False

    # Make sure all characters after the expected value are zeros (if any)
    for char in received_value[len(expected_value_hex):]:
        if char != "0":
            return False

    return True

def _check_key(key_rank, key_idx, received_key_hex):
    """Checks that the received key is the same as the sent key.

    Args:
        key_rank (int): 32-bit integer
        key_idx (int): 32-bit integer
        received_key_hex (int): hex(key_rank|key_idx)

    Returns:
        bool: is the received key is the same as the sent key

    """

    if len(received_key_hex) != 16:
        return False

    rank = struct.unpack("<I",
                         codecs.decode(received_key_hex[:8], "hex"))[0]
    idx = struct.unpack("<I",
                        codecs.decode(received_key_hex[8:], "hex"))[0]

    return (rank == key_rank) and (idx == key_idx)

class CartIvOneNodeTest(Test):
    """
    Runs basic CaRT tests on one-node

    :avocado: tags=all,cart,pr,iv,one_node
    """
    def setUp(self):
        """ Test setup """
        print("Running setup\n")
        self.utils = CartUtils()
        self.env = self.utils.get_env(self)

    def tearDown(self):
        """ Test tear down """
        print("Run TearDown\n")

    def _verify_action(self, action):
        """verify the action"""
        if (('operation' not in action) or
                ('rank' not in action) or
                ('key' not in action)):
            self.utils.print("Error happened during action check")
            raise ValueError("Each action must contain an operation," \
                             " rank, and key")

        if len(action['key']) != 2:
            self.utils.print("Error key should be tuple of (rank, idx)")
            raise ValueError("key should be a tuple of (rank, idx)")

    def _verify_fetch_operation(self, action):
        """verify fetch operation"""
        if (('return_code' not in action) or
                ('expected_value' not in action)):
            self.utils.print("Error: fetch operation was malformed")
            raise ValueError("Fetch operation malformed")

    def _iv_test_actions(self, cmd, actions):
        #pylint: disable=too-many-locals
        """Go through each action and perform the test"""
        for action in actions:
            clicmd = cmd
            command = 'tests/iv_client'

            self._verify_action(action)

            operation = action['operation']
            rank = int(action['rank'])
            key_rank = int(action['key'][0])
            key_idx = int(action['key'][1])

            if "fetch" in operation:
                self._verify_fetch_operation(action)
                expected_rc = int(action['return_code'])

                # Create a temporary file for iv_client to write the results to
                log_path_dir = os.environ['HOME']
                if os.environ['DAOS_TEST_SHARED_DIR']:
                    log_path_dir = os.environ['DAOS_TEST_SHARED_DIR']

                log_fd, log_path = tempfile.mkstemp(dir=log_path_dir)


                # try writing to an unwritable spot
                # log_path = "/"

                command = " {!s} -o '{!s}' -r '{!s}' -k '{!s}:{!s}' -l '{!s}'" \
                    .format(command, operation, rank, key_rank, key_idx,
                            log_path)
                clicmd += command

                self.utils.print("\nClient cmd : %s\n" % clicmd)
                cli_rtn = subprocess.call(shlex.split(clicmd))

                if cli_rtn != 0:
                    raise ValueError('Error code {!s} running command "{!s}"' \
                        .format(cli_rtn, command))

                # Read the result into test_result and remove the temp file
                log_file = open(log_path)

                # Try to induce "No JSON object could be decoded" error
                #
                # 1.
                # with open(log_path, "a") as myfile:
                # myfile.write("some-invalid-junk-appended-to-json")
                #
                # 2.
                # codecs.open(log_file, "w", "unicode").write('')

                # DEBUGGING: dump contents of JSON file to screen
                with open(log_path, 'r') as f:
                    print(f.read())

                test_result = json.load(log_file)

                log_file.close()
                os.close(log_fd)
                os.remove(log_path)

                # Parse return code and make sure it matches
                if expected_rc != test_result["return_code"]:
                    raise ValueError("Fetch returned return code {!s} != " \
                                     "expected value {!s}".format(
                                         test_result["return_code"],
                                         expected_rc))

                # Other values will be invalid if return code is failure
                if expected_rc != 0:
                    continue

                # Check that returned key matches expected one
                if not _check_key(key_rank, key_idx, test_result["key"]):
                    raise ValueError("Fetch returned unexpected key")

                # Check that returned value matches expected one
                if not _check_value(action['expected_value'],
                                    test_result["value"]):
                    raise ValueError("Fetch returned unexpected value")

            if "update" in operation:
                if 'value' not in action:
                    raise ValueError("Update operation requires value")

                command = " {!s} -o '{!s}' -r '{!s}' -k '{!s}:{!s}' -v '{!s}'"\
                        .format(command, operation, rank, key_rank, key_idx,
                                action['value'])
                if 'sync' in action:
                    command = "{!s} -s '{!s}'".format(command, action['sync'])
                if 'sync' not in action:
                    command = "{!s} -s '{!s}'".format(command, "none")

                clicmd += command

                self.utils.print("\nClient cmd : %s\n" % clicmd)
                cli_rtn = subprocess.call(shlex.split(clicmd))

                if cli_rtn != 0:
                    raise ValueError('Error code {!s} running command "{!s}"' \
                            .format(cli_rtn, command))

            if "invalidate" in operation:
                command = " {!s} -o '{!s}' -r '{!s}' -k '{!s}:{!s}' " \
			    .format( command, operation, rank, key_rank, \
				     key_idx )
                if 'sync' in action:
                    command = "{!s} -s '{!s}'".format(command, action['sync'])
                if 'sync' not in action:
                    command = "{!s} -s '{!s}'".format(command, "none")
                clicmd += command

                self.utils.print("\nClient cmd : %s\n" % clicmd)
                cli_rtn = subprocess.call(shlex.split(clicmd))

                if cli_rtn != 0:
                    raise ValueError('Error code {!s} running command "{!s}"' \
                            .format(cli_rtn, command))

            if "set_grp_version" in operation:
                command = " {!s} -o '{!s}' -r '{!s}' -v '{!s}' -m '{!s}'"\
                        .format(command, operation, rank,
                                action['version'], action['time'])
                clicmd += command

                self.utils.print("\nClient cmd : %s\n" % clicmd)
                cli_rtn = subprocess.call(shlex.split(clicmd))

                if cli_rtn != 0:
                    raise ValueError('Error code {!s} running command "{!s}"' \
                            .format(cli_rtn, command))

            if "get_grp_version" in operation:
                command = " {!s} -o '{!s}' -r '{!s}' " \
                        .format(command, operation, rank)
                clicmd += command

                self.utils.print("\nClient cmd : %s\n" % clicmd)
                cli_rtn = subprocess.call(shlex.split(clicmd))

                if cli_rtn != 0:
                    raise ValueError('Error code {!s} running command "{!s}"' \
                            .format(cli_rtn, command))

    def test_cart_iv(self):
        """
        Test CaRT IV

        :avocado: tags=all,cart,pr,iv,one_node
        """

        srvcmd = self.utils.build_cmd(self, self.env, "test_servers")

        try:
            srv_rtn = self.utils.launch_cmd_bg(self, srvcmd)
        # pylint: disable=broad-except
        except Exception as e:
            self.utils.print("Exception in launching server : {}".format(e))
            self.fail("Test failed.\n")

        # Verify the server is still running.
        if not self.utils.check_process(srv_rtn):
            procrtn = self.utils.stop_process(srv_rtn)
            self.fail("Server did not launch, return code %s" \
                       % procrtn)

        actions = [
            # Test of verison skew on update.
            # First create an iv value from rank to to rank 4.
            # Then verify that all ranks can see it.
            # Then remove it and verify that no ranks has a local copy
            # Need to know that this works prior to changing version
            #
            # Note to Alex: need to implement syncronization in the
            # invalidate for this series of test to run.
            #
            {"operation":"update", "rank":0, "key":(4, 42), "value":"turnip" },
            {"operation":"fetch", "rank":1, "key":(4, 42),
              "return_code":0, "expected_value":"turnip"},
            {"operation":"fetch", "rank":0, "key":(4, 42),
              "return_code":0, "expected_value":"turnip"},
            {"operation":"fetch", "rank":3, "key":(4, 42),
              "return_code":0, "expected_value":"turnip"},
            {"operation":"fetch", "rank":2, "key":(4, 42),
              "return_code":0, "expected_value":"turnip"},
            {"operation":"fetch", "rank":4, "key":(4, 42),
              "return_code":0, "expected_value":"turnip"},
            #
            {"operation":"invalidate", "rank":4, "key":(4, 42),
              "sync":"eager_notify", "return_code":0},
            #{"operation":"invalidate", "rank":4, "key":(4, 42),
            #  "sync":"eager_update", "return_code":0},
            #
            # Check for stale state.
            {"operation":"fetch", "rank":4, "key":(4, 42),
              "return_code":-1, "expected_value":""},
            {"operation":"fetch", "rank":1, "key":(4, 42),
              "return_code":-1, "expected_value":""},
            {"operation":"fetch", "rank":0, "key":(4, 42),
              "return_code":-1, "expected_value":""},
            {"operation":"fetch", "rank":2, "key":(4, 42),
              "return_code":-1, "expected_value":""},
            {"operation":"fetch", "rank":3, "key":(4, 42),
              "return_code":-1, "expected_value":""},
            #
            # ****
            # Fetch, to expect fail, no variable yet
            # Make sure everything goes to the top rank
            #{"operation":"fetch", "rank":0, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":1, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":4, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #
            # ****
            # Add variable 0:42
            #{"operation":"update", "rank":0, "key":(0, 42), "value":"potato"},
            #
            # ****
            # Fetch the value from each server and verify it
            #{"operation":"fetch", "rank":0, "key":(0, 42), "return_code":0,
            # "expected_value":"potato"},
            #{"operation":"fetch", "rank":1, "key":(0, 42), "return_code":0,
            # "expected_value":"potato"},
            #{"operation":"fetch", "rank":2, "key":(0, 42), "return_code":0,
            # "expected_value":"potato"},
            #{"operation":"fetch", "rank":3, "key":(0, 42), "return_code":0,
            # "expected_value":"potato"},
            #{"operation":"fetch", "rank":4, "key":(0, 42), "return_code":0,
            # "expected_value":"potato"},
            #
            # ****
            # Invalidate the value
            #{"operation":"invalidate", "rank":0, "key":(0, 42)},
            #
            # ****
            # Fetch the value again from each server, expecting failure
            # Reverse order of fetch just in case.
            #{"operation":"fetch", "rank":4, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":3, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":2, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":1, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"fetch", "rank":0, "key":(0, 42), "return_code":-1,
            # "expected_value":""},
            #
            ######################
            # Testing version number conflicts.
            ######################
            # Test of verison skew on fetch between rank 0 and rank 1.
            # ****
            # From parent to child and from child to parent
            # Don't setup a iv variable.
            # Modify version number on root 0.
            # Do fetch in both direction for and test for failure.
            # First, do test for normal failure.
            #{"operation":"fetch", "rank":0, "key":(1, 42), "return_code":-1,
            # "expected_value":""},
            #{"operation":"set_grp_version", "rank":0, "key":(0, 42), "time":0
            #  "version":"0xdeadc0de", "return_code":0, "expected_value":""},
            #{"operation":"fetch", "rank":0, "key":(1, 42),
            #  "return_code":-1036, "expected_value":""},
            #{"operation":"fetch", "rank":1, "key":(0, 42),
            #  "return_code":-1036, "expected_value":""},
            #{"operation":"set_grp_version", "rank":0, "key":(0, 42), "time":0
            #  "version":"0x0", "return_code":0, "expected_value":""},
            #{"operation":"invalidate", "rank":1, "key":(1, 42)},
            #
            # ****
            # Test of verison skew on fetch between rank 0 and rank 1.
            # Create iv variable on rank 1.
            # Fetch from rank 0.
            # Change version on rank 0 while request in flight,
            # Not an error:
            #   Used for testing to ensure we donot break something
            #   that should work.
            #{"operation":"update", "rank":1, "key":(1, 42), "value":"beans"},
            #{"operation":"set_grp_version", "rank":0, "key":(1, 42), "time":1,
            #  "version":"0xc001c001", "return_code":0, "expected_value":""},
            #{"operation":"fetch", "rank":0, "key":(1, 42),
            #  "return_code":0, "expected_value":"beans"},
            #{"operation":"set_grp_version", "rank":0, "key":(1, 42), "time":0,
            #  "version":"0", "return_code":0, "expected_value":""},
            #{"operation":"invalidate", "rank":1, "key":(1, 42)},
            #
            # Test of verison skew on fetch between rank 0 and rank 1.
            # From parent to child.
            # Create a iv variable on second server  (child).
            # Setup second server to change version after it receives
            #   the rpc request.
            # Fetch variable from the first server.
            # Tests version-check in crt_hdlr_iv_fetch_aux.
            #{"operation":"update", "rank":1, "key":(1, 42), "value":"carrot"},
            #{"operation":"set_grp_version", "rank":1, "key":(0, 42), "time":2,
            #  "version":"0xdeadc0de", "return_code":0, "expected_value":""},
            #{"operation":"fetch", "rank":0, "key":(1, 42),
            #  "return_code":-1036, "expected_value":""},
            #{"operation":"set_grp_version", "rank":1, "key":(0, 42), "time":0,
            #  "version":"0x0", "return_code":0, "expected_value":""},
            #{"operation":"invalidate", "rank":1, "key":(1, 42)},
        ]

        time.sleep(2)

        failed = False

        clicmd = self.utils.build_cmd(self, self.env, "test_clients")

        ########## Launch Client Actions ##########

        try:
            self._iv_test_actions(clicmd, actions)
        except ValueError as exception:
            failed = True
            traceback.print_stack()
            self.utils.print("TEST FAILED: %s" % str(exception))

        ########## Shutdown Servers ##########

        num_servers = self.utils.get_srv_cnt(self, "test_servers")

        srv_ppn = self.params.get("test_servers_ppn", '/run/tests/*/')

        # Note: due to CART-408 issue, rank 0 needs to shutdown last
        # Request each server shut down gracefully
        for rank in reversed(range(1, int(srv_ppn) * num_servers)):
            clicmd += " -o shutdown -r " + str(rank)
            self.utils.print("\nClient cmd : %s\n" % clicmd)
            try:
                subprocess.call(shlex.split(clicmd))
            # pylint: disable=broad-except
            except Exception as e:
                failed = True
                self.utils.print("Exception in launching client : {}".format(e))

        time.sleep(1)

        # Shutdown rank 0 separately
        clicmd += " -o shutdown -r 0"
        self.utils.print("\nClient cmd : %s\n" % clicmd)
        try:
            subprocess.call(shlex.split(clicmd))
        # pylint: disable=broad-except
        except Exception as e:
            failed = True
            self.utils.print("Exception in launching client : {}".format(e))

        time.sleep(2)

        # Stop the server if it is still running
        if self.utils.check_process(srv_rtn):
            # Return value is meaningless with --continuous
            self.utils.stop_process(srv_rtn)

        if failed:
            self.fail("Test failed.\n")


if __name__ == "__main__":
    main()