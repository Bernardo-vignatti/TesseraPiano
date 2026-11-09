import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    implicitHeight: 40
    implicitWidth: 210
    font.family: Theme.font
    font.pixelSize: 13
    leftPadding: 13
    rightPadding: 32
    opacity: enabled ? 1 : 0.4
    contentItem: Text {
        text: control.displayText
        font: control.font
        color: Theme.text
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    indicator: Text {
        x: control.width - 25
        anchors.verticalCenter: parent.verticalCenter
        text: "\uE70D"
        font.family: "Segoe MDL2 Assets"
        font.pixelSize: 10
        color: Theme.muted
    }
    background: Rectangle {
        color: Theme.surface
        radius: 7
        border.color: control.activeFocus ? Theme.accent : Theme.line
    }
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        width: control.width - 8
        height: 38
        text: modelData
        font: control.font
        highlighted: control.highlightedIndex === index
        contentItem: Text { text: parent.text; font: control.font; color: Theme.text; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 5; color: parent.highlighted || parent.hovered ? Theme.hover : "transparent" }
    }
    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 4
        implicitHeight: Math.min(280, contentItem.implicitHeight + 8)
        background: Rectangle { radius: 8; color: Theme.surface; border.color: Theme.line }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }
}
