import QtQuick
import QtQuick.Controls

MenuItem {
    id: control
    property bool danger: false
    implicitHeight: 42
    leftPadding: 13; rightPadding: 13
    contentItem: Text {
        text: control.text
        color: control.danger ? Theme.danger : Theme.text
        font.family: Theme.font; font.pixelSize: 13
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 7
        color: control.highlighted || control.hovered ? Theme.hover : "transparent"
        Behavior on color { ColorAnimation { duration: Theme.fast } }
    }
}
