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
    Binding { target: Theme; property: "reduced"; value: backend.settings.reduced_motion }
    Component.onCompleted: { width=backend.settings.window_width; height=backend.settings.window_height; if (!backend.settings.onboarding_completed) wizard.open() }
    Shortcut { sequence: "Ctrl+O"; onActivated: backend.importDialog() }
    Shortcut { sequence: "Ctrl+F"; onActivated: { root.navigate(0,false); library.focusSearch() } }
    Shortcut { sequence: "Ctrl+,"; onActivated: root.page=2 }
    RowLayout {
        anchors.fill: parent; anchors.bottomMargin: transport.height
        spacing: 0
        Rectangle {
            Layout.preferredWidth: 196; Layout.fillHeight: true
            color: Theme.side
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 18; spacing: 6
                RowLayout {
                    Layout.topMargin: 12; Layout.leftMargin: 5; Layout.bottomMargin: 40; spacing: 10
                    Image { source: "../resources/icons/tessera-48.png"; Layout.preferredWidth: 34; Layout.preferredHeight: 34; sourceSize.width: 68; sourceSize.height: 68 }
                    Column {
                        spacing: 3
                        Text { text: "Tessera"; color: Theme.text; font.family: Theme.font; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { text: "P I A N O"; color: Theme.muted; font.family: Theme.font; font.pixelSize: 9 }
                    }
                }
                Text { text: "REPERTÓRIO"; Layout.leftMargin: 12; Layout.bottomMargin: 8; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.6; color: Theme.faint }
                Repeater {
                    model: [{label:"Todas as músicas",icon:"\uE8F1",target:0,fav:false},{label:"Favoritos",icon:"\uE734",target:0,fav:true},{label:"Reprodução",icon:"\uE768",target:1,fav:false}]
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
            Layout.margins: 32; spacing: 26
            RowLayout {
                Layout.fillWidth: true; Layout.topMargin: 1
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Text { text: [root.favoriteView ? "Favoritos" : "Biblioteca","Reprodução","Configurações","Ajuda e sobre"][root.page]; font.family: Theme.font; font.pixelSize: 28; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: ["Seu repertório, pronto para o piano.","Interpretação, articulação e sustentação.","Seu piano. Suas preferências.","Tessera Piano " + backend.version][root.page]; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                }
                Row {
                    spacing: 8
                    Rectangle { width: 6; height: 6; radius: 3; color: backend.playback.busy ? Theme.accent : Theme.green; anchors.verticalCenter: parent.verticalCenter }
                    Text { text: backend.playback.importing ? "IMPORTANDO" : backend.playback.busy ? "EM EXECUÇÃO" : "PRONTO"; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.2; color: Theme.muted }
                }
            }
            StackLayout {
                id: pages
                Layout.fillWidth: true; Layout.fillHeight: true
                currentIndex: root.page
                NumberAnimation { id: pageFade; target: pages; property: "opacity"; from: .4; to: 1; duration: Theme.motion }
                LibraryPage { id: library; onOpenPlayer: root.page=1 }
                PlayerPage { }
                SettingsPage { onSetupRequested: { wizard.step=0; wizard.open() } }
                ScrollView {
                    clip: true; contentWidth: availableWidth
                    ColumnLayout {
                        width: parent.width; spacing: 22
                        Text { text: "Do arquivo ao seu piano"; font.family: Theme.font; font.pixelSize: 24; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "Importe MIDI, piano.json ou uma partitura TXT. Escolha uma música, deixe o piano aberto no Roblox e feche o chat. Pressione F6 e volte ao jogo durante a contagem."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Text { text: "F6  Iniciar     F8 / Esc  Parar     Ctrl+O  Importar     Ctrl+F  Buscar"; font.family: Theme.font; font.pixelSize: 13; color: Theme.accent }
                        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
                        Text { text: "Pedal e interpretação"; font.family: Theme.font; font.pixelSize: 18; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "No Visual Pianos, soltar Espaço liga a sustentação; segurar desliga. O modo Automático segue o MIDI e cria pedalização quando o arquivo não tem CC64. Original preserva o tempo; Natural e Expressivo acrescentam fraseado e articulação. O teclado comum não transmite a intensidade MIDI."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Text { text: "Dados locais e código aberto"; font.family: Theme.font; font.pixelSize: 18; font.weight: Font.DemiBold; color: Theme.text }
                        Text { Layout.fillWidth: true; text: "Músicas, preferências e logs ficam na sua pasta de dados. A desinstalação preserva sua biblioteca. As atualizações consultam o GitHub; o aplicativo não envia suas músicas e não usa telemetria. Código sob MIT; repertório e dependências conservam suas licenças."; wrapMode: Text.WordWrap; lineHeight: 1.4; font.family: Theme.font; font.pixelSize: 14; color: Theme.muted }
                        Flow { Layout.fillWidth: true; spacing: 9
                            TButton { text: "Código e documentação"; glyph: "\uE8A7"; onClicked: backend.openLink("github") }
                            TButton { text: "Visual Pianos"; onClicked: backend.openLink("game") }
                            TButton { text: "Créditos e licenças"; onClicked: backend.openLink("licenses") }
                        }
                        Text { text: "Desenvolvido por Vignatti"; Layout.topMargin: 8; font.family: Theme.font; font.pixelSize: 12; color: Theme.faint }
                    }
                }
            }
        }
    }
    Rectangle {
        id: transport
        anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 104; color: Theme.side
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: Theme.line }
        RowLayout {
            anchors.fill: parent; anchors.leftMargin: 27; anchors.rightMargin: 32; spacing: 22
            ColumnLayout {
                Layout.preferredWidth: 260; Layout.maximumWidth: 300; spacing: 6
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
                Slider {
                    id: timeline
                    Layout.fillWidth: true; implicitHeight: 22
                    from: 0; to: Math.max(.001,backend.song.duration)
                    value: backend.playback.position
                    enabled: !backend.playback.busy
                    onMoved: backend.seek(value)
                    background: Rectangle { x: timeline.leftPadding; y: timeline.topPadding + timeline.availableHeight/2 - 2; width: timeline.availableWidth; height: 3; radius: 2; color: Theme.line
                        Rectangle { width: parent.width * timeline.visualPosition; height: parent.height; radius: 2; color: Theme.accentFill }
                    }
                    handle: Rectangle { x: timeline.leftPadding + timeline.visualPosition * (timeline.availableWidth - width); y: timeline.topPadding + timeline.availableHeight/2 - height/2; width: 9; height: 9; radius: 5; color: timeline.hovered || timeline.pressed ? Theme.accentFill : Theme.muted }
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
    Popup {
        id: notification
        objectName: "notification"
        x: (root.width-width)/2; y: root.height-transport.height-height-18
        width: Math.min(660,root.width-80); padding: 17
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
        property string message: ""
        background: Rectangle { color: Theme.surface; border.color: Theme.line; radius: 9 }
        contentItem: Text { text: notification.message; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 13; color: Theme.text }
        Timer { id: notificationTimer; interval: 6500; onTriggered: notification.close() }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: Theme.motion } }
    }
    Connections { target: backend; function onToast(message) { notification.message=message; notification.open(); notificationTimer.restart() } }
    Welcome { id: wizard; parent: Overlay.overlay }
}
