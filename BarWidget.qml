import QtQuick
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "acp.streamdeck"

  function injectPanel() {
    if (!panelLoader.item) return
    panelLoader.item.bar = root.bar
    panelLoader.item.anchorItem = button
    panelLoader.item.hostWidget = root
  }
  function open() { if (panelLoader.item) panelLoader.item.open() }
  function close() { if (panelLoader.item) panelLoader.item.close() }
  function closeForPopoutSwitch() { close() }
  readonly property bool opened: panelLoader.item ? panelLoader.item.opened === true : false
  readonly property bool connected: panelLoader.item ? panelLoader.item.connected === true : false
  readonly property bool popoutSwitchClosing: false
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight
  onBarChanged: injectPanel()


  Loader {
    id: panelLoader
    active: true
    visible: false
    source: Qt.resolvedUrl("Panel.qml")
    onLoaded: root.injectPanel()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    dimmed: !root.connected
    tooltipText: root.connected ? "Elgato Control · Connected" : "Elgato Control · Disconnected"
    iconComponent: Component {
      Image {
        anchors.centerIn: parent
        width: Math.min(parent.width, parent.height) * 0.72
        height: width
        source: Qt.resolvedUrl("assets/elgato.svg")
        fillMode: Image.PreserveAspectFit
        smooth: true
      }
    }
    onPressed: function(mouseButton) { if (panelLoader.item) panelLoader.item.toggle() }
  }
}
