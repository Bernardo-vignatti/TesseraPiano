import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    spacing: 18
    RowLayout {
        Layout.fillWidth: true
        ColumnLayout {
            Layout.fillWidth: true; spacing: 7
            Text { text: backend.song.title; Layout.fillWidth: true; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 25; font.weight: Font.DemiBold; color: Theme.text }
            Text { text: backend.song.notes + " notas  ·  " + backend.settings.layout + " teclas  ·  Pedal " + backend.song.pedal; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
        }
        TButton { glyph: backend.song.favorite ? "\uE735" : "\uE734"; Accessible.name: "Favoritar música"; onClicked: backend.toggleFavorite(); enabled: backend.song.id !== "" }
        TButton { text: "Faixas"; visible: backend.song.tracks.length > 1; enabled: !backend.playback.busy; onClicked: tracksPopup.open()
            Popup {
                id: tracksPopup; y: parent.height + 5; width: 300; padding: 8
                background: Rectangle { radius: 8; color: Theme.surface; border.color: Theme.line }
                contentItem: Column {
                    Repeater { model: backend.song.tracks
                        CheckDelegate {
                            required property var modelData
                            width: 284
                            text: (modelData.id + 1) + ". " + (modelData.name || "Faixa sem nome")
                            checked: backend.settings.track_filter.length === 0 || backend.settings.track_filter.indexOf(modelData.id) >= 0
                            onClicked: backend.toggleTrack(modelData.id)
                            palette.text: Theme.text; palette.highlight: Theme.accent
                        }
                    }
                }
            }
        }
        TButton { glyph: "\uE712"; Accessible.name: "Mais opções da música"; onClicked: songMenu.open(); enabled: backend.song.id !== ""
            Menu {
                id: songMenu
                MenuItem { text: "Renomear"; onTriggered: renameDialog.open() }
                MenuItem { text: "Remover da biblioteca"; onTriggered: deleteDialog.open() }
            }
        }
    }
    RowLayout {
        Layout.fillWidth: true; Layout.topMargin: 6; spacing: 14
        Text { text: "Interpretação"; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
        Choice {
            model: ["Original", "Natural", "Expressivo"]
            currentIndex: ["original","natural","expressive"].indexOf(backend.settings.performance)
            onActivated: index => backend.setSetting("performance",["original","natural","expressive"][index])
            enabled: !backend.playback.busy
        }
        Text { text: "Pedal"; Layout.leftMargin: 8; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
        Choice {
            model: ["Automático", "Apenas MIDI", "Ligado", "Desligado", "Manual"]
            currentIndex: ["auto","midi","on","off","ignore"].indexOf(backend.settings.pedal_mode)
            onActivated: index => backend.setSetting("pedal_mode",["auto","midi","on","off","ignore"][index])
            enabled: !backend.playback.busy
        }
        Item { Layout.fillWidth: true }
        Text { text: backend.song.preparing ? "Preparando…" : ""; font.family: Theme.font; font.pixelSize: 11; color: Theme.accent }
    }
    PianoRoll {
        objectName: "pianoRoll"
        Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 150
        notes: backend.notes; duration: Math.max(.001,backend.song.duration); position: backend.playback.position
        lowPitch: backend.settings.layout === "88" ? 21 : 36
        highPitch: backend.settings.layout === "88" ? 108 : 96
        onSeek: seconds => backend.seek(seconds)
    }
    RowLayout {
        Layout.fillWidth: true
        Text { text: "Clique na linha do tempo para escolher o ponto inicial."; Layout.fillWidth: true; font.family: Theme.font; font.pixelSize: 11; color: Theme.faint }
        Rectangle { width: 6; height: 6; radius: 3; color: backend.playback.pedalManaged && backend.playback.pedal ? Theme.green : Theme.faint }
        Text { text: backend.playback.pedalManaged ? "Pedal " + (backend.playback.pedal ? "ligado" : "desligado") : "Pedal " + backend.song.pedal; font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
    }
    Keyboard { Layout.fillWidth: true; Layout.preferredHeight: 105; extended: backend.settings.layout === "88"; activeNotes: backend.playback.active }
    Text {
        Layout.fillWidth: true; Layout.bottomMargin: 8
        text: backend.playback.status === "countdown" ? "Selecione o piano no Roblox. A execução começa ao terminar a contagem." : "Abra o piano no Roblox e feche o chat. F6 inicia; F8 ou Esc interrompem."
        wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted
    }
    Dialog {
        id: renameDialog; title: "Renomear música"; modal: true
        anchors.centerIn: Overlay.overlay; width: 420
        standardButtons: Dialog.Ok | Dialog.Cancel
        onOpened: { nameField.text=backend.song.title; nameField.forceActiveFocus(); nameField.selectAll() }
        onAccepted: backend.renameSong(nameField.text)
        contentItem: TextField { id: nameField; font.family: Theme.font; selectByMouse: true; onAccepted: renameDialog.accept() }
    }
    Dialog {
        id: deleteDialog; title: "Remover da biblioteca?"; modal: true
        anchors.centerIn: Overlay.overlay; width: 440
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: backend.deleteSong()
        contentItem: Text { text: "Você poderá desfazer esta ação nas configurações. O arquivo original permanece no lugar."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 14; color: Theme.text }
        background: Rectangle { radius: 10; color: Theme.surface; border.color: Theme.line }
    }
}
