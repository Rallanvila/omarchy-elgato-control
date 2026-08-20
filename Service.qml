import QtQuick
import Quickshell
import Quickshell.Io

// The shell owns one long-running HID reader. It exits cleanly with the shell.
Item {
  id: root
  readonly property string helper: Qt.resolvedUrl("bin/elgato-control").toString().replace("file://", "")

  Process {
    id: daemon
    command: [root.helper, "daemon"]
    onExited: function(code) { restartTimer.start() }
  }

  Timer {
    id: restartTimer
    interval: 2000
    onTriggered: if (!daemon.running) daemon.running = true
  }

  Component.onCompleted: daemon.running = true
}
