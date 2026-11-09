import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: page
    signal openPlayer()
    spacing: 0
    function focusSearch() { search.forceActiveFocus() }
    RowLayout {
        Layout.fillWidth: true
        Layout.bottomMargin: 25
        spacing: 18
        TextField {
            id: search
            objectName: "librarySearch"
            Layout.fillWidth: true
            implicitHeight: 43
            placeholderText: "Buscar no repertório"
            font.family: Theme.font; font.pixelSize: 13
            color: Theme.text; placeholderTextColor: Theme.faint
            leftPadding: 38; selectByMouse: true
            selectionColor: Theme.accentTint
            onTextChanged: backend.setQuery(text)
            background: Rectangle { radius: 7; color: Theme.surface; border.color: search.activeFocus ? Theme.accent : Theme.line }
            Text { text: "\uE721"; font.family: "Segoe MDL2 Assets"; font.pixelSize: 14; color: Theme.muted; x: 13; anchors.verticalCenter: parent.verticalCenter }
        }
        Text { text: backend.songs.length + " músicas"; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
        TButton { text: "Importar"; glyph: "\uE898"; primary: true; enabled: !backend.playback.importing && !backend.playback.busy; onClicked: backend.importDialog() }
    }
    RowLayout {
        Layout.fillWidth: true; Layout.leftMargin: 20; Layout.rightMargin: 20; Layout.bottomMargin: 12
        spacing: 12
        Text { text: "MÚSICA"; Layout.fillWidth: true; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.5; color: Theme.faint }
        Text { text: "NOTAS"; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.3; color: Theme.faint }
        Text { text: "TEMPO"; Layout.preferredWidth: 75; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.3; color: Theme.faint }
        Text { text: "COLEÇÃO"; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 10; font.letterSpacing: 1.3; color: Theme.faint }
        Item { Layout.preferredWidth: 32 }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
    ListView {
        id: list
        objectName: "songList"
        Layout.fillWidth: true; Layout.fillHeight: true
        clip: true; spacing: 4; topMargin: 8; bottomMargin: 8
        model: backend.songs
        activeFocusOnTab: true
        keyNavigationEnabled: true
        onCurrentIndexChanged: { if (activeFocus && currentIndex >= 0 && currentIndex < backend.songs.length) backend.selectSong(backend.songs[currentIndex].id) }
        Keys.onReturnPressed: page.openPlayer()
        reuseItems: true
        ScrollBar.vertical: ScrollBar { }
        delegate: Rectangle {
            id: row
            required property var modelData
            required property int index
            width: list.width - 10; height: 68; radius: 8
            color: backend.song.id === modelData.id ? Theme.accentTint : mouse.containsMouse ? Theme.surface : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.motion } }
            Accessible.role: Accessible.ListItem
            Accessible.name: modelData.title
            MouseArea {
                id: mouse; anchors.fill: parent; hoverEnabled: true
                onClicked: backend.selectSong(row.modelData.id)
                onDoubleClicked: { backend.selectSong(row.modelData.id); page.openPlayer() }
            }
            RowLayout {
                anchors.fill: parent; anchors.leftMargin: 16; anchors.rightMargin: 12; spacing: 12
                Rectangle {
                    Layout.preferredWidth: 38; Layout.preferredHeight: 40; radius: 6
                    color: backend.song.id === row.modelData.id ? Theme.accentFill : Theme.hover
                    Row {
                        anchors.centerIn: parent; spacing: 2
                        Repeater { model: 3; Rectangle { width: 4; height: 18; radius: 1; color: backend.song.id === row.modelData.id ? "#49351e" : Theme.muted } }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Text { text: row.modelData.title; Layout.fillWidth: true; elide: Text.ElideRight; font.family: Theme.font; font.pixelSize: 14; font.weight: Font.DemiBold; color: Theme.text }
                    Text { text: "Pedal " + (row.modelData.pedal === "MIDI" ? "do MIDI" : "automático disponível"); font.family: Theme.font; font.pixelSize: 11; color: Theme.muted }
                }
                Text { text: row.modelData.notes.toLocaleString(Qt.locale("pt_BR"),"f",0); Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                Text { text: Math.floor(row.modelData.duration / 60) + ":" + ("0" + Math.floor(row.modelData.duration % 60)).slice(-2); Layout.preferredWidth: 75; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
                Text { text: row.modelData.origin; Layout.preferredWidth: 110; horizontalAlignment: Text.AlignRight; font.family: Theme.font; font.pixelSize: 12; color: Theme.muted }
                TButton {
                    Layout.preferredWidth: 32; compact: true
                    glyph: row.modelData.favorite ? "\uE735" : "\uE734"
                    Accessible.name: row.modelData.favorite ? "Remover favorito" : "Favoritar música"
                    onClicked: backend.toggleFavorite(row.modelData.id)
                }
            }
        }
        Column {
            anchors.centerIn: parent; spacing: 14
            visible: list.count === 0
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Nenhuma música por aqui"; font.family: Theme.font; font.pixelSize: 20; color: Theme.text }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: "Ajuste a busca ou importe um MIDI, JSON ou TXT."; font.family: Theme.font; font.pixelSize: 13; color: Theme.muted }
        }
    }
    Rectangle { Layout.fillWidth: true; height: 1; color: Theme.line }
    RowLayout {
        Layout.fillWidth: true; Layout.topMargin: 16; spacing: 12
        Text { text: "Arquivos locais. Seu repertório fica neste computador."; Layout.fillWidth: true; wrapMode: Text.WordWrap; font.family: Theme.font; font.pixelSize: 11; color: Theme.faint }
        TButton { text: "Abrir reprodução"; glyph: "\uE768"; enabled: backend.song.id !== ""; onClicked: page.openPlayer() }
    }
}
