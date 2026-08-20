import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "acp.streamdeck"
  ipcTarget: "acp.streamdeck"
  manageIpc: false
  property var anchorItem: null
  property var hostWidget: null
  readonly property var barIdentity: hostWidget || root
  property var status: ({ running: false, plus: null, pedal: null, profile: "Omarchy Default", brightness: 55 })
  property var profile: ({ keys: [], dials: [], pedals: [] })
  property string error: ""
  readonly property bool connected: status.plus !== null || status.pedal !== null
  readonly property string helper: Qt.resolvedUrl("bin/omarchy-streamdeck").toString().replace("file://", "")

  function open() { root.controller.show(); refresh() }
  function close() { root.controller.hide() }
  function toggle() { if (root.opened) close(); else open() }
  function refresh() {
    if (!statusProc.running) statusProc.running = true
    if (!profileProc.running) profileProc.running = true
  }
  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function") return root.bar.switchPanelFrom(root.barIdentity, direction)
    return false
  }

  Process {
    id: statusProc
    command: [root.helper, "status", "--json"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        try { root.status = JSON.parse(text); root.error = "" }
        catch (e) { root.error = "Could not read Stream Deck status" }
      }
    }
  }
  Process {
    id: profileProc
    command: [root.helper, "profile"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: { try { root.profile = JSON.parse(text) } catch (e) {} }
    }
  }
  Process { id: openProfileProc; command: ["uwsm-app", "--", "xdg-open", Quickshell.env("HOME") + "/.config/omarchy-streamdeck/profile.json"] }
  Timer { interval: 1500; repeat: true; running: root.opened; triggeredOnStart: true; onTriggered: root.refresh() }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: true
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(430))
    contentHeight: panel.fittedContentHeight(content.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: content
        width: parent.width
        spacing: Style.space(10)

        Row {
          width: parent.width
          spacing: Style.space(10)
          Image { width: Style.space(28); height: width; source: Qt.resolvedUrl("assets/elgato.svg"); fillMode: Image.PreserveAspectFit }
          Column {
            width: parent.width - Style.space(120)
            Text { text: "Elgato Stream Deck"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 16; font.bold: true }
            Text { text: root.status.profile || "Omarchy Default"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 11 }
          }
          Text { text: root.connected ? "Connected" : "Disconnected"; color: root.connected ? Color.accent : Color.muted; font.family: Style.font.family; font.pixelSize: 11 }
        }

        Rectangle { width: parent.width; height: 1; color: Qt.rgba(1, 1, 1, 0.2) }

        Text { text: "DEVICES"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10; font.bold: true }
        Row {
          width: parent.width; spacing: Style.space(8)
          Repeater {
            model: [
              { name: "Stream Deck +", connected: root.status.plus !== null },
              { name: "Pedal", connected: root.status.pedal !== null },
              { name: "Brightness " + (root.status.brightness || 0) + "%", connected: root.status.plus !== null }
            ]
            Rectangle {
              width: (parent.width - Style.space(16)) / 3; height: Style.space(32); radius: Style.cornerRadius
              color: modelData.connected ? Qt.rgba(0.2, 0.7, 0.5, 0.16) : Qt.rgba(1, 1, 1, 0.04)
              border.color: modelData.connected ? Color.accent : Qt.rgba(1, 1, 1, 0.2)
              Text { anchors.centerIn: parent; text: modelData.name; color: modelData.connected ? Color.foreground : Color.muted; font.family: Style.font.family; font.pixelSize: 10 }
            }
          }
        }

        Text { text: "KEY LIGHTS"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10; font.bold: true }
        Row {
          width: parent.width; spacing: Style.space(8)
          Repeater {
            model: root.status.lights || []
            Rectangle {
              width: (parent.width - Style.space(8)) / Math.max(1, (root.status.lights || []).length)
              height: Style.space(38); radius: Style.cornerRadius
              color: modelData.on ? Qt.rgba(1, .72, .18, .18) : Qt.rgba(1, 1, 1, .04)
              border.color: modelData.reachable ? (modelData.on ? "#f0b632" : Qt.rgba(1, 1, 1, .2)) : Color.urgent
              Column {
                anchors.centerIn: parent
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.name + " · " + (modelData.on ? "On" : "Off"); color: Color.foreground; font.family: Style.font.family; font.pixelSize: 11 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: modelData.reachable ? modelData.brightness + "% · " + Math.round(1000000 / modelData.temperature) + "K" : "Unavailable"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10 }
              }
            }
          }
        }

        Text { text: "KEYS"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10; font.bold: true }
        Grid {
          width: parent.width; columns: 4; columnSpacing: Style.space(6); rowSpacing: Style.space(6)
          Repeater {
            model: root.profile.keys || []
            Rectangle {
              width: (content.width - Style.space(18)) / 4; height: Style.space(42); radius: Style.cornerRadius
              color: modelData.color ? Qt.rgba(modelData.color[0]/255, modelData.color[1]/255, modelData.color[2]/255, .24) : Qt.rgba(1, 1, 1, 0.04)
              border.color: modelData.color ? Qt.rgba(modelData.color[0]/255, modelData.color[1]/255, modelData.color[2]/255, .75) : Qt.rgba(1, 1, 1, 0.2)
              Text { anchors.centerIn: parent; width: parent.width - Style.space(6); horizontalAlignment: Text.AlignHCenter; elide: Text.ElideRight; text: (index + 1) + " · " + modelData.label; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 10 }
            }
          }
        }

        Text { text: "DIALS"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10; font.bold: true }
        Text { width: parent.width; wrapMode: Text.WordWrap; text: (root.profile.dials || []).map(function(x, i) { return (i + 1) + " · " + x.label }).join("    "); color: Color.foreground; font.family: Style.font.family; font.pixelSize: 11 }
        Text { text: "PEDALS"; color: Color.muted; font.family: Style.font.family; font.pixelSize: 10; font.bold: true }
        Text { width: parent.width; wrapMode: Text.WordWrap; text: (root.profile.pedals || []).map(function(x, i) { return (i + 1) + " · " + x.label }).join("    "); color: Color.foreground; font.family: Style.font.family; font.pixelSize: 11 }

        Text { visible: !!root.status.lastAction; text: "Last action: " + (root.status.lastAction || "") + " · " + (root.status.lastEvent || ""); color: Color.muted; font.family: Style.font.family; font.pixelSize: 10 }
        Text { visible: root.error !== "" || !!root.status.error; text: root.error || root.status.error || ""; color: Color.urgent; font.family: Style.font.family; font.pixelSize: 11 }

        Rectangle {
          width: parent.width; height: Style.space(34); radius: Style.cornerRadius; color: mouse.containsMouse ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(1, 1, 1, 0.04); border.color: Qt.rgba(1, 1, 1, 0.2)
          Text { anchors.centerIn: parent; text: "Edit profile"; color: Color.foreground; font.family: Style.font.family; font.pixelSize: 11 }
          MouseArea { id: mouse; anchors.fill: parent; hoverEnabled: true; onClicked: { openProfileProc.startDetached(); root.close() } }
        }
      }
    }
  }
}
