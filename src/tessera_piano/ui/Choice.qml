import QtQuick
import QtQuick.Controls

ComboBox {
    id: control
    implicitHeight: 40
    implicitWidth: 210
    hoverEnabled: true
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
        color: control.hovered ? Theme.hover : Theme.side
        radius: 9
        border.color: control.activeFocus ? Theme.accent : Theme.line
    }
    delegate: ItemDelegate {
        required property var modelData
        required property int index
        objectName: control.objectName + "Option" + index
        width: control.width - 12
        height: 42
        leftPadding: 12; rightPadding: 28
        text: modelData
        font: control.font
        highlighted: control.highlightedIndex === index
        contentItem: Text { text: parent.text; font: control.font; color: index === control.currentIndex ? Theme.accent : Theme.text; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        background: Rectangle { radius: 5; color: parent.highlighted || parent.hovered ? Theme.hover : "transparent" }
        Text { anchors.right: parent.right; anchors.rightMargin: 11; anchors.verticalCenter: parent.verticalCenter; visible: index === control.currentIndex; text: "\uE73E"; font.family: "Segoe MDL2 Assets"; font.pixelSize: 11; color: Theme.accent }
    }
    popup: TPopup {
        objectName: control.objectName + "Popup"
        focus: false
        y: control.height + 4
        width: control.width
        implicitHeight: Math.min(280, contentItem.implicitHeight + 12)
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }
}
