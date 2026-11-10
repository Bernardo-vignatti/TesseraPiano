import QtQuick
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: 42
    font.family: Theme.font
    font.pixelSize: 13
    color: Theme.text
    placeholderTextColor: Theme.faint
    padding: 12
    selectByMouse: true
    selectionColor: Theme.accentTint
    selectedTextColor: Theme.text
    background: Rectangle {
        radius: 9
        color: Theme.side
        border.color: control.activeFocus ? Theme.accent : Theme.line
        Behavior on border.color { ColorAnimation { duration: Theme.fast } }
    }
}
