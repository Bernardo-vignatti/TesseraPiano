import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: studio
    objectName: "designPreview"
    width: 1440
    height: 960
    visible: true
    title: "Tessera Piano · proposta 4.1 / 01"
    color: "#15191c"

    property color ink: "#f0eee7"
    property color muted: "#9a9fa0"
    property color accent: "#e7bb7e"
    property real playhead: 26.4
    property bool playing: false
    property bool reduced: false
    property int interpretation: 1
    property int pedal: 0
    readonly property real contentWidth: width - 544
    readonly property var styles: ["Original", "Natural", "Expressivo"]
    readonly property var pedals: ["Automático", "Apenas MIDI", "Ligado", "Desligado", "Manual"]
    readonly property var whites: {
        let keys = []
        for (let n = 21; n <= 108; n++) if ([0, 2, 4, 5, 7, 9, 11].includes(n % 12)) keys.push(n)
        return keys
    }
    readonly property var blacks: {
        let keys = []
        for (let n = 21; n <= 108; n++) if ([1, 3, 6, 8, 10].includes(n % 12)) keys.push(n)
        return keys
    }
    function timeText(seconds) { return Math.floor(seconds / 60) + ":" + ("0" + Math.floor(seconds % 60)).slice(-2) }

    component Copy: Text {
        color: studio.ink
        font.family: "Segoe UI"
        font.pixelSize: 13
        renderType: Text.QtRendering
    }
    component Caption: Copy {
        font.pixelSize: 10
        font.letterSpacing: 1.7
        color: studio.muted
    }
    component Icon: Copy {
        font.family: "Segoe MDL2 Assets"
        font.pixelSize: 16
    }
    component Surface: Rectangle {
        radius: 16
        color: "#1c2226"
        border.color: "#343b3e"
        Rectangle { x: 18; y: 0; width: parent.width - 36; height: 1; color: "#526064"; opacity: .22 }
    }
    component Action: Button {
        id: action
        property bool primary: false
        property bool quiet: false
        property string symbol: ""
        implicitHeight: 40
        implicitWidth: label.implicitWidth + (symbol ? 58 : 30)
        hoverEnabled: true
        Accessible.name: text
        scale: down ? .975 : 1
        Behavior on scale { NumberAnimation { duration: studio.reduced ? 0 : 100; easing.type: Easing.OutCubic } }
        contentItem: Item {
            Icon { x: 1; anchors.verticalCenter: parent.verticalCenter; text: action.symbol; color: action.primary ? "#30271c" : studio.muted; visible: text.length > 0 }
            Copy { id: label; text: action.text; anchors.centerIn: parent; anchors.horizontalCenterOffset: action.symbol ? 10 : 0; font.pixelSize: 12; font.weight: action.primary ? Font.DemiBold : Font.Normal; color: action.primary ? "#30271c" : studio.ink }
        }
        background: Rectangle {
            radius: 9
            color: action.primary ? (action.hovered ? "#f0cca0" : studio.accent) : (action.hovered ? "#313a3f" : action.quiet ? "transparent" : "#262e32")
            border.color: action.activeFocus ? studio.accent : action.primary || action.quiet ? "transparent" : "#41494b"
            Behavior on color { ColorAnimation { duration: studio.reduced ? 0 : 120 } }
        }
    }
    component TrackSlider: Slider {
        id: slider
        implicitHeight: 26
        background: Rectangle {
            x: slider.leftPadding; y: slider.height / 2 - 2; width: slider.availableWidth; height: 4; radius: 2; color: "#3a4447"
            Rectangle { width: parent.width * slider.visualPosition; height: parent.height; radius: 2; color: studio.accent }
        }
        handle: Rectangle {
            x: slider.leftPadding + slider.visualPosition * (slider.availableWidth - width); y: slider.height / 2 - 6
            width: 12; height: 12; radius: 6; color: "#f0d4ac"; border.color: "#a98353"
            scale: slider.pressed ? 1.2 : 1
            Behavior on scale { NumberAnimation { duration: studio.reduced ? 0 : 100 } }
        }
    }

    Canvas {
        anchors.fill: parent
        onPaint: {
            const c = getContext("2d")
            c.reset()
            let wash = c.createRadialGradient(width * .72, 10, 0, width * .72, 10, width * .82)
            wash.addColorStop(0, "#303a3e"); wash.addColorStop(1, "#15191c")
            c.fillStyle = wash; c.fillRect(0, 0, width, height)
            let seed = 7341
            for (let i = 0; i < 26000; i++) {
                seed = (seed * 16807) % 2147483647
                const x = seed % width
                seed = (seed * 16807) % 2147483647
                c.fillStyle = i % 2 ? "rgba(255,255,255,.024)" : "rgba(0,0,0,.07)"
                c.fillRect(x, seed % height, 1, 1)
            }
        }
    }

    Rectangle {
        width: parent.width; height: 44; color: "#14191c"
        Copy { x: 22; anchors.verticalCenter: parent.verticalCenter; text: "TESSERA PIANO"; font.pixelSize: 10; font.letterSpacing: 2.5; color: "#c2c4bd" }
        Copy { x: 211; anchors.verticalCenter: parent.verticalCenter; text: "/   Prévia visual 4.1 · 01"; font.pixelSize: 11; color: "#747e81" }
        Icon { anchors.right: parent.right; anchors.rightMargin: 24; anchors.verticalCenter: parent.verticalCenter; text: "\uE8A7"; font.pixelSize: 12; color: "#929c9d" }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#343d40"; opacity: .6 }
    }

    Rectangle {
        x: 0; y: 44; width: 208; height: parent.height - 160
        gradient: Gradient { GradientStop { position: 0; color: "#1b2023" } GradientStop { position: 1; color: "#14191c" } }
        Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: "#343d40"; opacity: .6 }
        Image { x: 24; y: 32; width: 36; height: 36; source: "../../../src/tessera_piano/resources/icons/tessera-48.png"; sourceSize.width: 96; sourceSize.height: 96 }
        Copy { x: 70; y: 31; text: "tessera"; font.pixelSize: 24; font.weight: Font.DemiBold; font.letterSpacing: -.9 }
        Caption { x: 72; y: 61; text: "P I A N O"; font.pixelSize: 8; color: "#bab6a9" }
        Caption { x: 28; y: 130; text: "SEU REPERTÓRIO"; font.pixelSize: 9 }
        Column {
            x: 16; y: 155; width: 176; spacing: 7
            Repeater {
                model: [{label: "Biblioteca", glyph: "\uE8F1"}, {label: "Favoritos", glyph: "\uE734"}, {label: "Reprodução", glyph: "\uE768"}]
                Button {
                    id: nav
                    required property var modelData
                    required property int index
                    width: 176; height: 45; hoverEnabled: true
                    Accessible.name: modelData.label
                    background: Rectangle { radius: 9; color: nav.index === 2 ? "#38352f" : nav.hovered ? "#252d31" : "transparent"; border.color: nav.index === 2 ? "#5a4d3a" : "transparent"; Behavior on color { ColorAnimation { duration: 120 } } }
                    Icon { x: 15; anchors.verticalCenter: parent.verticalCenter; text: nav.modelData.glyph; font.pixelSize: 15; color: nav.index === 2 ? studio.accent : studio.muted }
                    Copy { x: 44; anchors.verticalCenter: parent.verticalCenter; text: nav.modelData.label; color: nav.index === 2 ? "#f0d3a8" : "#acb1af"; font.weight: nav.index === 2 ? Font.DemiBold : Font.Normal }
                    Rectangle { x: 1; y: 14; width: 2; height: 17; radius: 1; color: studio.accent; visible: nav.index === 2 }
                }
            }
        }
        Caption { x: 28; y: 346; text: "COLEÇÃO TESSERA"; font.pixelSize: 9 }
        Copy { x: 28; y: 378; text: "9 músicas incluídas"; font.pixelSize: 12; color: "#b1b8b5" }
        Copy { x: 28; y: 405; text: "Do clássico ao original."; font.pixelSize: 10; color: "#7e8c8c" }
        Rectangle {
            x: 20; y: parent.height - 220; width: 168; height: 94; radius: 12; color: "#222a2d"; border.color: "#364144"
            Icon { x: 14; y: 15; text: "\uE765"; color: studio.accent; font.pixelSize: 16 }
            Copy { x: 40; y: 14; text: "Pronto para o piano"; font.pixelSize: 11 }
            Copy { x: 14; y: 41; width: 140; text: "F6 inicia · F8 interrompe\nSelecione o Roblox ao iniciar."; font.pixelSize: 10; lineHeight: 1.5; color: studio.muted }
        }
        Action { x: 17; y: parent.height - 106; width: 174; text: "Configurações"; symbol: "\uE713"; quiet: true }
        Copy { x: 30; y: parent.height - 45; text: "ESTUDO DE INTERFACE  /  01"; font.pixelSize: 8; font.letterSpacing: 1.1; color: "#7e898a" }
    }

    Caption { x: 242; y: 77; text: "ESTÚDIO  /  REPRODUÇÃO"; color: "#a5adab"; font.pixelSize: 9 }
    Copy { x: 240; y: 95; text: "O piano em primeiro plano."; font.pixelSize: 26; font.weight: Font.DemiBold; font.letterSpacing: -.6 }
    Action { x: parent.width - 146; y: 82; width: 114; text: "Importar MIDI"; symbol: "\uE898" }

    Surface {
        id: hero
        x: 240; y: 150; width: studio.contentWidth; height: 176; clip: true
        gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#333b3c" } GradientStop { position: .55; color: "#2b3335" } GradientStop { position: 1; color: "#20272b" } }
        Canvas {
            anchors.fill: parent
            onPaint: {
                let c = getContext("2d"); c.reset()
                let light = c.createRadialGradient(width - 180, 28, 0, width - 180, 28, 330)
                light.addColorStop(0, "rgba(221,173,104,.23)"); light.addColorStop(1, "rgba(221,173,104,0)")
                c.fillStyle = light; c.fillRect(0, 0, width, height)
                c.save(); c.translate(width - 360, 39); c.rotate(-.26)
                c.beginPath(); c.moveTo(30, 105); c.lineTo(36, 9); c.bezierCurveTo(110, -17, 128, -42, 210, -9); c.bezierCurveTo(258, 11, 251, 62, 318, 89); c.lineTo(318, 113); c.closePath()
                let lid = c.createLinearGradient(60, -25, 260, 130); lid.addColorStop(0, "#5a6260"); lid.addColorStop(.07, "#3b4444"); lid.addColorStop(.65, "#1c2427"); lid.addColorStop(1, "#13191c")
                c.shadowColor = "#111618"; c.shadowBlur = 20; c.shadowOffsetY = 13; c.fillStyle = lid; c.fill(); c.shadowBlur = 0; c.shadowOffsetY = 0; c.strokeStyle = "#8f8266"; c.lineWidth = 1; c.stroke()
                c.save(); c.clip()
                for (let i = 0; i < 29; i++) { c.beginPath(); c.moveTo(68 + i * 7.4, -25); c.lineTo(46 + i * 8.3, 92); c.strokeStyle = i % 3 ? "rgba(201,172,123,.13)" : "rgba(224,190,131,.28)"; c.lineWidth = .7; c.stroke() }
                c.restore()
                c.fillStyle = "#10171a"; c.fillRect(32, 88, 286, 79)
                for (let k = 0; k < 23; k++) {
                    const x = 37 + k * 12
                    let ivory = c.createLinearGradient(0, 93, 0, 160); ivory.addColorStop(0, "#a7b0ae"); ivory.addColorStop(.24, "#e3e1d4"); ivory.addColorStop(.89, "#d0cbbd"); ivory.addColorStop(1, "#8a918c")
                    c.fillStyle = ivory; c.fillRect(x, 93, 11, 67)
                    c.fillStyle = "#8e9995"; c.fillRect(x, 159, 11, 3)
                    if ([0, 1, 3, 4, 5].includes(k % 7)) { c.fillStyle = "#10171b"; c.fillRect(x + 7, 92, 8, 42); c.fillStyle = "#303b3f"; c.fillRect(x + 8, 94, 6, 3) }
                }
                c.restore()
            }
        }
        Caption { x: 24; y: 23; text: "REPERTÓRIO ORIGINAL"; color: "#d9bc8d"; font.pixelSize: 9 }
        Text { x: 23; y: 45; text: "Entre Órbitas"; color: "#f0ede2"; font.family: "Georgia"; font.pixelSize: 39; font.letterSpacing: -1.2 }
        Copy { x: 25; y: 102; text: "Piano solo  ·  Composição original  ·  2:20"; font.pixelSize: 12; color: "#c0c3b9" }
        Row {
            x: 24; y: 136; spacing: 17
            Copy { text: "88 teclas"; font.pixelSize: 10; color: "#acb6af" }
            Rectangle { width: 1; height: 12; color: "#606a64" }
            Copy { text: "Pedal contextual"; font.pixelSize: 10; color: "#acb6af" }
        }
        Action { anchors.right: parent.right; anchors.rightMargin: 16; y: 14; width: 32; height: 30; text: "···"; quiet: true }
    }

    Surface {
        x: 240; y: 344; width: studio.contentWidth; height: 251; color: "#192024"
        Caption { x: 20; y: 18; text: "PARTITURA EM MOVIMENTO"; font.pixelSize: 9 }
        Copy { anchors.right: parent.right; anchors.rightMargin: 20; y: 17; text: "0:00 — 0:32"; font.pixelSize: 10; color: studio.muted }
        Rectangle { x: 0; y: 43; width: parent.width; height: 1; color: "#303a3e" }
        Canvas {
            id: score
            x: 0; y: 44; width: parent.width; height: parent.height - 44
            onPaint: {
                const c = getContext("2d"); c.reset()
                const left = 42, top = 22, span = width - 62, usable = height - 48
                for (let i = 0; i <= 8; i++) {
                    const x = left + span * i / 8
                    c.strokeStyle = "#303c40"; c.lineWidth = .7; c.beginPath(); c.moveTo(x, 10); c.lineTo(x, height - 25); c.stroke()
                    c.fillStyle = "#77878a"; c.font = "9px 'Segoe UI'"; c.fillText("0:" + ("0" + i * 4).slice(-2), x - 10, height - 9)
                }
                for (let p = 36; p <= 84; p += 12) {
                    const y = top + (88 - p) / 58 * usable
                    c.strokeStyle = "#2c373b"; c.beginPath(); c.moveTo(35, y); c.lineTo(width - 18, y); c.stroke()
                    c.fillStyle = "#697b7e"; c.font = "9px 'Segoe UI'"; c.fillText("C" + (p / 12 - 1), 12, y + 3)
                }
                for (let n of previewNotes) {
                    if (n.start > 32) continue
                    const x = left + n.start / 32 * span, y = top + (88 - n.pitch) / 58 * usable
                    c.fillStyle = n.pitch >= 60 ? "#d7b580" : "#759c9b"; c.globalAlpha = n.start < studio.playhead ? .42 : .92
                    c.fillRect(x, y, Math.max(3, Math.min(n.duration, 32 - n.start) / 32 * span - 1), n.pitch >= 60 ? 4 : 3)
                }
                c.globalAlpha = 1
            }
        }
        Rectangle {
            x: 42 + Math.min(32, studio.playhead) / 32 * (parent.width - 62) - 10; y: 45; width: 21; height: parent.height - 68
            gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "#00e7bb7e" } GradientStop { position: .5; color: "#22e7bb7e" } GradientStop { position: 1; color: "#00e7bb7e" } }
            Rectangle { x: 10; width: 1; height: parent.height; color: studio.accent }
            Rectangle { x: 7; y: 0; width: 7; height: 5; radius: 2; color: studio.accent }
        }
    }

    Surface {
        id: instrument
        x: 240; y: 613; width: studio.contentWidth; height: 171
        gradient: Gradient { GradientStop { position: 0; color: "#333d40" } GradientStop { position: .19; color: "#262f33" } GradientStop { position: 1; color: "#151c20" } }
        Caption { x: 20; y: 15; text: "TECLADO"; font.pixelSize: 9; color: "#a8b4b0" }
        Copy { anchors.right: parent.right; anchors.rightMargin: 20; y: 14; text: "88 TECLAS  /  A0 – C8"; font.pixelSize: 9; font.letterSpacing: .8; color: "#a8b4b0" }
        Rectangle {
            x: 14; y: 40; width: parent.width - 28; height: 115; radius: 7; color: "#0d1418"; border.color: "#465356"
            Item {
                id: keys
                x: 5; y: 5; width: parent.width - 10; height: 102
                readonly property real unit: width / studio.whites.length
                Repeater {
                    model: studio.whites
                    Rectangle {
                        required property int index
                        required property int modelData
                        readonly property bool sounding: [45, 57, 64, 69].includes(modelData)
                        x: index * keys.unit; width: keys.unit - 1; height: keys.height; radius: 2
                        gradient: Gradient {
                            GradientStop { position: 0; color: sounding ? "#d1ac73" : "#b9c3c1" }
                            GradientStop { position: .16; color: sounding ? "#e4c48f" : "#ecece3" }
                            GradientStop { position: .92; color: sounding ? "#e4bb7c" : "#dbddd5" }
                            GradientStop { position: 1; color: sounding ? "#9f7950" : "#909c99" }
                        }
                        Copy { visible: modelData % 12 === 0; anchors.bottom: parent.bottom; anchors.bottomMargin: 9; anchors.horizontalCenter: parent.horizontalCenter; text: "C" + (Math.floor(modelData / 12) - 1); font.pixelSize: 8; color: "#646e68" }
                    }
                }
                Repeater {
                    model: studio.blacks
                    Rectangle {
                        required property int modelData
                        x: (studio.whites.indexOf(modelData - 1) + 1) * keys.unit - width / 2; width: keys.unit * .65; height: 66; radius: 2
                        gradient: Gradient { GradientStop { position: 0; color: "#3e4b50" } GradientStop { position: .1; color: "#253039" } GradientStop { position: .87; color: "#10191f" } GradientStop { position: 1; color: "#354149" } }
                        border.color: "#111a20"
                        Rectangle { x: 2; y: 3; width: parent.width - 4; height: 1; color: "#677477"; opacity: .5 }
                    }
                }
            }
        }
    }
    Copy { x: 243; y: 800; text: "Clique na partitura para escolher de onde começar."; font.pixelSize: 11; color: "#8a9999" }
    Row {
        x: 240 + studio.contentWidth - 131; y: 801; spacing: 7
        Rectangle { width: 5; height: 5; radius: 3; color: "#95b8a5"; anchors.verticalCenter: parent.verticalCenter }
        Copy { text: "Pedal contextual"; font.pixelSize: 10; color: "#acbdb0" }
    }

    Surface {
        id: inspector
        x: 260 + studio.contentWidth; y: 150; width: 252; height: 634
        gradient: Gradient { GradientStop { position: 0; color: "#293236" } GradientStop { position: 1; color: "#1b2428" } }
        Caption { x: 20; y: 23; text: "SUA INTERPRETAÇÃO"; color: "#bdc5bf"; font.pixelSize: 9 }
        Copy { x: 20; y: 58; text: "Caráter"; font.pixelSize: 12; color: "#c3cbc6" }
        Action {
            id: styleSelect
            objectName: "styleSelect"
            x: 20; y: 83; width: 212; height: 43; text: studio.styles[studio.interpretation]
            onClicked: interpretationMenu.open()
            Icon { x: 18; anchors.verticalCenter: parent.verticalCenter; text: "\uE8D6"; color: studio.accent; font.pixelSize: 13 }
            Icon { anchors.right: parent.right; anchors.rightMargin: 13; anchors.verticalCenter: parent.verticalCenter; text: "\uE70D"; font.pixelSize: 10; color: studio.muted }
        }
        Copy { x: 20; y: 139; width: 208; text: "Fraseado sutil e ataques\nmenos uniformes."; font.pixelSize: 11; lineHeight: 1.45; color: "#99aaa9" }
        Copy { x: 20; y: 194; text: "Intensidade"; font.pixelSize: 12; color: "#c3cbc6" }
        Copy { anchors.right: parent.right; anchors.rightMargin: 20; y: 195; text: Math.round(intensity.value) + "%"; font.pixelSize: 11; color: studio.accent }
        TrackSlider { id: intensity; x: 16; y: 219; width: 220; from: 0; to: 100; value: 42 }
        Rectangle { x: 20; y: 270; width: 212; height: 1; color: "#3a4548" }
        Copy { x: 20; y: 293; text: "Pedal de sustentação"; font.pixelSize: 12; color: "#c3cbc6" }
        Action {
            id: pedalSelect
            x: 20; y: 319; width: 212; height: 43; text: studio.pedals[studio.pedal]
            onClicked: pedalMenu.open()
            Icon { anchors.right: parent.right; anchors.rightMargin: 13; anchors.verticalCenter: parent.verticalCenter; text: "\uE70D"; font.pixelSize: 10; color: studio.muted }
        }
        Copy { x: 20; y: 375; width: 208; text: "Segue o MIDI ou cria o pedal\na partir das frases da música."; font.pixelSize: 11; lineHeight: 1.45; color: "#99aaa9" }
        Rectangle { x: 20; y: 433; width: 212; height: 1; color: "#3a4548" }
        Copy { x: 20; y: 456; text: "Alcance do piano"; font.pixelSize: 12; color: "#c3cbc6" }
        Rectangle {
            x: 20; y: 484; width: 212; height: 39; radius: 9; color: "#151f24"; border.color: "#3d484b"
            Rectangle { x: 107; y: 3; width: 102; height: 33; radius: 7; color: "#485153"; border.color: "#626a66" }
            Copy { x: 28; anchors.verticalCenter: parent.verticalCenter; text: "61 teclas"; font.pixelSize: 11; color: "#91a09f" }
            Copy { x: 135; anchors.verticalCenter: parent.verticalCenter; text: "88 teclas"; font.pixelSize: 11; color: "#eee9dd" }
        }
        Icon { x: 20; y: 555; text: "\uE946"; font.pixelSize: 13; color: studio.accent }
        Copy { x: 44; y: 553; width: 179; text: "Ative também o modo\n88key no Visual Pianos."; font.pixelSize: 11; lineHeight: 1.45; color: "#a4b3af" }
    }

    Popup {
        id: interpretationMenu
        objectName: "interpretationPopup"
        parent: Overlay.overlay
        x: inspector.x + 20; y: inspector.y + 132; width: 212; padding: 5
        popupType: Popup.Item
        focus: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        background: Rectangle { radius: 11; color: "#10181c"; border.color: "#53605f"; Rectangle { x: 1; y: parent.height; width: parent.width - 2; height: 8; color: "#22101618"; radius: 6 } }
        contentItem: Column {
            Repeater {
                model: studio.styles
                Button {
                    id: option
                    required property string modelData
                    required property int index
                    width: 202; height: 44; hoverEnabled: true
                    Accessible.name: modelData
                    onClicked: { studio.interpretation = index; interpretationMenu.close() }
                    background: Rectangle { radius: 7; color: option.hovered || option.activeFocus ? "#37413e" : option.index === studio.interpretation ? "#2b3635" : "transparent" }
                    Copy { x: 12; anchors.verticalCenter: parent.verticalCenter; text: option.modelData; color: option.index === studio.interpretation ? "#f1d4a8" : "#d6dfd7"; font.pixelSize: 12 }
                    Icon { anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: "\uE73E"; font.pixelSize: 11; color: studio.accent; visible: option.index === studio.interpretation }
                }
            }
        }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: studio.reduced ? 0 : 160; easing.type: Easing.OutCubic } NumberAnimation { property: "scale"; from: .97; to: 1; duration: studio.reduced ? 0 : 160; easing.type: Easing.OutCubic } }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: studio.reduced ? 0 : 100 } }
    }
    Popup {
        id: pedalMenu
        parent: Overlay.overlay
        x: inspector.x + 20; y: inspector.y + 368; width: 212; padding: 5; focus: true; popupType: Popup.Item
        background: Rectangle { radius: 11; color: "#10181c"; border.color: "#53605f" }
        contentItem: Column {
            Repeater {
                model: studio.pedals
                Action { required property string modelData; required property int index; width: 202; height: 39; text: modelData; quiet: index !== studio.pedal; onClicked: { studio.pedal = index; pedalMenu.close() } }
            }
        }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: studio.reduced ? 0 : 160 } }
    }

    Rectangle {
        x: 0; y: parent.height - 116; width: parent.width; height: 116
        gradient: Gradient { GradientStop { position: 0; color: "#283034" } GradientStop { position: .07; color: "#1c2428" } GradientStop { position: 1; color: "#141b20" } }
        Rectangle { width: parent.width; height: 1; color: "#495450" }
        Rectangle {
            x: 24; y: 27; width: 62; height: 62; radius: 11; color: "#353f3e"; border.color: "#56615a"
            Repeater { model: 3; Rectangle { required property int index; x: 14 + index * 12; y: 19 - index * 3; width: 7; height: 29; radius: 2; color: index === 1 ? "#e7bb7e" : "#babaa8"; rotation: 16 } }
        }
        Copy { x: 102; y: 32; text: "Entre Órbitas"; font.pixelSize: 14; font.weight: Font.DemiBold }
        Copy { x: 102; y: 57; text: "Piano solo  ·  " + studio.styles[studio.interpretation]; font.pixelSize: 11; color: studio.muted }
        Action { x: 331; y: 36; width: 42; text: ""; symbol: "\uE72B"; quiet: true; Accessible.name: "Voltar ao início da prévia"; onClicked: studio.playhead = 0 }
        Action { id: play; objectName: "previewPlay"; x: 382; y: 34; width: 137; height: 45; text: studio.playing ? "Pausar prévia" : "Reproduzir"; symbol: studio.playing ? "\uE769" : "\uE768"; primary: true; onClicked: studio.playing = !studio.playing }
        TrackSlider { id: timeline; x: 550; y: 35; width: parent.width - 798; from: 0; to: 140.357; value: studio.playhead; onMoved: studio.playhead = value }
        Copy { x: 555; y: 68; text: studio.timeText(studio.playhead); font.pixelSize: 10; color: "#c6c7ba" }
        Copy { x: parent.width - 275; y: 68; text: "2:20"; font.pixelSize: 10; color: studio.muted }
        Rectangle { x: parent.width - 224; y: 30; width: 1; height: 57; color: "#3e494c" }
        Copy { x: parent.width - 201; y: 37; text: "100%"; font.pixelSize: 15; color: "#dddccf" }
        Caption { x: parent.width - 201; y: 63; text: "VELOCIDADE"; font.pixelSize: 8; font.letterSpacing: .9 }
        Rectangle { x: parent.width - 102; y: 38; width: 31; height: 24; radius: 5; color: "#2b3539"; border.color: "#4a5657"; Copy { anchors.centerIn: parent; text: "F6"; font.pixelSize: 10; color: "#c6cdbf" } }
        Copy { x: parent.width - 109; y: 70; text: "INICIAR"; font.pixelSize: 8; font.letterSpacing: 1; color: "#8e9d9a" }
    }
    Timer { interval: 40; running: studio.playing; repeat: true; onTriggered: { studio.playhead = (studio.playhead + .04) % 32; score.requestPaint() } }
}
