pragma Singleton
import QtQuick

QtObject {
    property bool light: false
    property bool reduced: false
    readonly property color bg: light ? "#f1eee6" : "#171d21"
    readonly property color backdrop: light ? "#dedbd0" : "#303a3e"
    readonly property color side: light ? "#e8e5dc" : "#151b1f"
    readonly property color surface: light ? "#faf8f1" : "#222c30"
    readonly property color surfaceTop: light ? "#fffdf8" : "#303b3f"
    readonly property color hover: light ? "#e6e1d4" : "#344145"
    readonly property color line: light ? "#d2ccbf" : "#3b484c"
    readonly property color text: light ? "#293431" : "#f0eee7"
    readonly property color muted: light ? "#596962" : "#a4b3b0"
    readonly property color faint: light ? "#68756e" : "#8b9c9c"
    readonly property color accent: light ? "#79501e" : "#e7bb7e"
    readonly property color accentFill: "#e7bb7e"
    readonly property color accentTint: light ? "#ebe0cb" : "#393930"
    readonly property color green: light ? "#2b6a50" : "#95b8a5"
    readonly property color danger: light ? "#af4244" : "#eda3a0"
    readonly property string font: "Segoe UI"
    readonly property string titleFont: "Georgia"
    readonly property int motion: reduced ? 0 : 160
    readonly property int fast: reduced ? 0 : 120
    readonly property int pageMotion: reduced ? 0 : 220
}
