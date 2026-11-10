import QtQuick
import QtQuick.Controls

SpinBox {
    id: control
    implicitHeight: 40
    implicitWidth: 150
    leftPadding: 38; rightPadding: 38
    font.family: Theme.font; font.pixelSize: 13
    contentItem: TextInput {
        text: control.textFromValue(control.value, control.locale)
        font: control.font
        color: Theme.text
        selectionColor: Theme.accentTint
        selectedTextColor: Theme.text
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        readOnly: !control.editable
        validator: control.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }
    background: Rectangle { radius: 9; color: Theme.side; border.color: control.activeFocus ? Theme.accent : Theme.line }
    up.indicator: Rectangle {
        x: control.width - width; width: 36; height: control.height
        radius: 9; color: control.up.pressed || control.up.hovered ? Theme.hover : "transparent"
        Text { anchors.centerIn: parent; text: "+"; font.family: Theme.font; font.pixelSize: 18; color: Theme.text; opacity: control.up.enabled ? 1 : .4 }
    }
    down.indicator: Rectangle {
        width: 36; height: control.height
        radius: 9; color: control.down.pressed || control.down.hovered ? Theme.hover : "transparent"
        Text { anchors.centerIn: parent; text: "−"; font.family: Theme.font; font.pixelSize: 18; color: Theme.text; opacity: control.down.enabled ? 1 : .4 }
    }
}
