import QtQuick
import QtQuick.Controls

Button {
    id: control
    property bool primary: false
    property bool danger: false
    property bool compact: false
    property string glyph: ""
    property bool selected: false
    property bool leftAligned: false
    implicitHeight: compact ? 34 : 42
    implicitWidth: text.length === 0 ? (compact ? 36 : 42) : Math.max(compact ? 36 : 42, label.implicitWidth + (glyph ? 54 : 28))
    hoverEnabled: true
    scale: down ? .975 : 1
    Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    opacity: enabled ? 1 : 0.4
    font.family: Theme.font
    font.pixelSize: 13
    Accessible.name: text
    contentItem: Item {
        implicitWidth: label.implicitWidth + (control.glyph ? 24 : 0)
        Text {
            visible: control.glyph.length > 0
            text: control.glyph
            anchors.left: control.text.length ? parent.left : undefined
            anchors.horizontalCenter: control.text.length ? undefined : parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            font.family: "Segoe MDL2 Assets"
            font.pixelSize: 15
            color: control.primary ? "#282015" : (control.danger ? Theme.danger : Theme.text)
        }
        Text {
            id: label
            text: control.text
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: control.leftAligned ? parent.left : undefined
            anchors.leftMargin: control.glyph ? 25 : 0
            anchors.horizontalCenter: control.leftAligned ? undefined : parent.horizontalCenter
            anchors.horizontalCenterOffset: control.glyph ? 10 : 0
            color: control.primary ? "#282015" : (control.danger ? Theme.danger : Theme.text)
            font.family: control.font.family
            font.pixelSize: control.font.pixelSize
            font.weight: control.primary ? Font.DemiBold : Font.Normal
        }
    }
    background: Rectangle {
        radius: 9
        color: control.primary ? (control.down ? "#cda568" : control.hovered ? "#eccc98" : Theme.accentFill) : control.selected ? Theme.accentTint : (control.down || control.hovered ? Theme.hover : control.flat ? "transparent" : Theme.surface)
        border.width: control.primary || control.flat && !control.activeFocus ? 0 : 1
        border.color: control.activeFocus ? Theme.accent : Theme.line
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
    TToolTip { visible: control.hovered && control.text.length === 0 && control.Accessible.name.length > 0; text: control.Accessible.name }
}
