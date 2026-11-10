import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: dialog
    property string acceptText: "Confirmar"
    property bool destructive: false
    property bool canAccept: true
    property string acceptName: "dialogAccept"
    width: Math.min(440, Overlay.overlay.width - 32)
    contentWidth: width - leftPadding - rightPadding
    implicitHeight: contentItem.implicitHeight + header.implicitHeight + footer.implicitHeight + topPadding + bottomPadding
    anchors.centerIn: Overlay.overlay
    modal: true; focus: true; padding: 24
    popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape
    Overlay.modal: Rectangle { color: Theme.light ? "#80525b55" : "#b00c1418" }
    background: Surface { radius: 16 }
    header: Text {
        text: dialog.title; color: Theme.text
        leftPadding: 24; topPadding: 24; rightPadding: 24
        font.family: Theme.font; font.pixelSize: 21; font.weight: Font.DemiBold
        wrapMode: Text.WordWrap
    }
    footer: Item {
        implicitHeight: 70
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; anchors.bottomMargin: 16
            Item { Layout.fillWidth: true }
            TButton { text: "Cancelar"; onClicked: dialog.reject() }
            TButton { objectName: dialog.acceptName; text: dialog.acceptText; primary: !dialog.destructive; danger: dialog.destructive; enabled: dialog.canAccept; onClicked: dialog.accept() }
        }
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion } NumberAnimation { property: "scale"; from: .97; to: 1; duration: Theme.motion; easing.type: Easing.OutCubic } }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.fast } }
}
