import QtQuick
import QtQuick.Controls

Switch {
    id: control
    implicitHeight: 36
    font.family: Theme.font
    font.pixelSize: 13
    opacity: enabled ? 1 : .4
    indicator: Rectangle {
        implicitWidth: 36
        implicitHeight: 21
        x: control.leftPadding
        y: parent.height / 2 - height / 2
        radius: 11
        color: control.checked ? Theme.accentFill : Theme.line
        border.color: control.activeFocus ? Theme.accent : "transparent"
        Rectangle {
            x: control.checked ? 17 : 3
            y: 3
            width: 15
            height: 15
            radius: 8
            color: control.checked ? "#282015" : Theme.muted
            Behavior on x { NumberAnimation { duration: Theme.motion; easing.type: Easing.OutCubic } }
        }
        Behavior on color { ColorAnimation { duration: Theme.motion } }
    }
    contentItem: Text {
        text: control.text
        font: control.font
        color: control.enabled ? Theme.text : Theme.faint
        verticalAlignment: Text.AlignVCenter
        leftPadding: control.indicator.width + 12
    }
}
