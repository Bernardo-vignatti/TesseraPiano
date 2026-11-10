import QtQuick
import QtQuick.Controls

Menu {
    padding: 6
    margins: 12
    popupType: Popup.Item
    background: Surface { radius: 11 }
    enter: Transition {
        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion; easing.type: Easing.OutCubic }
        NumberAnimation { property: "scale"; from: .97; to: 1; duration: Theme.motion; easing.type: Easing.OutCubic }
    }
    exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: Theme.fast } }
}
