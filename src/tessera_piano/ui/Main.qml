import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root
    objectName: "mainWindow"
    width: 1280; height: 830
    minimumWidth: 1040; minimumHeight: 720
    visible: true
    title: "Tessera Piano"
    color: Theme.bg
    property int page: 0
    property bool favoriteView: false
    font.family: Theme.font
    palette.window: Theme.bg
    palette.windowText: Theme.text
    palette.text: Theme.text
    palette.base: Theme.surface
    palette.button: Theme.surface
    palette.buttonText: Theme.text
    palette.highlight: Theme.accentTint
    palette.highlightedText: Theme.text
    function timeText(seconds) { return Math.floor(seconds / 60) + ":" + ("0" + Math.floor(seconds % 60)).slice(-2) }
    function navigate(index, favorites) {
        root.page=index; root.favoriteView=favorites
        if (index === 0) backend.setFavorites(favorites)
    }
    onClosing: close => close.accepted=backend.closeWindow()
    onPageChanged: pageFade.restart()
    Binding { target: Theme; property: "light"; value: (wizard.opened && wizard.step > 0 ? wizard.chosenTheme : backend.settings.theme) === "light" || ((wizard.opened && wizard.step > 0 ? wizard.chosenTheme : backend.settings.theme) === "system" && backend.systemLight) }
    Binding { target: Theme; property: "reduced"; value: wizard.opened && wizard.step > 0 ? wizard.chosenMotion : backend.settings.reduced_motion }
    Canvas {
        id: backdrop
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: Theme; function onLightChanged() { backdrop.requestPaint() } }
        onPaint: {
            const c = getContext("2d"); c.reset()
            const wash = c.createRadialGradient(width * .75, 0, 0, width * .75, 0, width)
            wash.addColorStop(0, Theme.backdrop); wash.addColorStop(1, Theme.bg)
            c.fillStyle = wash; c.fillRect(0, 0, width, height)
            let seed = 7341
            for (let i = 0; i < 22000; i++) {
                seed = (seed * 16807) % 2147483647
                const x = seed % Math.max(1, width)
                seed = (seed * 16807) % 2147483647
                c.fillStyle = i % 2 ? "rgba(255,255,255,.025)" : "rgba(0,0,0,.045)"
                c.fillRect(x, seed % Math.max(1, height), 1, 1)
            }
        }
    }
    Component.onCompleted: { width=backend.settings.window_width; height=backend.settings.window_height; if (!backend.settings.onboarding_completed) wizard.open() }
    Shortcut { sequence: "Ctrl+O"; onActivated: backend.importDialog() }
    Shortcut { sequence: "Ctrl+F"; onActivated: { root.navigate(0,false); library.focusSearch() } }
    Shortcut { sequence: "Ctrl+,"; onActivated: root.page=2 }
    RowLayout {
        anchors.fill: parent; anchors.bottomMargin: transport.height
        spacing: 0
        Rectangle {
            Layout.preferredWidth: 208; Layout.fillHeight: true
            gradient: Gradient { GradientStop { position: 0; color: Theme.light ? "#eeebe3" : "#20282c" } GradientStop { position: 1; color: Theme.side } }
            Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: Theme.line; opacity: .6 }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 18; spacing: 6
                RowLayout {
                    Layout.topMargin: 12; Layout.leftMargin: 5; Layout.bottomMargin: 40; spacing: 10
                    Image { source: "../resources/icons/tessera-48.png"; Layout.preferredWidth: 34; Layout.preferredHeight: 34; sourceSize.width: 68; sourceSize.height: 68 }
                    Column {
                        spacing: 3
                        Text { text: "tessera"; color: Theme.text; font.family: Theme.font; font.pixelSize: 23; font.weight: Font.DemiBold; font.letterSpacing: -.7 }
                        Text { text: "P I A N O"; color: Theme.muted; font.family: Theme.font; font.pixelSize: 9 }
                    }
                }
                Text { text: "REPERTÓRIO"; Layout.leftMargin: 12; Layout.bottomMargin: 8; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.6; color: Theme.faint }
                Repeater {
                    model: [{label:"Biblioteca",icon:"\uE8F1",target:0,fav:false},{label:"Favoritos",icon:"\uE734",target:0,fav:true},{label:"Reprodução",icon:"\uE768",target:1,fav:false}]
                    TButton {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 43
                        text: modelData.label; glyph: modelData.icon
                        flat: true; leftAligned: true
                        selected: root.page === modelData.target && (root.page !== 0 || root.favoriteView === modelData.fav)
                        onClicked: root.navigate(modelData.target,modelData.fav)
                    }
                }
                Item { Layout.fillHeight: true }
                Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line; Layout.bottomMargin: 9 }
                Repeater {
                    model: [{label:"Configurações",icon:"\uE713",target:2},{label:"Ajuda e sobre",icon:"\uE946",target:3}]
                    TButton {
                        required property var modelData
                        Layout.fillWidth: true; Layout.preferredHeight: 41
                        text: modelData.label; glyph: modelData.icon
                        flat: true; leftAligned: true
                        selected: root.page === modelData.target
                        onClicked: root.page=modelData.target
                    }
                }
                Text { text: backend.playback.preview ? "PRÉVIA · SEM ENVIO DE TECLAS" : "v" + backend.version; Layout.leftMargin: 12; Layout.topMargin: 15; Layout.bottomMargin: 5; font.family: Theme.font; font.pixelSize: 9; color: Theme.faint }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            Layout.margins: 28; spacing: 22
            Item {
                Layout.fillWidth: true; implicitHeight: 38
                Text { anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; text: [root.favoriteView ? "Favoritos" : "Biblioteca","Reprodução","Configurações","Ajuda e sobre"][root.page]; font.family: Theme.font; font.pixelSize: 28; font.weight: Font.DemiBold; color: Theme.text }
                Row {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    spacing: 8
                    Rectangle { width: 6; height: 6; radius: 3; color: backend.playback.busy ? Theme.accent : Theme.green; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: backend.playback.importing ? "IMPORTANDO" : backend.playback.busy ? "EM EXECUÇÃO" : "PRONTO"; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.2; color: Theme.muted }
                }
            }
            StackLayout {
                id: pages
                objectName: "pages"
                Layout.fillWidth: true; Layout.fillHeight: true
                currentIndex: root.page
                transform: Translate { id: pageOffset }
                ParallelAnimation {
                    id: pageFade
                    NumberAnimation { target: pages; property: "opacity"; from: .65; to: 1; duration: Theme.pageMotion; easing.type: Easing.OutCubic }
                    NumberAnimation { target: pageOffset; property: "y"; from: 8; to: 0; duration: Theme.pageMotion; easing.type: Easing.OutCubic }
                }
                LibraryPage { id: library; onOpenPlayer: root.page=1 }
                PlayerPage { }
                SettingsPage { onSetupRequested: { wizard.step=0; wizard.open() } }
                ScrollView {
                    clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width; spacing: 22
                        Text { text: "Do arquivo ao seu piano"; font.family: Theme.font; font.pixelSize: 24; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "Importe MIDI, JSON ou TXT. Abra o piano no Roblox, feche o chat e pressione F6. Volte ao jogo durante a contagem."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Text { text: "F6  Iniciar     F8 / Esc  Parar     Ctrl+O  Importar     Ctrl+F  Buscar"; font.family: Theme.font; font.pixelSize: 13; color: Theme.accent }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                        Text { text: "Pedal e interpretação"; font.family: Theme.font; font.pixelSize: 18; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "Espaço solto liga a sustentação; segurar desliga. Automático segue o CC64 ou cria pedal contextual. Natural e Expressivo acrescentam fraseado. O teclado comum não transmite velocity MIDI."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Text { text: "Dados locais e código aberto"; font.family: Theme.font; font.pixelSize: 18; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "Sua biblioteca fica neste computador. As atualizações consultam o GitHub; não há telemetria. Código MIT; repertório e dependências mantêm suas licenças."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Flow { Layout.fillWidth: true; spacing: 9
                            TButton { text: "Código e documentação"; glyph: "\uE8A7"; onClicked: backend.openLink("github") }
                            TButton { text: "Visual Pianos"; onClicked: backend.openLink("game") }
                            TButton { text: "Créditos e licenças"; onClicked: backend.openLink("licenses") }
                        }
                        Text { text: "Tessera Piano " + backend.version + " · Vignatti"; Layout.topMargin: 8; font.family: Theme.font; font.pixelSize: 12; color: Theme.faint }
                    }
                }
            }
        }
    }
    Rectangle {
        id: transport
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 100
        gradient: Gradient { GradientStop { position: 0; color: Theme.surfaceTop } GradientStop { position: .12; color: Theme.side } }
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 27; anchors.rightMargin: 32; spacing: 22
            ColumnLayout {
                Layout.preferredWidth: root.width < 1200 ? 190 : 260; Layout.maximumWidth: 300; spacing: 6
                Text { text: backend.song.title; Layout.fillWidth: true; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 13; font.weight: Font.DemiBold; color: Theme.text }
                Text { text: backend.playback.busy ? backend.playback.message : backend.settings.layout + " teclas · " + ({original:"Original",natural:"Natural",expressive:"Expressivo"})[backend.settings.performance]; Layout.fillWidth: true; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
            }
            TButton {
                objectName: "playButton"
                text: backend.playback.busy ? "Parar" : "Reproduzir"
                glyph: backend.playback.busy ? "\uE71A" : "\uE768"
                primary: true
                enabled: backend.playback.busy || backend.song.id !== "" && !backend.song.preparing
                onClicked: backend.playback.busy ? backend.stop() : backend.start()
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 8
                TSlider {
                    id: timeline
                    Layout.fillWidth: true; implicitHeight: 22
                    from: 0; to: Math.max(.001,backend.song.duration)
                    value: backend.playback.position
                    enabled: !backend.playback.busy
                    onMoved: backend.seek(value)
                    Accessible.name: "Posição da música"
                }
                RowLayout {
                    Layout.fillWidth: true
                    Text { text: root.timeText(backend.playback.position) + " / " + root.timeText(backend.song.duration); font.family: Theme.font; font.pixelSize: 10; color: Theme.muted }
                    Item { Layout.fillWidth: true }
                    Text { text: backend.playback.status === "countdown" ? "COMEÇA EM " + backend.playback.countdown + " s" : backend.settings.speed + "%"; font.family: Theme.font; font.pixelSize: 10; color: backend.playback.busy ? Theme.accent : Theme.faint }
                }
            }
            Text { text: backend.playback.busy ? "F8  PARAR" : "F6  INICIAR"; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1; color: Theme.faint }
        }
    }
    DropArea {
        anchors.fill: parent
        onDropped: drop => { if (drop.hasUrls) backend.importPaths(drop.urls.map(url => url.toString())) }
        Rectangle { anchors.fill: parent; color: Theme.accentTint; opacity: .94; visible: parent.containsDrag; border.width: 2; border.color: Theme.accent
            Text { anchors.centerIn: parent; text: "Solte para importar suas músicas"; font.family: Theme.font; font.pixelSize: 25; color: Theme.text }
        }
    }
    TPopup {
        id: notification
        objectName: "notification"
        x: (root.width-width)/2; y: root.height-transport.height-height-18
        width: Math.min(660,root.width-80); padding: 17
        focus: false
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        property string message: ""
        contentItem: Text { text: notification.message; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 13; color: Theme.text }
        Timer { id: notificationTimer; interval: 6500; onTriggered: notification.close() }
    }
    Connections { target: backend; function onToast(message) { notification.message=message; notification.open(); notificationTimer.restart() } }
    Welcome { id: wizard; parent: Overlay.overlay }
}
