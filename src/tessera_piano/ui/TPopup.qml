import QtQuick
import QtQuick.Controls

Popup {
    padding: 6
    margins: 12
    focus: true
    popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    background: Surface { radius: 11 }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: .97; to: 1; duration: Theme.motion; easing.type: Easing.OutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.fast } }
}
