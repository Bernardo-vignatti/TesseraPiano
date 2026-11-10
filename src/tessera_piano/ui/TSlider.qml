import QtQuick
import QtQuick.Controls

Slider {
    id: control
    implicitHeight: 26
    opacity: enabled ? 1 : .4
    background: Rectangle {
        x: control.leftPadding
        y: control.height / 2 - 2
        width: control.availableWidth
        height: 4; radius: 2; color: Theme.line
        Rectangle { width: parent.width * control.visualPosition; height: parent.height; radius: 2; color: Theme.accent }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.height / 2 - height / 2
        width: 12; height: 12; radius: 6
        color: Theme.light ? Theme.accent : "#f0d4ac"
        border.color: control.activeFocus ? Theme.text : Theme.accent
        scale: control.pressed ? 1.2 : 1
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }
}
