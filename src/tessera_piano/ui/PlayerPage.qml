import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: page
    readonly property bool wide: width >= 1000
    function restoreOptionsFocus() { optionsButton.forceActiveFocus() }
    spacing: 20
    ColumnLayout {
        Layout.fillWidth: true; Layout.fillHeight: true; spacing: 16
        Surface {
            Layout.fillWidth: true; Layout.preferredHeight: page.wide ? 160 : 144
            StudioArt { anchors.right: parent.right; width: Math.min(360, parent.width * .48); height: parent.height; opacity: page.wide ? .85 : .38; clip: true }
            Column {
                x: 22; y: 20; width: parent.width - 44; spacing: 10
                Text { text: backend.song.personal ? "BIBLIOTECA PESSOAL" : "COLEÇÃO TESSERA"; color: Theme.accent; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.6 }
                Text { width: parent.width; text: backend.song.title; elide: Text.ElideRight; color: Theme.text; font.family: Theme.titleFont; font.pixelSize: page.wide ? 32 : 29; font.letterSpacing: -.8 }
                Text { text: backend.song.preparing ? "Preparando… " + Math.round(backend.features.analysisProgress * 100) + "%" : root.timeText(backend.song.duration) + "  ·  " + backend.settings.layout + " teclas"; color: Theme.muted; font.family: Theme.font; font.pixelSize: 12 }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 14; anchors.bottom: parent.bottom; anchors.bottomMargin: 12; spacing: 6
                TButton { text: "Cancelar preparação"; compact: true; visible: backend.song.preparing; onClicked: backend.cancelPreparation() }
                TButton {
                    objectName: "interpretationButton"
                    text: "Interpretação"; compact: true; visible: !page.wide
                    onClicked: settingsPopup.open()
                    TPopup {
                        id: settingsPopup; objectName: "performancePopup"
                        y: parent.height + 6; width: 274; padding: 20
                        contentItem: Loader { active: settingsPopup.visible; sourceComponent: performanceContent }
                    }
                }
                TButton { glyph: backend.song.favorite ? "\uE735" : "\uE734"; compact: true; Accessible.name: "Favoritar música"; onClicked: backend.toggleFavorite(); enabled: backend.song.id !== "" }
                TButton {
                    objectName: "tracksButton"
                    text: "Faixas"; compact: true; visible: backend.song.tracks.length > 1; enabled: !backend.playback.busy
                    onClicked: tracksPopup.open()
                    TPopup {
                        id: tracksPopup; objectName: "tracksPopup"
                        y: parent.height + 6; width: 300
                        implicitHeight: Math.min(300, backend.song.tracks.length * 44 + 12)
                        contentItem: ListView {
                            id: tracksList; clip: true
                            model: backend.song.tracks; keyNavigationEnabled: true; activeFocusOnTab: true
                            ScrollBar.vertical: ScrollBar {}
                            delegate: TCheck {
                                required property var modelData
                                objectName: "track-" + modelData.id
                                width: tracksList.width
                                text: (modelData.id + 1) + ". " + (modelData.name || "Faixa sem nome")
                                checked: backend.settings.track_filter.length === 0 || backend.settings.track_filter.indexOf(modelData.id) >= 0
                                nextCheckState: function() {
                                    backend.toggleTrack(modelData.id)
                                    return backend.settings.track_filter.length === 0 || backend.settings.track_filter.indexOf(modelData.id) >= 0 ? Qt.Checked : Qt.Unchecked
                                }
                            }
                        }
                    }
                }
                TButton {
                    id: optionsButton
                    objectName: "songOptions"
                    glyph: "\uE712"; compact: true; Accessible.name: "Opções da música"
                    enabled: backend.song.id !== "" && !backend.playback.busy
                    onClicked: songMenu.open()
                    TMenu {
                        id: songMenu; objectName: "songMenu"; width: 225; y: parent.height + 6
                        onClosed: { if (!renameDialog.visible && !deleteDialog.visible) parent.forceActiveFocus() }
                        TMenuItem { objectName: "renameAction"; text: "Renomear"; onTriggered: renameDialog.open() }
                        TMenuItem { objectName: "deleteAction"; text: "Remover da biblioteca"; danger: true; onTriggered: deleteDialog.open() }
                    }
                }
            }
        }
        PianoRoll {
            objectName: "pianoRoll"
            Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 140
            notes: backend.notes; duration: Math.max(.001, backend.song.duration); position: backend.playback.position
            lowPitch: backend.settings.layout === "88" ? 21 : 36
            highPitch: backend.settings.layout === "88" ? 108 : 96
            onSeek: seconds => backend.seek(seconds)
        }
        Surface {
            Layout.fillWidth: true; Layout.preferredHeight: page.height < 550 ? 132 : 151
            RowLayout {
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 16
                Text { text: "TECLADO"; Layout.fillWidth: true; color: Theme.muted; font.family: Theme.font; font.pixelSize: 9; font.letterSpacing: 1.4 }
                Text { text: backend.playback.pedalManaged ? "Pedal " + (backend.playback.pedal ? "ligado" : "desligado") : "Pedal " + backend.song.pedal; color: Theme.muted; font.family: Theme.font; font.pixelSize: 10 }
            }
            Rectangle {
                anchors.fill: parent; anchors.topMargin: 37; anchors.bottomMargin: 13; anchors.leftMargin: 13; anchors.rightMargin: 13
                radius: 6; color: "#10191e"; border.color: Theme.line
                Keyboard { anchors.fill: parent; anchors.margins: 4; extended: backend.settings.layout === "88"; activeNotes: backend.playback.active }
            }
        }
        Text {
            Layout.fillWidth: true
            text: backend.playback.status === "countdown" ? "Selecione o piano no Roblox. Começa em " + backend.playback.countdown + " s." : (backend.features.summary || "F6 inicia · F8 encerra suavemente · Esc interrompe.")
            font.family: Theme.font; font.pixelSize: 11; color: Theme.muted
        }
    }
    Surface {
        visible: page.wide; Layout.preferredWidth: 246; Layout.fillHeight: true
        Loader { anchors.fill: parent; anchors.margins: 20; sourceComponent: performanceContent; active: page.wide }
    }
    Component { id: performanceContent; PerformancePanel {} }
    TDialog {
        id: renameDialog; objectName: "renameDialog"
        title: "Renomear música"; acceptText: "Salvar nome"; acceptName: "renameAccept"
        canAccept: nameField.text.trim().length > 0
        onOpened: { nameField.text = backend.song.title; nameField.forceActiveFocus(); nameField.selectAll() }
        onClosed: page.restoreOptionsFocus()
        onAccepted: backend.renameSong(nameField.text)
        contentItem: TField { id: nameField; objectName: "renameField"; Accessible.name: "Nome da música"; onAccepted: { if (renameDialog.canAccept) renameDialog.accept() } }
    }
    TDialog {
        id: deleteDialog; objectName: "deleteDialog"
        title: "Remover da biblioteca?"; acceptText: "Remover"; acceptName: "deleteAccept"; destructive: true
        onAccepted: backend.deleteSong()
        onClosed: page.restoreOptionsFocus()
        contentItem: Text { text: "Você pode desfazer nas configurações. O arquivo original será preservado."; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
    }
}
