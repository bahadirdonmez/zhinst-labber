import time
import numpy as np
from BaseDriver import LabberDriver, Error

import zhinst.toolkit as tk


# change this value in case you are not using 'localhost'
HOST = "localhost"


class Driver(LabberDriver):
    """This class implements a Labber driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        interface = self.comCfg.interface
        if not interface == "USB":
            interface = "1GbE"
        # initialize controller and connect
        self.controller = tk.PQSC(
            self.comCfg.name, self.comCfg.address[:8], interface=interface, host=HOST
        )
        self.controller.setup()
        self.controller.connect_device()
        value = self.readValueFromOther("Revisions - Data Server Version")
        self.setValue("Revisions - Data Server Version", str(value))
        value = self.readValueFromOther("Revisions - Firmware Version")
        self.setValue("Revisions - Firmware Version", str(value))
        value = self.readValueFromOther("Revisions - FPGA Version")
        self.setValue("Revisions - FPGA Version", str(value))
        # Update display options
        self.update_display_options()

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        pass

    def initSetConfig(self):
        """This function is run before setting values in Set Config"""
        pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        quant.setValue(value)

        # Load factory preset
        if "Factory Reset" in quant.name:
            self.factory_reset()

        # if a 'set_cmd' is defined, just set the node
        if quant.set_cmd:
            if "Alias" in quant.name:
                value = self.set_node_vector(quant, value)
            else:
                value = self.set_node_value(quant, value)
        # Check if reference clock is locked
        if "Reference Clock" in quant.name:
            self.check_ref_clock()
        # Start / Stop sending triggers
        if "Run/Stop" in quant.name:
            value = self.start_stop()
        # Update display options
        if "Enable Forwarding" in quant.name:
            self.update_display_options()
        return value

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        if quant.get_cmd:
            # if a 'get_cmd' is defined, use it to return the node value
            if "Data Server Version" in quant.name:
                return self.version_parser(self.controller._get(quant.get_cmd))
            else:
                return self.controller._get(quant.get_cmd)
        else:
            return quant.getValue()

    def performArm(self, quant_names, options={}):
        """Perform the instrument arm operation"""
        self.controller.arm()

    def set_node_value(self, quant, value):
        if quant.datatype == quant.COMBO:
            i = quant.getValueIndex(value)
            if len(quant.cmd_def) == 0:
                self.controller._set(quant.set_cmd, i)
            else:
                self.controller._set(quant.set_cmd, quant.cmd_def[i])
        else:
            self.controller._set(quant.set_cmd, value)
        return self.controller._get(quant.get_cmd)

    def set_node_vector(self, quant, vector):
        if quant.datatype == quant.COMBO:
            i = quant.getValueIndex(vector)
            if len(quant.cmd_def) == 0:
                self.controller._setVector(quant.set_cmd, i)
            else:
                self.controller._setVector(quant.set_cmd, quant.cmd_def[i])
        else:
            self.controller._setVector(quant.set_cmd, vector)
        return self.controller._get(quant.get_cmd)

    def data_server_version_greater_equal(self, limit):
        data_server_version = self.getValue("Revisions - Data Server Version")
        if limit <= data_server_version:
            return True
        else:
            return False

    def update_display_options(self):
        num_ports = 18
        display_enable_bit_fowarding = self.data_server_version_greater_equal(
            "21.09.00000"
        )
        for i in range(num_ports):
            display_enable_bit_fowarding = (
                display_enable_bit_fowarding
                and self.getValue(f"ZSYNC Output Port {i+1} - Enable Forwarding")
            )
            self.setValue(
                f"ZSYNC Output Port {i+1} - Display Enable Bit Forwarding",
                display_enable_bit_fowarding,
            )

    def check_ref_clock(self) -> None:
        """Check if reference clock is locked succesfully."""
        self.controller.check_ref_clock()

    def factory_reset(self) -> None:
        """Loads the factory default settings."""
        self.controller.factory_reset()

    def start_stop(self):
        """Start or stop sending triggers to all connected instruments over ZSync ports.."""
        if self.controller.is_running:
            self.controller.stop()
        else:
            self.controller.run()
        return self.controller.is_running

    @staticmethod
    def version_parser(v):
        v = str(v)
        year = v[:2]
        month = v[2:4]
        build = v[4:]
        return f"{year}.{month}.{build}"
