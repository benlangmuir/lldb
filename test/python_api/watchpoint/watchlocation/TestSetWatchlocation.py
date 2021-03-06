"""
Use lldb Python SBValue.WatchPointee() API to create a watchpoint for write of '*g_char_ptr'.
"""

import os, time
import re
import unittest2
import lldb, lldbutil
from lldbtest import *

class SetWatchlocationAPITestCase(TestBase):

    mydir = os.path.join("python_api", "watchpoint", "watchlocation")

    def setUp(self):
        # Call super's setUp().
        TestBase.setUp(self)
        # Our simple source filename.
        self.source = 'main.cpp'
        # Find the line number to break inside main().
        self.line = line_number(self.source, '// Set break point at this line.')
        # This is for verifying that watch location works.
        self.violating_func = "do_bad_thing_with_location";

    @unittest2.skipUnless(sys.platform.startswith("darwin"), "requires Darwin")
    @python_api_test
    @dsym_test
    def test_watch_location_with_dsym(self):
        """Exercise SBValue.WatchPointee() API to set a watchpoint."""
        self.buildDsym()
        self.do_set_watchlocation()

    @expectedFailureFreeBSD('llvm.org/pr16706') # Watchpoints fail on FreeBSD
    @skipIfLinux # Sometimes passes, sometimes not.
    @python_api_test
    @dwarf_test
    def test_watch_location_with_dwarf(self):
        """Exercise SBValue.WatchPointee() API to set a watchpoint."""
        self.buildDwarf()
        self.do_set_watchlocation()

    def do_set_watchlocation(self):
        """Use SBValue.WatchPointee() to set a watchpoint and verify that the program stops later due to the watchpoint."""
        exe = os.path.join(os.getcwd(), "a.out")

        # Create a target by the debugger.
        target = self.dbg.CreateTarget(exe)
        self.assertTrue(target, VALID_TARGET)

        # Now create a breakpoint on main.c.
        breakpoint = target.BreakpointCreateByLocation(self.source, self.line)
        self.assertTrue(breakpoint and
                        breakpoint.GetNumLocations() == 1,
                        VALID_BREAKPOINT)

        # Now launch the process, and do not stop at the entry point.
        process = target.LaunchSimple(None, None, os.getcwd())

        # We should be stopped due to the breakpoint.  Get frame #0.
        process = target.GetProcess()
        self.assertTrue(process.GetState() == lldb.eStateStopped,
                        PROCESS_STOPPED)
        thread = lldbutil.get_stopped_thread(process, lldb.eStopReasonBreakpoint)
        frame0 = thread.GetFrameAtIndex(0)

        value = frame0.FindValue('g_char_ptr',
                                 lldb.eValueTypeVariableGlobal)
        pointee = value.CreateValueFromAddress("pointee",
                                               value.GetValueAsUnsigned(0),
                                               value.GetType().GetPointeeType())
        # Watch for write to *g_char_ptr.
        error = lldb.SBError();
        watchpoint = value.WatchPointee(True, False, True, error)
        self.assertTrue(value and watchpoint,
                        "Successfully found the pointer and set a watchpoint")
        self.DebugSBValue(value)
        self.DebugSBValue(pointee)

        # Hide stdout if not running with '-t' option.
        if not self.TraceOn():
            self.HideStdout()

        print watchpoint

        # Continue.  Expect the program to stop due to the variable being written to.
        process.Continue()

        if (self.TraceOn()):
            lldbutil.print_stacktraces(process)

        thread = lldbutil.get_stopped_thread(process, lldb.eStopReasonWatchpoint)
        self.assertTrue(thread, "The thread stopped due to watchpoint")
        self.DebugSBValue(value)
        self.DebugSBValue(pointee)

        self.expect(lldbutil.print_stacktrace(thread, string_buffer=True), exe=False,
            substrs = [self.violating_func])

        # This finishes our test.


if __name__ == '__main__':
    import atexit
    lldb.SBDebugger.Initialize()
    atexit.register(lambda: lldb.SBDebugger.Terminate())
    unittest2.main()
