import QtQuick
import QtQuick.Controls

CheckDelegate {
    id: control
    implicitHeight: 44
    leftPadding: 38; rightPadding: 12
    indicator: Rectangle {
        x: 12; y: (control.height - height) / 2
        width: 17; height: 17; radius: 4
        color: control.checked ? Theme.accentFill : Theme.side
        border.color: control.activeFocus ? Theme.text : control.checked ? Theme.accent : Theme.line
        Text { anchors.centerIn: parent; text: "\uE73E"; font.family: "Segoe MDL2 Assets"; font.pixelSize: 11; color: "#30271c"; visible: control.checked }
    }
    contentItem: Text { text: control.text; font.family: Theme.font; font.pixelSize: 12; color: Theme.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
    background: Rectangle { radius: 7; color: control.hovered || control.activeFocus ? Theme.hover : "transparent" }
}
