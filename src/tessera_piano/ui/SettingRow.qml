import QtQuick

Item {
    id: row
    property string title: ""
    property string detail: ""
    property Component editor
    implicitHeight: detail ? 82 : 64
    implicitWidth: 600
    Column {
        anchors.left: parent.left; anchors.leftMargin: 20; anchors.verticalCenter: parent.verticalCenter
        width: parent.width - 290; spacing: 5
        Text { text: row.title; width: parent.width; font.family: Theme.font; font.pixelSize: 13; color: Theme.text; wrapMode: Text.WordWrap }
        Text { visible: row.detail.length > 0; text: row.detail; width: parent.width; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted; wrapMode: Text.WordWrap }
    }
    Loader { anchors.right: parent.right; anchors.rightMargin: 20; anchors.verticalCenter: parent.verticalCenter; width: 230; sourceComponent: row.editor }
    Rectangle { anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 20; height: 1; color: Theme.line; opacity: .55 }
}
